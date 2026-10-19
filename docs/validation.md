# Validation and release readiness

Prepared on **2026-10-19**. This is local verification evidence, not a claim
that remote CI, public distribution, or every agent's UI integration has run.

## Verified locally

Environment: Windows, CPython **3.11.13**, Git **2.46.2.windows.1**.

| Check | Result |
| --- | --- |
| Unit/integration suite against source | 40 tests passed; no skips |
| Same suite against the installed wheel in a fresh environment | 40 tests passed; no skips |
| Built-wheel installation in a fresh virtual environment | Passed with `--no-index --no-deps` |
| Built-wheel console/module entrypoints and bundled skill/license | Passed |
| Copied runtime's independent operation in a temporary Git project | Passed |
| Cross-agent claim conflict, completion, and subsequent handoff | Passed in wheel smoke test |
| Python docstring audit over runtime and tests | Passed in strict mode |
| Skill frontmatter/name validation | Passed |
| Wheel contents | Package/runtime/skill/license and distribution metadata only |

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

## Release boundaries

- No GitHub repository, remote, commit, tag, push, release, or PyPI upload was
  created by the preparation task. The local Git repository starts on `main`.
- Runtime coordination is local to one working tree. The tests do not prove
  distributed coordination or safety on network/cloud-sync filesystems.
- CLI interactions are tested; automatic skill discovery and hook loading
  must be checked in the specific installed agent/version. No live Codex,
  Claude Code, or Antigravity session was driven by the tests.
- The source project's application files, private settings, database records,
  agent histories, credentials, and customer data are outside this extraction.
  Local development stores and generated copies are ignored in this repository.
- Version 0.1.0 is an unreleased initial version. Review CI results and the
  owner-side publishing checklist in the README before making a public release.
