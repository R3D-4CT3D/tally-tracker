# Deploy notes

## Nightly balance-snapshot job

`app/jobs/balance_snapshot.py` computes each household's `cash_cents`/
`debt_cents` for dashboard sparklines. There's no in-process scheduler or
scheduler container in this compose stack — run it via host crontab instead:

```cron
15 3 * * * cd /path/to/debt-tracker && docker compose -f deploy/docker-compose.yml exec -T api python -m app.jobs.balance_snapshot >> /var/log/tally-balance-snapshot.log 2>&1
```

The job is idempotent for a given day (upserts on `household_id, date`), so a
missed or re-run invocation is safe.

This is a small, targeted deploy note for the M4 job specifically — the full
consolidated operator runbook (backup/restore, all scheduled jobs, health
checks) is M7 scope per `docs/TALLY_BUILD_SPEC.md`'s build order, not yet
written here.
