# 2. M0 tooling choices

## Status

Accepted

## Context

M0 (repo scaffold & CI, see `docs/TALLY_BUILD_SPEC.md` §8) required picking between several
build-time options the spec left open (§10) or offered as either/or (§7).

## Decision

- **Python dependency management: `uv`**, not pip-tools. Single tool for venv +
  lockfile + install, meaningfully faster, and the lockfile format is what the CI
  pipeline and Dockerfile builder stage are written against.
- **Git remote: none yet.** The repo is initialized locally only for M0. No GitHub
  repo was created or pushed to. CI workflow YAML is written and locally validated
  tool-by-tool, but GitHub Actions itself is unverified until a remote exists.
- **Container registry: none yet.** Dockerfiles are written to be multi-arch/buildx
  compatible (amd64 + arm64, per spec §6), and CI builds + Trivy-scans them locally
  (`load: true`, no push). Wiring an actual registry (likely GHCR) is deferred to
  whenever the Pi deploy becomes real, so it isn't done twice.
- **UUIDv7 generation: the `uuid6` PyPI package** (pure Python, no C extension) used
  as the default value factory in `app/models/base.py`. Postgres 16 has no native
  `uuidv7()` function, so IDs are generated application-side. Pure Python (not a
  C-extension package) was chosen specifically because arm64/Raspberry Pi wheel
  availability is a real constraint for this project, not a hypothetical one.

## Consequences

- Whoever wires up the GitHub remote later must also add repository secrets (if any
  scanners need API tokens) and branch protection — neither exists yet.
- If `uuid6` is ever abandoned upstream, swapping the id factory is a single-file
  change (`app/models/base.py`), not a schema migration, since the column type is
  plain `UUID`.
