# Agent setup and walkthrough

Initialize once per project, then point every participating agent at the same
skill and working tree. The register is language independent; the small CLI
needs Python and Git even if the project itself uses another language.

## Project instructions

`agent-accord --root /path/to/project init` appends an `AGENTS.md` section and
installs the self-contained skill/runtime. Review the generated changes. If
an existing agent session has already loaded its instructions, explicitly ask
it to read `.agents/skills/agent-accord/SKILL.md` before continuing.

Use this bootstrap instruction with any participating agent:

```text
Read .agents/skills/agent-accord/SKILL.md. For this project, use agent identity
YOUR_AGENT. Check the shared status, register the actual task, and claim the
paths before editing. Follow this project's existing approval and Git rules.
```

Replace `YOUR_AGENT` with a lowercase stable name. A practical mapping:

| Tool/session | Agent ID | Where to put the pointer |
| --- | --- | --- |
| Codex | `codex` | Project instructions / generated `AGENTS.md` |
| Claude Code | `claude` | Add a pointer to the project's existing `CLAUDE.md` or configured instructions |
| Antigravity | `antigravity` | The project's configured agent rules/instructions |
| Independent second Codex session | `codex-ui` | Explicit session instruction |
| Another tool or custom role | `reviewer-1` | Its configured project instructions |

Tool-specific instruction discovery and hook formats can change. This project
does not install hidden home-directory settings, alter permissions, or assume
that every tool automatically discovers `.agents/skills`. Explicitly reading
the installed skill is the portable fallback. The installed skill has no
vendor SDK dependency and can be read as ordinary Markdown.

## Optional startup or prompt hooks

If your tool supports command hooks, configure a startup hook to run the
following command from the project root, replacing the agent identity:

```sh
python .agents/skills/agent-accord/scripts/coord.py status --agent claude --text
```

Merge it into your existing hook configuration using the schema supported by
your installed tool; do not replace unrelated hooks or permissions. For a
hook running outside the project, give an absolute script path and put
`--root /absolute/path/to/project` before `status`. Quote paths with spaces.
Set a timeout above the command's possible Git (15-second) and SQLite
(10-second) waits, and surface hook failures instead of assuming coordination
is current. Python's executable must be available to the agent's environment.

A before-prompt hook can help active agents see new notes, but repeats context
on every prompt. Start with a session-start hook plus explicit status checks
before new scopes and after pauses. Routine full-history snapshots are
unnecessary. Hooks should only read status: do not auto-register tasks or
silently acknowledge messages on every prompt.

No hook can make queued messages into live interruptions. The sender should
wait for an explicit response or completion before editing an owned scope.

## Two-agent example

Both agents work in the same project directory and follow the installed skill.
The commands below use the package executable; the copied Python CLI works
identically. Replace symbolic task IDs with the actual IDs returned.

**Codex opens and claims its work:**

```sh
agent-accord register --agent codex --summary "Fix parser error handling"
agent-accord claim --task CODEX_TASK --path src/parser.py
```

**Claude checks status before working:**

```sh
agent-accord status --agent claude --text
agent-accord register --agent claude --summary "Update parser documentation"
agent-accord claim --task CLAUDE_TASK --path docs/parser.md
```

Claude sees Codex's `src/parser.py` claim and can work on documentation without
overlap. If Claude also needs `src/parser.py`, its claim fails. If authorized
to send a coordination note, Claude can queue:

```sh
agent-accord message --task CLAUDE_TASK --to-task CODEX_TASK --text "I need parser.py after your fix; please include the contract change in your handoff"
```

**Codex reads the note, completes its scope, and releases the claim:**

```sh
agent-accord inbox --agent codex --task CODEX_TASK --ack
agent-accord finish --task CODEX_TASK --summary "Parser now raises ParseError for malformed rows" --evidence "Parser tests passed"
```

Claude rechecks the actual diff and evidence, then claims the newly released
file if it is still part of its authorized task. If Codex left edits in the
working tree, that claim also needs an explicit, reviewed
`--adopt-existing`. Completion releases ownership; it does not commit or erase
working-tree changes.

## Distinct sessions, clones, and environments

Two active sessions may share an identity for card ownership, but their inbox
acknowledgements are shared. Distinct identities (`codex-api`, `codex-ui`)
avoid this ambiguity and can message each other. Each session should keep its
own returned task ID.

Different clones or Git worktrees have separate roots and default databases.
Agent Accord does not coordinate their edits automatically. Likewise, a host
and container mounting the same files at different absolute paths will fail
the store's root check. Use a consistent local execution environment; do not
edit the database root binding to simulate a distributed service.

## Updating the installed copy

Upgrade the source/package, review the changes, and run:

```sh
agent-accord --root /path/to/project init --upgrade
```

This replaces the installed skill/runtime/license only with explicit upgrade
authorization. It does not erase task records or rewrite customized project
instructions. Re-read the skill in already-running agent sessions. Do not
upgrade the CLI version halfway through simultaneous sessions without
coordinating the update.
