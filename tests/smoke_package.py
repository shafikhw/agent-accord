"""Exercise a built, installed package and its copied runtime in a fresh project.

Run with the Python environment containing the built wheel, without PYTHONPATH
pointing at the repository's src directory. No network or external service is used.
"""

import json
from importlib.metadata import version
from pathlib import Path
import subprocess
import sys
import sysconfig
import tempfile

from agent_accord import __version__, cli


def run(*arguments: str, cwd: Path) -> dict:
    """Execute a successful JSON command using the wheel environment's Python.

    Args:
        arguments: Executable arguments, such as -m agent_accord status.
        cwd: Isolated working directory used to prove root discovery.

    Returns:
        The parsed JSON operation result.

    Raises:
        subprocess.CalledProcessError: If the CLI command fails.
        json.JSONDecodeError: If the command does not produce JSON.
    """
    result = subprocess.run([sys.executable, *arguments], cwd=cwd, check=True,
                            capture_output=True, text=True, timeout=30)
    return json.loads(result.stdout)


def main() -> None:
    """Verify installed resources and a complete cross-agent ownership lifecycle.

    Raises:
        AssertionError: If source imports leak in or installed behavior fails.
        subprocess.CalledProcessError: If Git or the installed CLI fails.
    """
    source_tree = Path(__file__).resolve().parents[1] / "src"
    assert not Path(cli.__file__).resolve().is_relative_to(source_tree), "Smoke test imported source instead of wheel"
    assert __version__ == cli.VERSION == version("agent-accord"), "Package/runtime versions differ"
    command = Path(sysconfig.get_path("scripts")) / ("agent-accord.exe" if sys.platform == "win32" else "agent-accord")
    console = subprocess.run([str(command), "--version"], check=True, capture_output=True, text=True, timeout=30)
    assert console.stdout.strip() == "Agent Accord " + __version__
    with tempfile.TemporaryDirectory(prefix="accord wheel ") as directory:
        root = Path(directory).resolve()
        subprocess.run(["git", "init", "-q"], cwd=root, check=True, capture_output=True)
        installed = run("-m", "agent_accord", "init", cwd=root)
        script = root / installed["entrypoint"]
        skill = script.parent.parent / "SKILL.md"
        assert skill.is_file() and (skill.parent / "LICENSE").is_file()
        assert not (root / ".agent-accord").exists(), "init unexpectedly created a database"
        owner = run("-m", "agent_accord", "register", "--agent", "codex", "--summary", "Wheel test", cwd=root)["task_id"]
        reviewer = run(str(script), "register", "--agent", "claude", "--summary", "Review test", cwd=root)["task_id"]
        run(str(script), "claim", "--task", owner, "--path", "planned.py", cwd=root)
        conflict = subprocess.run([sys.executable, str(script), "claim", "--task", reviewer,
                                   "--path", "planned.py"], cwd=root, capture_output=True, text=True, timeout=30)
        assert conflict.returncode == 2 and "Claim conflict" in json.loads(conflict.stdout)["error"]
        run("-m", "agent_accord", "finish", "--task", owner, "--summary", "Handoff ready", cwd=root)
        run(str(script), "claim", "--task", reviewer, "--path", "planned.py", cwd=root)
        run(str(script), "finish", "--task", reviewer, "--summary", "Review complete", cwd=root)
        assert run(str(script), "status", cwd=root)["tasks"] == []
        assert run(str(script), "init", cwd=root)["written"] == []
    print(f"Installed wheel {__version__}: resources, standalone runtime, claim conflict, handoff, and idempotence passed.")


if __name__ == "__main__":
    main()
