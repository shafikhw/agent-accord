"""Verify local HTTP monitoring, register immutability, launchers, and distribution assets."""

import argparse
import contextlib
import http.client
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

from agent_accord import cli, monitor
from test_register import ProjectCase


class MonitorTests(ProjectCase):
    """Read real temporary register state through a loopback HTTP server."""

    def setUp(self) -> None:
        """Start an ephemeral server for this test's isolated root and store."""
        super().setUp()
        self.server = monitor.create_server(self.read_snapshot)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        """Stop only this test's server before releasing its temporary project."""
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        super().tearDown()

    def read_snapshot(self) -> dict:
        """Read the isolated store with the same read-only callback used by the CLI.

        Returns:
            All published tasks and recent messages without acknowledgement.
        """
        return cli.monitor_snapshot(self.root, self.store)

    def request(self, path: str, method: str = "GET", headers: dict | None = None) -> tuple:
        """Send one bounded HTTP request to the fixture server.

        Args:
            path: Exact URL path to request.
            method: HTTP method used to test the read-only boundary.
            headers: Optional Host/Origin overrides for isolation tests.

        Returns:
            Status code, header mapping, and body bytes.
        """
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        try:
            connection.request(method, path, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_snapshot_contains_live_tasks_evidence_and_claims(self) -> None:
        """Expose current and completed cards with their evidence and retained paths."""
        task = self.task("codex-api")
        self.claim(task, "README.md")
        self.complete(task)
        status, headers, payload = self.request("/api/snapshot")
        snapshot = json.loads(payload)
        self.assertEqual(status, 200)
        self.assertEqual(snapshot["tasks"][0]["state"], "done")
        self.assertEqual(snapshot["tasks"][0]["evidence"], "Tests passed")
        self.assertEqual(snapshot["tasks"][0]["claims"][0]["path"], "readme.md")
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertTrue(snapshot["store_exists"])

    def test_refresh_observes_external_writer(self) -> None:
        """Pick up a new independent CLI publication without restarting the server."""
        self.assertEqual(json.loads(self.request("/api/snapshot")[2])["tasks"], [])
        result = self.cli("register", "--agent", "claude", "--summary", "Live publication")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(json.loads(self.request("/api/snapshot")[2])["tasks"][0]["summary"], "Live publication")

    def test_monitor_preserves_database_and_message_read_state(self) -> None:
        """Observe messages without modifying database bytes or consuming an inbox."""
        sender = self.task()
        target = self.task("claude")
        self.send(sender, target=target)
        before = self.store.read_bytes()
        snapshot = json.loads(self.request("/api/snapshot")[2])
        self.assertEqual(snapshot["unread_count"], 1)
        self.assertEqual(snapshot["messages"][0]["to_task"], target)
        self.assertIsNone(snapshot["messages"][0]["read_at"])
        self.assertEqual(self.store.read_bytes(), before)
        self.assertEqual(len(self.inbox("claude", target)), 1)

    def test_missing_store_waits_without_creating_state(self) -> None:
        """Allow a dashboard to wait for an agent's first published card."""
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "not-created/register.sqlite3"
            snapshot = cli.monitor_snapshot(self.root, missing)
            self.assertFalse(snapshot["store_exists"])
            self.assertEqual(snapshot["messages"], [])
            self.assertFalse(missing.parent.exists())

    def test_messages_are_bounded_and_unread_total_is_complete(self) -> None:
        """Limit dashboard message payloads while preserving the overall unread count."""
        sender = self.task()
        for number in range(205):
            self.send(sender, recipient="claude")
        snapshot = self.read_snapshot()
        self.assertEqual(len(snapshot["messages"]), 200)
        self.assertEqual(snapshot["message_count"], 205)
        self.assertEqual(snapshot["unread_count"], 205)
        self.assertEqual(snapshot["messages"][0]["id"], 205)

    def test_static_routes_have_security_headers(self) -> None:
        """Serve only packaged assets with browser restrictions and correct MIME types."""
        for path, expected in (("/", "text/html"), ("/assets/app.js", "text/javascript"), ("/assets/style.css", "text/css")):
            with self.subTest(path=path):
                code, headers, body = self.request(path)
                self.assertEqual(code, 200)
                self.assertIn(expected, headers["Content-Type"])
                self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
                self.assertNotIn("Access-Control-Allow-Origin", headers)
                self.assertTrue(body)

    def test_project_files_and_traversal_are_not_served(self) -> None:
        """Never turn the monitor into an arbitrary project file server."""
        for path in ("/README.md", "/.git/config", "/../cli.py", "/assets/../cli.py", "/api/snapshot?store=other"):
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 404)

    def test_foreign_host_origin_and_fetch_site_are_rejected(self) -> None:
        """Reject rebinding and cross-origin browser requests before reading records."""
        for headers in ({"Host": "evil.example"}, {"Origin": "https://evil.example"},
                        {"Sec-Fetch-Site": "cross-site"}, {"Sec-Fetch-Site": "same-site"}):
            with self.subTest(headers=headers):
                self.assertEqual(self.request("/api/snapshot", headers=headers)[0], 403)

    def test_mutating_methods_are_not_implemented(self) -> None:
        """Expose no HTTP endpoint for changes or message acknowledgement."""
        before = self.store.read_bytes()
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            with self.subTest(method=method):
                self.assertEqual(self.request("/api/snapshot", method)[0], 501)
        self.assertEqual(self.store.read_bytes(), before)

    def test_database_failure_returns_503_without_private_paths(self) -> None:
        """Surface errors without leaking raw database diagnostics into the page."""
        self.db.execute("PRAGMA user_version=99")
        with contextlib.redirect_stderr(io.StringIO()):
            code, _, payload = self.request("/api/snapshot")
        self.assertEqual(code, 503)
        self.assertNotIn(str(self.root), payload.decode())

    def test_loopback_only_and_invalid_ports(self) -> None:
        """Keep monitoring local and validate requested ports before starting HTTP."""
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        for port in (-1, 65536):
            with self.assertRaises(ValueError):
                monitor.create_server(self.read_snapshot, port)

    def test_installer_bundles_monitor_and_relocatable_launcher(self) -> None:
        """Include monitor resources and a root-relative launcher in a target project."""
        installed = cli.initialize(self.root)
        runtime = self.root / installed["entrypoint"]
        for resource in ("monitor.py", "monitor_assets/index.html", "monitor_assets/style.css", "monitor_assets/app.js"):
            self.assertTrue((runtime.parent / resource).is_file())
        launcher = self.root / installed["launcher"]
        self.assertTrue(launcher.is_file())
        self.assertNotIn(str(self.root), launcher.read_text(encoding="utf-8"))
        self.assertEqual(cli.initialize(self.root)["written"], [])

    def test_existing_launcher_is_preserved_until_explicit_upgrade(self) -> None:
        """Reject customized launchers before any installation output is written."""
        name, _ = monitor.launcher(sys.platform)
        (self.root / name).write_text("custom launcher", encoding="utf-8")
        with self.assertRaisesRegex(cli.CoordinationError, "upgrade"):
            cli.initialize(self.root)
        self.assertFalse((self.root / cli.SKILL_PATH).exists())

    def test_project_launcher_selects_root_and_forwards_monitor_flags(self) -> None:
        """Execute the real shell launcher and verify its Python invocation contract."""
        installed = cli.initialize(self.root)
        launcher = self.root / installed["launcher"]
        runtime = self.root / installed["entrypoint"]
        # A short recording entrypoint lets the actual platform launcher finish
        # normally, without depending on permission to kill Windows process trees.
        runtime.write_text(
            '"""Record a test-only launcher invocation without starting HTTP."""\n'
            'import json, os, sys\nprint(json.dumps({"cwd": os.getcwd(), "args": sys.argv[1:]}))\n',
            encoding="utf-8",
        )
        command = (["cmd.exe", "/d", "/c", "call", str(launcher), "--no-browser"]
                   if sys.platform == "win32" else ["sh", str(launcher), "--no-browser"])
        result = subprocess.run(command, cwd=self.root.parent, capture_output=True, text=True,
                                timeout=20, check=True)
        recorded = json.loads(result.stdout.strip())
        self.assertEqual(Path(recorded["cwd"]), self.root)
        self.assertEqual(recorded["args"], ["monitor", "--no-browser"])

    def test_copied_cli_runs_monitor_without_package(self) -> None:
        """Start the copied CLI, retrieve its actual URL, and read the selected store."""
        installed = cli.initialize(self.root)
        runtime = self.root / installed["entrypoint"]
        process = subprocess.Popen([sys.executable, str(runtime), "monitor", "--no-browser"],
                                   cwd=self.root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            # Startup prints the bound URL before the server accepts requests.
            line = process.stdout.readline().strip()
            self.assertTrue(line.startswith("Agent Accord monitor: http://127.0.0.1:"), line)
            port = int(line.rsplit(":", 1)[1])
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            try:
                connection.request("GET", "/api/snapshot")
                response = connection.getresponse()
                self.assertEqual(response.status, 200)
                self.assertEqual(json.loads(response.read())["repo"], str(self.root))
            finally:
                connection.close()
        finally:
            process.terminate()
            process.communicate(timeout=10)


if __name__ == "__main__":
    unittest.main()
