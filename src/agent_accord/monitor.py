"""Serve the Agent Accord read-only monitor on the local loopback interface.

Only allowlisted assets and snapshots are exposed. The server does not serve
project files, accept mutations, acknowledge notes, or write register records.
"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from typing import Any, Callable
import webbrowser

ASSETS = Path(__file__).resolve().with_name("monitor_assets")
ROUTES = {"/": ("index.html", "text/html; charset=utf-8"),
          "/assets/style.css": ("style.css", "text/css; charset=utf-8"),
          "/assets/app.js": ("app.js", "text/javascript; charset=utf-8")}


def launcher(platform: str) -> tuple[str, str]:
    """Build a relocatable project launcher with no machine-specific Python path.

    Args:
        platform: Python platform identifier, such as win32, darwin, or linux.

    Returns:
        Root filename and its contents. Windows uses a double-clickable CMD;
        macOS uses an executable command file and Linux uses an executable shell script.
    """
    if platform == "win32":
        return "Agent Accord Monitor.cmd", '''@echo off
rem Open this project's read-only Agent Accord monitor. Close the window to stop.
setlocal
cd /d "%~dp0"
call py -3 --version >nul 2>nul
if not errorlevel 1 goto py
call python --version >nul 2>nul
if not errorlevel 1 goto python
echo Python 3.10 or newer is required. Install Python and reopen this launcher.
pause
exit /b 1
:python
call python ".agents/skills/agent-accord/scripts/coord.py" monitor %*
goto done
:py
call py -3 ".agents/skills/agent-accord/scripts/coord.py" monitor %*
:done
if errorlevel 1 pause
'''
    name = "Agent Accord Monitor.command" if platform == "darwin" else "Agent Accord Monitor.sh"
    return name, '''#!/bin/sh
# Open this project's read-only monitor; Ctrl+C stops its local server.
# Usage: double-click where supported, or run this script in a terminal.
# Requires Python 3.10+ on PATH; exits nonzero if Python/server startup fails.
cd -- "$(dirname -- "$0")" || exit 1
exec python3 ".agents/skills/agent-accord/scripts/coord.py" monitor "$@"
'''


class MonitorHandler(BaseHTTPRequestHandler):
    """Expose only fixed dashboard routes to requests for the bound local origin.

    Attributes:
        server: Threading HTTP server with a snapshot_reader callback.
    """

    def setup(self) -> None:
        """Bound idle request sockets so abandoned local connections cannot linger."""
        super().setup()
        self.connection.settimeout(15)

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress routine polling logs and untrusted request text.

        Args:
            format: Ignored HTTP log template.
            args: Ignored template arguments.
        """

    def respond(self, code: int, payload: bytes, content_type: str) -> None:
        """Return a non-cacheable response with browser isolation headers.

        Args:
            code: HTTP status code.
            payload: Already serialized response bytes.
            content_type: Fixed allowlisted MIME type.
        """
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; "
                         "connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        """Serve fixed assets or a fresh read-only snapshot; reject foreign origins."""
        host = f"127.0.0.1:{self.server.server_port}"
        if (self.headers.get("Host") != host
                or self.headers.get("Origin") not in (None, "http://" + host)
                or self.headers.get("Sec-Fetch-Site") not in (None, "same-origin", "none")):
            self.respond(403, b'{"error":"Local origin required"}', "application/json")
            return
        if self.path == "/api/snapshot":
            try:
                snapshot = self.server.snapshot_reader()
                self.respond(200, json.dumps(snapshot).encode("utf-8"), "application/json; charset=utf-8")
            except Exception as exc:
                # The callback can reject root/schema binding with its own error
                # type; do not expose exception strings or filesystem paths.
                self.respond(503, b'{"error":"Register unavailable. Check the selected store and server terminal."}',
                             "application/json")
                print("Agent Accord monitor: unable to read the selected register (" + type(exc).__name__ + ").",
                      file=sys.stderr)
            return
        resource = ROUTES.get(self.path)
        if resource is None:
            self.respond(404, b"Not found", "text/plain; charset=utf-8")
            return
        filename, content_type = resource
        try:
            self.respond(200, (ASSETS / filename).read_bytes(), content_type)
        except OSError:
            self.respond(503, b"Monitor assets are missing. Reinstall or run init --upgrade.", "text/plain")


def create_server(reader: Callable[[], dict[str, Any]], port: int = 0) -> ThreadingHTTPServer:
    """Bind a monitor to IPv4 loopback, never to a LAN or public interface.

    Args:
        reader: Callback returning a JSON-serializable, read-only register snapshot.
        port: Requested port, or zero to let the OS select an available port.

    Returns:
        A bound HTTP server; caller must serve and close it.

    Raises:
        ValueError: If the port is outside 0-65535.
        OSError: If the requested port cannot be bound.
    """
    if not 0 <= port <= 65535:
        raise ValueError("Monitor port must be between 0 and 65535.")
    server = ThreadingHTTPServer(("127.0.0.1", port), MonitorHandler)
    server.daemon_threads = True
    server.snapshot_reader = reader
    return server


def serve(reader: Callable[[], dict[str, Any]], port: int = 0, open_browser: bool = True) -> int:
    """Open a browser monitor and serve until interrupted or its terminal is closed.

    Args:
        reader: Callback reading the selected project/store without mutations.
        port: Loopback port, zero for automatic selection.
        open_browser: Whether to open the default system browser.

    Returns:
        Zero after an intentional keyboard interrupt.

    Raises:
        OSError: If assets are missing or the selected port cannot be bound.
        ValueError: If the port is invalid.
    """
    if not all((ASSETS / filename).is_file() for filename, _ in ROUTES.values()):
        raise OSError("Monitor assets are missing; reinstall or run init --upgrade.")
    server = create_server(reader, port)
    url = f"http://127.0.0.1:{server.server_port}"
    print("Agent Accord monitor: " + url, flush=True)
    print("Read-only local monitor. Close this terminal or press Ctrl+C to stop.", flush=True)
    try:
        if open_browser:
            try:
                if not webbrowser.open(url):
                    print("Open the URL above in your browser.", flush=True)
            except webbrowser.Error:
                print("Open the URL above in your browser.", flush=True)
        server.serve_forever(poll_interval=0.3)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
