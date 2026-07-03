#!/usr/bin/env bash
# Generates deploy/.env with random secrets for a local verification run.
# Never commit the output -- deploy/.env is gitignored.
set -euo pipefail
cd "$(dirname "$0")/../../.."

cat > deploy/.env <<EOF
DOMAIN=localhost
ENV=production
INSTANCE_MODE=self_hosted
ALLOW_SIGNUP=false
SESSION_SECRET=$(openssl rand -hex 32)
POSTGRES_USER=tally
POSTGRES_PASSWORD=$(openssl rand -hex 16)
POSTGRES_DB=tally
REDIS_PASSWORD=$(openssl rand -hex 16)
EOF
echo "wrote deploy/.env"
