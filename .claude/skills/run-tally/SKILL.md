---
name: run-tally
description: Build, run, and drive the full Tally stack (caddy, api, db, redis via docker compose). Use when asked to start Tally, run its docker compose stack, take a screenshot of its UI, verify a change end-to-end in a browser, or run the Playwright e2e driver.
---

Tally is a docker-compose-orchestrated web app (Caddy reverse proxy +
FastAPI backend + Postgres + Redis). Drive it via
`.claude/skills/run-tally/driver.mjs`, a headless-Chromium Playwright
script — there is no `chromium-cli` in this environment, so this driver
is the harness. All paths below are relative to the repo root.

## Prerequisites

Docker + Docker Compose v2 (`docker compose`, not `docker-compose`).
Node 20 for the driver (the frontend itself also requires it — see
`frontend/.nvmrc`).

Playwright's Chromium needs to be downloaded once per machine (~180MB,
not committed):

```bash
npx --yes playwright install chromium
```

## Setup

Install the driver's own dependencies (kept separate from
`frontend/package.json` — this is agent tooling, not product code):

```bash
cd .claude/skills/run-tally && npm install && cd -
```

## Run (agent path)

`stack.sh` handles the full lifecycle — generating `deploy/.env` with
random secrets, building images, running migrations (the `db` service
has no host-published port by design, so migrations run from *inside*
the compose network via a one-off `api` container, not from the host),
and waiting for the stack to actually answer over HTTPS before
returning:

```bash
bash .claude/skills/run-tally/stack.sh up
```

Then drive the representative auth flow (first-run setup wizard →
`/dashboard` → logout → login → `/dashboard` again) and screenshot each
step:

```bash
node .claude/skills/run-tally/driver.mjs
```

Screenshots land in `.claude/skills/run-tally/screenshots/` (pass a
different directory as the first arg; a second arg overrides the base
URL, default `https://localhost`). On success it prints `DRIVER OK`; on
failure it prints which step failed, saves a `FAILED-<step>.png`, and
exits non-zero.

`/setup` only ever succeeds once per instance — re-running the driver
against a stack that's already been set up will fail at the first step
(it'll see the login page, not the setup wizard). Reset first:

```bash
bash .claude/skills/run-tally/stack.sh reset-db
```

Tear down when done:

```bash
bash .claude/skills/run-tally/stack.sh down
```

| `stack.sh` command | what it does |
|---|---|
| `up` | generate `deploy/.env` if missing, build+start db/redis, migrate, build+start everything, wait for `https://localhost/api/v1/health` |
| `reset-db` | drop and recreate the `tally` database, re-migrate, flush redis — for a fresh first-run state without a full teardown |
| `down` | `docker compose down -v` + remove `deploy/.env` |

## Test

Backend: `cd backend && uv run pytest --cov` (98% coverage on
`app/services` as of M1). Frontend: `cd frontend && npm run test`
(Vitest, mocks the API client — doesn't catch the class of bug the
driver above does; see Gotchas).

## Gotchas

- **A passing Vitest suite does not mean the app works.** The frontend
  tests mock `src/lib/api.ts`, so they never exercise real TanStack
  Query cache reactivity. The M1 logout bug (`queryClient.removeQueries()`
  not forcing already-mounted components to re-render — the dashboard
  kept showing "logged in" after a real, successful server-side logout
  until a manual reload) only surfaced by actually driving a browser
  against the real stack. Always run the driver after frontend changes
  that touch auth/session state, not just the unit tests.
- **`/setup` is one-time per instance.** The driver's first step always
  expects the setup wizard, not the login page. If a previous run left
  the instance set up, `stack.sh reset-db` before re-running — the
  driver won't tell you *why* it failed to find "Set up Tally," it'll
  just time out waiting for that selector.
- **Migrations can't run from the host.** `db` intentionally has no
  `ports:` mapping in `deploy/docker-compose.yml` (only `caddy`
  publishes to the host, by design). `alembic upgrade head` has to run
  via `docker compose run --rm --no-deps api alembic upgrade head`,
  not directly against `localhost:5432`.
- **`backend/Dockerfile` didn't used to copy `alembic.ini`/`alembic/`
  into the image at all** (fixed in the M1 backend commit) — if a
  future Dockerfile edit regresses this, `stack.sh up` will fail at the
  migration step with `No 'script_location' key found in configuration`,
  not an obviously-related error.
- **Self-signed cert.** Caddy's automatic HTTPS uses its own internal
  CA for `localhost`. The driver launches with
  `--ignore-certificate-errors` and `ignoreHTTPSErrors: true` — both
  are needed (the launch arg alone isn't sufficient for Playwright's
  own cert validation).

## Troubleshooting

- **`No 'script_location' key found in configuration`** during
  `stack.sh up`: the `api` image is missing `alembic.ini`/`alembic/`
  (see Gotchas above) — check `backend/Dockerfile` copies them into the
  runtime stage.
- **Driver times out on `text=Set up Tally`**: the instance is already
  set up. Run `stack.sh reset-db` and retry.
- **`ECONNREFUSED` / driver can't reach `https://localhost`**: the
  stack isn't up yet, or `stack.sh up` didn't reach its own health-wait
  loop successfully — check `docker compose -f deploy/docker-compose.yml --env-file deploy/.env ps`
  for a container stuck unhealthy.
