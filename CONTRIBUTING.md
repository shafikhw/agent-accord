# Contributing to Agent Accord

Useful contributions improve real coordination outcomes: clearer ownership,
reliable concurrency, smaller context snapshots, reproducible handoffs, and
installation that respects an existing project.

## Work locally

```sh
python -m venv .venv
# Activate .venv using your shell's normal activation command.
python -m pip install -e .
python -m unittest discover -s tests -v
python -m pip wheel . --no-deps
```

Tests use temporary Git repositories and their own SQLite files. They do not
need an LLM, network access, API key, or service. Symlink tests may be skipped
when the host cannot create symlinks; verify them on a permitted environment
before changing path-boundary logic. See [validation](docs/validation.md).

## Coordinate changes to this repository

Read `AGENTS.md`. If multiple agents share your checkout, initialize the local
skill with `python src/agent_accord/cli.py init`, then use its status, task,
and claim workflow. The repository ignores that generated development copy;
edit the canonical source in `src/agent_accord/` and rerun `init --upgrade`
after reviewing a change. Do not commit local register data.

## Design expectations

- Keep the CLI and portable runtime standard-library only. Introducing a
  dependency, daemon, or remote service changes the project's operating model;
  discuss that scope before implementing it.
- Preserve atomic claim batches, lifecycle serialization, dirty-work
  protection, and the rule that staleness does not release ownership.
- Never add a silent force-claim, auto-adoption, automatic Git reset/commit,
  or background message acknowledgement.
- Treat all summary/message fields as untrusted data. Keep them out of shell
  interpolation and do not turn task cards into executable instructions.
- Document new or changed modules/functions with their inputs, meaningful
  outputs, expected failures, and side effects. Type new Python interfaces.
- Update the CLI reference, skill, tests, and changelog when contracts change.
  Keep root `LICENSE` and packaged `src/agent_accord/LICENSE` synchronized.
- Test observable behavior, especially independent processes and real Git
  state. A mock returning success does not establish safe concurrent editing.

Any database change needs a deliberate schema-version and compatibility plan.
Never apply development migrations to a real project's register to prove them.
Use fixtures and temporary stores. Old project-local private registers are not
automatically compatible with the public schema.

## Pull requests and issues

Describe the concrete trigger, current result, expected behavior, and relevant
test evidence. Include OS, Python/Git versions, and a minimal reproduction for
bugs. Remove paths, prompts, customer data, credentials, and live task contents
from examples. Prefer synthetic task cards. Keep changes focused and state
which platforms were actually tested.

The issue and PR templates are starting points. Security-sensitive reports
should follow [SECURITY.md](SECURITY.md). Be respectful and specific in
reviews; assess the change, not the contributor.

## Release checklist

1. Update the version in `pyproject.toml`, `src/agent_accord/__init__.py`, and
   the standalone `VERSION` constant in `cli.py` together.
2. Update the changelog and skill/docs for changed behavior.
3. Run the suite and inspect skipped tests. Confirm CI on supported platforms.
4. Build a wheel and test it in a clean virtual environment, then run
   `python tests/smoke_package.py` using that environment's Python.
5. Inspect wheel contents and Git's publishable file list for private data.
6. Publish/tag only with the repository owner's approval. No automated publish
   job is included in this project.
