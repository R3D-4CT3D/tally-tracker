#!/usr/bin/env bash
# Lifecycle helper for the full Tally docker compose stack (caddy, api, db,
# redis). Run from anywhere; paths are resolved relative to this script.
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SKILL_DIR/../../.."   # repo root

COMPOSE_ARGS=(-f deploy/docker-compose.yml --env-file deploy/.env)

up() {
  if [ ! -f deploy/.env ]; then
    "$SKILL_DIR/gen-env.sh"
  fi

  docker compose "${COMPOSE_ARGS[@]}" up -d --build db redis
  echo "waiting for db + redis to be healthy..."
  timeout 30 bash -c "
    until [ \"\$(docker compose ${COMPOSE_ARGS[*]} ps db --format '{{.Health}}')\" = healthy ] \
       && [ \"\$(docker compose ${COMPOSE_ARGS[*]} ps redis --format '{{.Health}}')\" = healthy ]; do
      sleep 1
    done
  "

  # db has no host-published port (only caddy does, by design) -- migrations
  # must run from inside the compose network via a one-off api container.
  docker compose "${COMPOSE_ARGS[@]}" build api
  docker compose "${COMPOSE_ARGS[@]}" run --rm --no-deps api alembic upgrade head

  docker compose "${COMPOSE_ARGS[@]}" up -d --build
  echo "waiting for the stack to answer over HTTPS..."
  timeout 60 bash -c 'until curl -sk -o /dev/null https://localhost/api/v1/health; do sleep 1; done'
  echo "stack is up at https://localhost (self-signed cert -- ignoreHTTPSErrors in Playwright)"
}

down() {
  docker compose "${COMPOSE_ARGS[@]}" down -v
  rm -f deploy/.env
}

reset_db() {
  # Wipes all data and re-applies migrations from scratch, without tearing
  # down the containers -- useful between e2e runs that need a fresh
  # first-run (setup wizard) state, since /setup only ever succeeds once.
  docker compose "${COMPOSE_ARGS[@]}" exec -T db psql -U tally -d postgres \
    -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='tally' AND pid <> pg_backend_pid();"
  docker compose "${COMPOSE_ARGS[@]}" exec -T db psql -U tally -d postgres -c "DROP DATABASE tally;"
  docker compose "${COMPOSE_ARGS[@]}" exec -T db psql -U tally -d postgres -c "CREATE DATABASE tally OWNER tally;"
  docker compose "${COMPOSE_ARGS[@]}" run --rm --no-deps api alembic upgrade head
  docker compose "${COMPOSE_ARGS[@]}" exec -T redis sh -c 'redis-cli -a "$REDIS_PASSWORD" FLUSHALL' >/dev/null
}

case "${1:-}" in
  up) up ;;
  down) down ;;
  reset-db) reset_db ;;
  *)
    echo "usage: $0 {up|down|reset-db}" >&2
    exit 1
    ;;
esac
