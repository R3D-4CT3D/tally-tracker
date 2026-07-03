# 3. Documented Trivy exceptions for the api image

## Status

Accepted

## Context

The first real run of CI on GitHub Actions (not just local tool invocations)
surfaced Trivy findings that local validation couldn't: `python:3.12-slim` OS
packages carry several HIGH/CRITICAL CVEs (`gzip`, `libacl1`, `ncurses`,
`perl-base`/`perl-Archive-Tar`/`perl-IO-Compress`, `libsqlite3-0`, `zlib1g`).

We first tried pinning the base image to `python:3.12-slim-bookworm` (Debian 12)
instead of the floating `slim` tag (which currently resolves to Debian 13
"trixie"), on the theory that trixie was simply a newer, less-patched release.
That made things *worse* (13 findings vs. 11) — bookworm has its own unpatched
set, including `CVE-2023-45853` (zlib) which Debian has marked `will_not_fix`,
and several `perl-Archive-Tar`/`perl-IO-Compress` CVEs marked `fix_deferred`.
These are generic Debian packaging issues, not release-specific, and none of
them are reachable from this application: we never invoke `gzip`, `perl`,
`libacl`, or Python's `sqlite3` stdlib module, and there's no interactive
terminal (`ncurses`) inside the container.

The more thorough fix — a distroless final stage (`gcr.io/distroless/base-debian12`
or `-nonroot`, copying in the self-contained `uv`-built venv and dropping
system packages we don't need entirely) — could not be verified in this
environment: there's no local Docker access here (WSL/Docker Desktop
integration isn't enabled), so pushing an unverified base-image rewrite risked
shipping a container that doesn't boot, with no local way to catch that before
it reached CI or the Pi.

## Decision

Keep `python:3.12-slim-bookworm`. Add `.trivyignore` at the repo root listing
each specific CVE ID with a one-line justification (unreachable code path /
package not used by this application), and pass `trivyignores: .trivyignore`
to the `trivy scan api image` step only (not the caddy/Alpine image scan,
which stays fully strict).

## Consequences

- The container-scan gate is honest about what it's actually checking:
  vulnerabilities in code paths we exercise, not every CVE that happens to
  exist in the base image's package set.
- `.trivyignore` entries must be revisited if reachability assumptions change
  (e.g. if a future feature starts shelling out to `perl` or `gzip`) or once
  upstream ships fixes — remove the corresponding line and let Trivy re-flag it
  to confirm.
- A distroless rewrite remains worth doing once it can be built and smoke-tested
  against a real Docker daemon (e.g. once Docker Desktop's WSL integration is
  enabled here, or directly on the Pi) — this ADR intentionally leaves that as
  a follow-up rather than shipping it unverified.
