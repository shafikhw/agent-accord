"""Test project installation, standalone operation, and clean-start concurrency."""

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import unittest

from agent_accord import cli as coord
from test_register import ProjectCase


class InstallationTests(ProjectCase):
    """Install the portable runtime into a separate, disposable project."""

    def test_install_preserves_instructions_and_is_idempotent(self) -> None:
        """Append a protocol pointer while retaining existing human instructions."""
        instructions = self.root / "AGENTS.md"
        instructions.write_text("# Existing rules\nKeep these.\n", encoding="utf-8")
        ignore_before = (self.root / ".gitignore").read_bytes()
        first = coord.initialize(self.root)
        self.assertIn("scripts/coord.py", first["entrypoint"])
        self.assertTrue(instructions.read_text(encoding="utf-8").startswith("# Existing rules\nKeep these."))
        self.assertEqual((self.root / ".gitignore").read_bytes(), ignore_before)
        second = coord.initialize(self.root)
        self.assertEqual(second["written"], [])

    def test_install_preflights_conflicts_before_writing(self) -> None:
        """Reject a custom installed script without replacing it or adding other files."""
        runtime = self.root / coord.SKILL_PATH / "scripts/coord.py"
        runtime.parent.mkdir(parents=True)
        runtime.write_text("# Custom runtime\n", encoding="utf-8")
        with self.assertRaisesRegex(coord.CoordinationError, "--upgrade"):
            coord.initialize(self.root)
        self.assertFalse((self.root / coord.SKILL_PATH / "SKILL.md").exists())
        self.assertFalse((self.root / "AGENTS.md").exists())
        self.assertEqual(runtime.read_text(encoding="utf-8"), "# Custom runtime\n")
        coord.initialize(self.root, upgrade=True)
        self.assertEqual(runtime.read_text(encoding="utf-8"), Path(coord.__file__).read_text(encoding="utf-8"))

    def test_edited_instruction_block_requires_manual_reconciliation(self) -> None:
        """Protect locally customized project instructions even during an upgrade."""
        coord.initialize(self.root)
        instructions = self.root / "AGENTS.md"
        instructions.write_text(instructions.read_text(encoding="utf-8").replace("Before editing", "Only on Mondays"), encoding="utf-8")
        before = instructions.read_bytes()
        with self.assertRaisesRegex(coord.CoordinationError, "manually"):
            coord.initialize(self.root, upgrade=True)
        self.assertEqual(instructions.read_bytes(), before)

    def test_install_cannot_follow_directory_link_outside_project(self) -> None:
        """Reject a malicious or accidental external .agents installation target."""
        with tempfile.TemporaryDirectory() as outside:
            self.directory_link(self.root / ".agents", Path(outside))
            with self.assertRaisesRegex(coord.CoordinationError, "outside"):
                coord.initialize(self.root)
            self.assertEqual(list(Path(outside).iterdir()), [])

    def test_copied_runtime_discovers_target_root_from_subdirectory(self) -> None:
        """Run copied code with spaces in paths and without importing its package."""
        coord.initialize(self.root)
        runtime = self.root / coord.SKILL_PATH / "scripts/coord.py"
        result = self.cli("register", "--agent", "antigravity", "--summary", "Standalone task",
                          cwd=self.root / "src", script=runtime)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        task = json.loads(result.stdout)["task_id"]
        result = self.cli("claim", "--task", task, "--path", "planned.txt", script=runtime)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = self.cli("init", script=runtime)
        self.assertEqual(json.loads(result.stdout)["written"], [])
        self.assertEqual(len(self.snapshot()["tasks"]), 1)

    def test_explicit_root_works_from_an_unrelated_directory(self) -> None:
        """Keep installation location and current directory out of root selection."""
        with tempfile.TemporaryDirectory() as elsewhere:
            result = self.cli("--root", str(self.root), "status", "--text", cwd=Path(elsewhere))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("No active task", result.stdout)
        result = self.cli("--root", str(self.root / "src"), "status")
        self.assertEqual(result.returncode, 2)

    def test_custom_store_is_relative_to_project_root(self) -> None:
        """Resolve custom local storage consistently when invoked from a subdirectory."""
        result = self.cli("--store", "other/register.sqlite3", "register", "--agent", "codex",
                          "--summary", "Other store", cwd=self.root / "src")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.root / "other/register.sqlite3").is_file())
        self.assertEqual(self.snapshot()["tasks"], [])

    def test_status_and_inbox_on_new_project_create_no_state(self) -> None:
        """Let startup hooks inspect an empty Git project without writing a database."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            coord.git(root, "init", "-q")
            for args in (("status", "--agent", "claude"), ("inbox", "--agent", "codex")):
                result = self.cli(*args, cwd=root)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse((root / ".agent-accord").exists())

    def test_non_git_project_is_rejected_without_files(self) -> None:
        """Require Git rather than silently disabling dirty-work inspection."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = self.cli("--root", str(root), "init", cwd=root)
            self.assertEqual(result.returncode, 2)
            self.assertIn("git init", json.loads(result.stdout)["error"])
            self.assertEqual(list(root.iterdir()), [])

    def test_simultaneous_first_writers_create_one_valid_store(self) -> None:
        """Initialize and register concurrently from separate CLI processes."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            coord.git(root, "init", "-q")

            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = [executor.submit(self.cli, "register", "--agent", agent, "--summary", "First writer", cwd=root)
                           for agent in ("codex", "claude", "antigravity", "custom")]
                self.assertEqual([future.result().returncode for future in futures], [0, 0, 0, 0])
            result = self.cli("status", cwd=root)
            self.assertEqual(len(json.loads(result.stdout)["tasks"]), 4)


if __name__ == "__main__":
    unittest.main()
