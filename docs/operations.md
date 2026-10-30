# Operations and troubleshooting

## Keep the active store local

The default store is `.agent-accord/register.sqlite3` inside the target Git
working tree. `init` appends `/.agent-accord/` to the project's ignore file.
Ignored does not mean encrypted or protected from other local processes.

If a checkout is in a synchronized directory, choose an unsynchronized local
path for the active database. For example:

```powershell
# Run from the target project's Git root. Use a different store for each project.
python .agents/skills/agent-accord/scripts/coord.py --store "$env:LOCALAPPDATA\AgentAccord\my-project.sqlite3" status --agent codex --text
```

The equivalent POSIX pattern is `--store "$HOME/.local/state/agent-accord/my-project.sqlite3"`.
These are caller-chosen locations; the CLI defines no environment-variable
configuration. Every participant must use exactly the same store and canonical
root. Record those arguments in project instructions and any hook command;
otherwise agents using the default store will not see this work.
If a custom store is inside the checkout, explicitly ignore its path and
SQLite sidecars too; the generated ignore entry covers only the default folder.

Keep active SQLite files off network filesystems and cloud-sync services.
Store binding rejects a different project root; `--store` is a local placement
option, not cross-clone or cross-machine sharing.

## Ownership conflicts and abandoned tasks

Inspect status and the actual diff. A stale or paused task is still an owner.
Use an authorized coordination message, find a disjoint scope, or ask the
human project owner to review and explicitly close the abandoned task:

```sh
agent-accord finish --task ABANDONED_TASK --summary "Owner-reviewed handoff; remaining work moved to the new task" --evidence "Reviewed current diff; no tests claimed"
```

The CLI has no identity authentication, so that command is technically
available to any local process. The skill requires owner/user authorization.
Do not finish someone else's card just to remove a conflict. Register a new
task for the continuation and review existing edits before adopting them.

If an agent-wide message was acknowledged by another session using the same
identity, it will no longer appear unread. Use distinct identities for
independent sessions and task-specific routing for scoped notes.

## Backup, relocation, and recovery

Stop writers before copying a store and its relevant SQLite sidecars. For a
live backup, use SQLite's supported backup facility rather than filesystem
sync. Never publish backups with the open-source code.

The store is bound to its original absolute canonical root. After relocating
or renaming a checkout, finish or explicitly hand off open work first. Archive
the old register privately, then start a fresh store at the new location.
The CLI deliberately has no automatic rebind or migration from the private
project's original register. Review historical cards through the old location
or a separately controlled SQLite inspection when needed.

If SQLite reports corruption, stop writers, preserve the file privately, and
recover from a known backup or create a fresh store after reviewing remaining
work. Never delete an active store to make a claim conflict disappear.

## Common failures

| Message or symptom | Check |
| --- | --- |
| Git working tree required | Install Git, select the correct directory, or run `git init` for a new project |
| Explicit root is a subdirectory | Pass the Git working-tree root; claim paths remain relative to that root |
| Git could not inspect changes | Verify Git permissions, project health, and the selected root; dirty protection is not bypassed |
| Existing changes under a path | Inspect owner and diff, then adopt only if authorized |
| Claim conflict | Inspect the owner; paused/stale does not release it |
| Database locked | Check for a long-running writer and local filesystem locking; write waits are bounded at ten seconds |
| Store belongs to another project | Use its original root/store or a new store for this project |
| Unsupported schema / unrelated database | Select an Agent Accord store with the matching version; do not point the tool at application databases |
| Existing installation differs | Review the installed diff, then use `init --upgrade` if appropriate |
| Instructions were edited | Reconcile the managed coordination block in `AGENTS.md` manually |
| Installed command not found | Use the same Python environment for installation/execution, `python -m agent_accord`, or the copied CLI |
| No new note appears | Check the identity, exact task ID, selected store, and whether another session acknowledged it |
| Monitor launcher is missing | Update Agent Accord and run `init --upgrade` after reviewing the installed changes |
| Double-click opens an editor on Linux | Execute the `.sh` in a terminal or use your desktop's executable-script setting |
| Monitor URL no longer responds | Keep the launch terminal open, or use the project launcher to start a new server |
| Monitor shows a different register | Launch with the same `--root` and `--store` arguments as the coding agents; launchers use the default store |

`status` and non-acknowledging `inbox` reads do not initialize or modify an
existing store. They still need Git root discovery and SQLite read access.
Permission errors are surfaced; the tool never silently falls back to a
different directory or turns off ownership checks.

The monitor is intentionally local. Do not expose it through a public reverse
proxy or use it as a hosted dashboard. A local process can read snapshots just
as it can read the register; the HTTP interface does not add user authentication.
Closing the browser tab alone does not stop the server. Close the terminal or
press Ctrl+C when monitoring is finished. Repeated launches start separate
servers; use a fixed `--port` and an existing browser tab if you prefer one URL.
