# CLI reference

Use the installed `agent-accord` command, `python -m agent_accord`, or the
project's copied `python .agents/skills/agent-accord/scripts/coord.py`.

```text
agent-accord [--root PROJECT] [--store DATABASE] COMMAND [OPTIONS]
```

Global options go **before** the command. Commands operate on the Git root
discovered from the current directory, including when invoked from a nested
folder. Relative claim paths and `--store` paths are always relative to that
root. An explicit `--root` must name the working-tree root itself.

`--version` prints the version without requiring a Git project.
`--help` and `COMMAND --help` explain syntax.

## Commands

| Command | Required options | Optional options | Effect |
| --- | --- | --- | --- |
| `init` | None | `--upgrade` | Copy skill, license, and runtime; append project instructions and ignore entry |
| `status` | None | `--agent ID`, `--text`, `--all` | Read every agent's active/paused cards; optionally include selected agent's unread inbox/history |
| `register` | `--agent ID --summary TEXT` | `--session-ref TEXT` | Create active task; return `task_id` |
| `claim` | `--task ID` and at least one scope | repeated `--path PATH`, repeated `--directory PATH`, `--adopt-existing` | Atomically acquire all scopes or reject all |
| `update` | `--task ID` | `--summary TEXT`, `--evidence TEXT`, `--state active\|paused` | Checkpoint without releasing claims |
| `finish` | `--task ID --summary TEXT` | `--evidence TEXT` | Mark done and release claims from conflict checks |
| `message` | `--task ID --text TEXT`, exactly one of `--to AGENT` or `--to-task ID` | None | Queue a note for another agent identity |
| `inbox` | `--agent ID` | `--task ID`, `--ack` | Read/acknowledge broadcasts and optional targeted notes |
| `correct` | `--from-task ID --target-task ID --summary TEXT` | None | Append a revised summary to a finished task |

`init` does not accept a custom `--store`; it installs instructions for the
default location. For a custom local database, configure the same `--store`
in every agent command and update your project's instructions accordingly.

## Identity and field limits

Agent IDs match `[a-z][a-z0-9_-]{0,63}`. Tool names are conventions, not a
fixed list or authenticated identity. Multiple sessions that need independent
inboxes should use distinct identities.

Summaries, messages, and corrections allow 1-1000 characters after trimming.
Evidence allows 0-4000 characters and optional session references allow 0-500.
Do not paste sensitive material in these fields. Timestamps use UTC with an
explicit offset. Task IDs are generated locally as 12-character hexadecimal
strings; use the exact returned ID, not a prefix or another session's ID.

## Claims

```sh
agent-accord claim --task TASK_ID --path src/parser.py --path tests/test_parser.py
agent-accord claim --task TASK_ID --directory src/new-feature
```

Existing directories are automatically directory scopes, even when passed via
`--path`. Use `--directory` for planned directories. Files may be claimed before
creation. Case-only path aliases share an ownership key on every platform;
this deliberately creates conservative conflicts on case-sensitive filesystems.
Symlinks resolve to their targets before containment checks. The project root,
Git metadata, and the default register directory cannot be claimed.

Git inspects proposed paths literally, including names with brackets. Existing
modified, staged, untracked, or ignored files require explicit adoption after
review. A task may reassert its already-owned scope after its own edits.
Adoption does not replace the active or paused ownership of another task.

## Messages and acknowledgement

```sh
agent-accord message --task SENDER_TASK_ID --to-task RECIPIENT_TASK_ID --text "API scope is ready for review"
agent-accord inbox --agent claude --task RECIPIENT_TASK_ID --ack
```

`status --agent claude` displays all unread notes for that identity, including
notes for its different tasks. `inbox --agent claude` reads only agent-wide
broadcasts. Adding `--task` includes broadcasts plus that task's targeted notes.
`--ack` marks exactly the returned IDs as read; it does not consume another
task's targeted messages. Broadcast acknowledgement is shared by all sessions
using the same agent ID.

Senders and task-specific recipients must be active or paused. Previously
queued notes remain readable after their recipient finishes. Self-identity
messaging is rejected even between distinct task IDs. Use distinct identities
for independent parallel sessions that need to communicate.

## Output and exit status

Successful commands print JSON to stdout, except `status --text` and
`--version`. Runtime rejections print `{"error": "..."}` and return exit code
**2**. Successful commands return **0**. Argument syntax errors are argparse
usage messages on stderr with exit code 2; help returns 0. Do not infer success
from the presence of JSON alone.

`status` without `--all` omits finished cards. `--all` includes original
completion summaries, correction history, and `effective_summary` (the latest
correction, or the original summary). `--agent` selects an inbox; it **never
hides other agents' ownership**.

`status --text` escapes control characters and clips summaries to 240 source
characters, previews to 20 claimed paths (160 characters per path), and notes
to 300 characters. It marks omitted claims and clips with an ellipsis. The
JSON output retains the full fields. Text snapshots still grow with the number
of active tasks and unread messages; resolve old work and acknowledge notes
instead of calling `status --all` at every prompt.

Status and unacknowledged inbox reads open existing stores read-only. Reading
a project with no store returns empty state without creating directories or
database files. Write operations may create a store even if the requested
operation is later rejected; claims themselves remain atomic.
