# 4. Documented Trivy exceptions for the caddy image (temporary, upstream lag)

## Status

Accepted

## Context

Once the api image's Trivy scan passed (docs/adr/0003), the caddy image's scan
ran for the first time (it had been skipped in every prior CI run because the
api scan failed first, and GitHub Actions skips subsequent steps by default
after a failure). It found 2 HIGH CVEs in the `caddy` Go binary itself:
`CVE-2026-27145` (crypto/x509 DoS via DNS name constraint processing) and
`CVE-2026-42504` (mime header decoding DoS), both in the Go standard library,
fixed in Go 1.25.11/1.26.4.

We confirmed via the Docker Hub API that `caddy:2-alpine` (digest
`sha256:5f5c8640...`, built 2026-06-24) is genuinely the current latest —
there is no newer tag or digest published yet. The Go patch releases came out
after Caddy's last image build. Unlike the backend's OS-package exceptions
(`gzip`/`perl`/`ncurses`/etc., which are permanently unreachable code paths),
this is a temporary timing gap: a fix exists, we just can't pull an image that
contains it yet.

## Decision

Add `.trivyignore-caddy` (separate from the backend's `.trivyignore`, to keep
the two natures of exception distinguishable) listing both CVE IDs with the
above rationale, wired into the `trivy scan caddy image` CI step only.

## Consequences

- This file should be short-lived. Once Caddy publishes a new `2-alpine` build
  against a patched Go toolchain, remove the ignore file (or its two lines) and
  let Trivy re-verify — do not treat this the same as the backend's longer-lived
  exceptions.
- If Dependabot's `docker` ecosystem watch on `/deploy` picks up a new
  `caddy:2-alpine` digest before this is manually revisited, that PR is the
  natural trigger to also delete `.trivyignore-caddy`.
