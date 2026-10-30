# Validation and release readiness

The suite uses temporary Git repositories, isolated SQLite stores, and a
loopback HTTP server. It verifies the coordination protocol and portable
monitor without reading or changing a user's project register.

## Verified locally

Environment: Windows, CPython **3.11.13**, Git **2.46.2.windows.1**.

| Check | Result |
| --- | --- |
| Unit/integration suite against source | 55 tests passed; no skips |
| Same suite against the installed wheel in a fresh environment | 55 tests passed; no skips |
| Built-wheel installation in a fresh virtual environment | Passed with `--no-index --no-deps` |
| Built-wheel console/module entrypoints and bundled skill/license | Passed |
| Copied runtime's independent operation in a temporary Git project | Passed |
| Cross-agent claim conflict, completion, and subsequent handoff | Passed in wheel smoke test |
| Python docstring audit over runtime and tests | Passed in strict mode |
| Skill frontmatter/name validation | Passed |
| Monitor routes and live snapshots | Read-only responses, asset allowlist, origin checks, and error states passed |
| Generated Windows launcher | Executed from another directory with a space-containing project path; root and flags verified |
| Browser UI | Filters, search, details, corrections, messages, light/dark themes, and disconnected-state behavior checked |
| Wheel contents | CLI, monitor, dashboard assets, skill/license, and distribution metadata |

The suite uses real temporary Git projects and SQLite files. It covers
directory and batch conflicts, staged/untracked/ignored work, explicit
adoption, component-aligned directory prefixes, conservative case aliases,
literal Git pathspecs, planned paths, stale/paused ownership, lifecycle
finality, inbox boundaries, and append-only completion corrections.

Concurrent tests use separate database connections and independent CLI
processes. They verify a single winner for competing claims, simultaneous
first-time database writers, and a finish/checkpoint race that cannot reopen
a completed task. Installation tests check preservation of existing
instructions, conflict preflight, explicit upgrades, root discovery from
subdirectories/unrelated directories, and clean read-only startup behavior.

Windows path-boundary tests use directory junctions when creating symlinks
requires privileges. Both claim containment and installation containment were
exercised locally. On a host permitting neither link type, those tests report
explicit skips; do not interpret skipped tests as passed boundary checks.

The distribution check installs the built wheel into a disposable virtual
environment, without the source tree on `PYTHONPATH`. It then verifies the
console entrypoint, module entrypoint, installed resources, and a copied
runtime's claim/handoff lifecycle. Package, standalone runtime, and installed
distribution versions must agree.

## Reproduce

```sh
python -m pip install -e .
python -m unittest discover -s tests -v
python -m pip wheel . --no-deps --wheel-dir dist
```

For the package check, create a separate virtual environment, install the
wheel from `dist` with `--no-index --no-deps`, and run
`python tests/smoke_package.py` using that environment's Python. Do not point
`PYTHONPATH` at `src` during the wheel check. The full unittest suite can also
run against the installed wheel from that environment.

## CI prepared, not yet executed remotely

`.github/workflows/ci.yml` tests Windows, macOS, and Linux on Python 3.10 and
3.13. Each job installs the package, runs the suite, builds a wheel, reinstalls
that wheel without network access, and runs the distribution smoke test. The
workflow has read-only repository contents permissions and no publishing step.

The workflow uses the v7 major versions shown in the official
[checkout usage](https://github.com/actions/checkout#usage) and
[setup-python usage](https://github.com/actions/setup-python#basic-usage),
checked while preparing this repository. Hosted-runner execution remains to
be confirmed after the first push. macOS/Linux and other Python versions were
not locally exercised in this preparation.

## Verification boundaries

Runtime coordination is local to one working tree. The tests do not prove
distributed coordination or safety on network/cloud-sync filesystems.
Automatic skill discovery and hook loading depend on the installed agent;
the suite invokes CLI processes rather than driving real coding-agent sessions.

Monitor HTTP tests verify fresh external-writer updates, unchanged SQLite bytes,
unchanged message acknowledgement state, empty stores, bounded messages,
loopback binding, rejected foreign origins/mutation methods, and fixed asset
routes. The generated launcher test executes the actual OS shell and Python
entrypoint; a separate copied-runtime test starts the real HTTP server.

Browser checks use synthetic cards for active, paused, stale, completed, and
corrected work. HTML-looking message text is displayed literally. Activity
reports only stored publications; it does not establish process liveness.
Windows browser behavior and a narrow desktop layout were checked locally;
other desktop launcher behavior, phone layouts, and OS/browser combinations
remain platform-specific verification targets.

See [CONTRIBUTING.md](../CONTRIBUTING.md) for release checks. A passing local
run is separate from hosted CI results and public package distribution.
