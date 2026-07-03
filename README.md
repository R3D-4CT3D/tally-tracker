# Tally

A privacy-first, self-hosted household finance tracker — bills, debt, and savings,
with manual CSV/paste import (no bank-credential linking) and moderate gamification
(streaks, debt "boss" HP bars, savings quests, monthly Close the Books).

Full product spec: [`docs/TALLY_BUILD_SPEC.md`](docs/TALLY_BUILD_SPEC.md). Product principles (what we will
never do for engagement's sake): [`docs/product-principles.md`](docs/product-principles.md).
Architecture decisions: [`docs/adr/`](docs/adr/).

Status: **M0 — repo scaffold & CI pipeline** (see spec §8 for the full milestone plan).

## Repo layout

```
backend/    FastAPI app (Python 3.12, SQLAlchemy 2.x async, Alembic, uv)
frontend/   React + TypeScript + Vite PWA
deploy/     docker-compose.yml, Caddyfile, .env.example
docs/       spec, ADRs, product principles
```

## Local development

### Backend

```sh
cd backend
uv sync
uv run ruff check .
uv run mypy .
uv run pytest
```

Migrations (needs a running Postgres; see `deploy/.env.example` for `DATABASE_URL`):

```sh
uv run alembic upgrade head
```

### Frontend

```sh
cd frontend
npm ci
npm run lint
npm run build
npm run test
```

### Full stack (Docker Compose)

```sh
cp deploy/.env.example deploy/.env   # fill in secrets
docker compose -f deploy/docker-compose.yml --env-file deploy/.env up --build
```

This brings up `caddy` (reverse proxy + static frontend), `api` (FastAPI), `db`
(Postgres 16), and `redis`. Nothing binds to a public interface by design — intended
access is over a Tailscale tailnet (or `localhost` for dev). See `docs/TALLY_BUILD_SPEC.md` §6 for
the full deployment model.

## CI

Every PR runs backend lint/type/test, frontend lint/type/test, Semgrep SAST,
`pip-audit` + `npm audit`, gitleaks, and a Trivy scan of the built images. See
`.github/workflows/ci.yml`.
