# Design

Agent Accord coordinates **cooperating processes in one Git working tree**.
It is a synchronous CLI over a local SQLite database, plus a skill that makes
its ownership rules part of each coding session's workflow.

## Small components

| Component | Responsibility |
| --- | --- |
| `src/agent_accord/cli.py` | Standalone CLI, path normalization, Git inspection, SQLite operations, installation |
| `src/agent_accord/SKILL.md` | Portable session, claim, checkpoint, and handoff protocol |
| `src/agent_accord/monitor.py` | Loopback HTTP reader and platform launcher generation |
| `src/agent_accord/monitor_assets/` | Dependency-free, responsive monitoring UI |
| `src/agent_accord/LICENSE` | License distributed with copied runtime |
| `.agent-accord/register.sqlite3` | Ignored local state, created on first write |
| Generated `AGENTS.md` block | Points project agents to the skill and CLI |

The package entrypoint and copied runtime execute the same code. There is no
agent SDK, provider API, telemetry endpoint, or persistent background service.
The optional monitor runs a local HTTP server for the lifetime of its terminal.

## Read-only monitoring

`monitor` runs a standard-library threaded HTTP server on IPv4 loopback,
using an available port unless one is requested. Its three packaged assets
and `/api/snapshot` are the only routes. Snapshots use read-only SQLite
connections and a consistent transaction to include tasks, corrections,
latest messages, and counts; no acknowledgement operation is called.

The page polls every three seconds without overlapping requests. It retains
the previous snapshot with a warning when reads fail. All register text is
inserted using DOM `textContent`, and the server supplies a same-origin
Content Security Policy, no-store caching, and restrictive Host/Origin/fetch
checks. It exposes no mutation endpoints or arbitrary filesystem serving.
The local filesystem user remains the trust boundary.

Activity is derived from card creation, the current `updated_at` checkpoint,
completion state, corrections, and recent messages. It does not fabricate
an event history: previous checkpoint text/timestamps are not retained by
the schema. Agent summaries therefore describe publication activity, not
whether a tool process is alive. No schema migration is needed for monitoring.

`init` copies the monitor and its assets next to `coord.py` and creates one
platform-appropriate root launcher. The launcher is root-relative, uses
Python on PATH, opens the browser, and leaves a terminal available to stop
the server. No Python package installation is required in the target project.

## Transaction boundaries

SQLite connections use autocommit mode, a ten-second busy timeout, and foreign
key enforcement. Schema initialization and root binding occur in one
`BEGIN IMMEDIATE` transaction. Concurrent first writers cannot observe and
initialize a partially created schema.

Every mutating operation acquires the writer lock before reading lifecycle or
ownership state. A claim batch checks active and paused owners and existing
Git changes, then inserts all requested claims and refreshes the task timestamp
within the same transaction. A conflict rolls back the batch. Completion and
checkpoints are serialized too, so a concurrent update cannot reopen a task
that another process has already finished.

Read operations take consistent read transactions. Existing status/inbox
stores open with SQLite's read-only URI mode; they do not create or migrate
schema. Write connections reject unsupported schema versions and existing
unversioned databases containing unrelated or legacy tables.

This protects **register consistency**. Git and external file edits are not
part of a SQLite transaction. A non-cooperating process can edit after Git
inspection or change symlinks between inspection and use. Agents still need
normal diff review and careful handling of concurrent changes.

## Ownership scopes

Claims store a normalized relative path and a kind (`file` or `directory`).
Two claims intersect if their paths are equal or one directory path is a
component-aligned prefix of the other. `src/api` therefore contains
`src/api/router.py` but does not contain `src/api-v2/router.py`.

Paths resolve against the canonical project root before normalization.
Traversal and resolved symlink targets outside the root are rejected.
Case folding is deliberately conservative on every platform: two paths that
differ only by case cannot have competing owners, including on a
case-sensitive filesystem. Git receives original canonical paths with literal
pathspec handling, so bracketed filenames are not treated as patterns.

A directory claim covers its entire subtree. Pause retains claims. Staleness
is a **display hint**, calculated from `updated_at` after 15 minutes; it is
never a lease timeout. Completion changes the task state to `done`; historical
claim rows remain, while conflict checks exclude finished tasks.

## Store isolation and trust

The database metadata binds the store to an absolute canonical project root.
Reusing one store with another clone/root is rejected. This prevents accidental
cross-project state mixing, but is not authentication or a remote sync scheme.
The local filesystem user can edit the database directly, impersonate an
identity, or finish another task. Keep normal filesystem access controls.

Task summaries, messages, and evidence are untrusted caller-provided data.
The skill and text snapshots label them as data. Terminal rendering escapes
controls; it cannot eliminate semantic prompt injection. An agent must not
treat a task card as permission to expand scope or execute arbitrary commands.

## Schema version 1

| Table | Stored information |
| --- | --- |
| `metadata` | Canonical project root |
| `tasks` | ID, agent, summary, optional session reference, state, timestamps, evidence |
| `claims` | Task ID, normalized path, kind |
| `messages` | Sender task, recipient identity, optional recipient task, body, creation/read timestamps |
| `corrections` | Active author task, finished target task, replacement summary, timestamp |

`PRAGMA user_version = 1` identifies the schema. Corrections append records;
the original completion summary remains in `tasks`. This is useful history,
not cryptographic integrity, full event sourcing, or an audit security boundary.
Checkpoints replace the current task summary/evidence; prior checkpoints are
not separately retained.

## Generalization from the original register

The original tool was a project-local coordination script and skill for
Codex, Claude Code, and later Antigravity. Agent Accord preserves its task,
claim, pause, stale ownership, message, completion, and correction semantics.

The standalone version replaces a fixed ancestor-based root with Git root
discovery and explicit `--root`, accepts generic identities, and adds project
installation, packaging, root-bound stores, read-only snapshots, field limits,
foreign keys, literal Git pathspecs, and broader lifecycle transactions. Its
test suite covers real Git changes and independent processes. Project-specific
hooks, private settings, live cards/messages, application code, and database
files were not imported. The original local database is not an import format.

## Deliberate boundaries

This version targets one working tree with shared local filesystem access.
Cross-machine coordination would need a separate service or a purpose-built
replication design, identity/authentication, failure semantics, and a different
root/path model. Copying SQLite sidecars through Git or cloud sync does not
provide those properties.
