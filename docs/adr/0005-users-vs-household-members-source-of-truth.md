# 5. `household_members` is the sole source of truth for membership/role

## Status

Accepted

## Context

`docs/TALLY_BUILD_SPEC.md` §5's schema sketch lists `household_id` and `role`
columns on *both* `users` and `household_members`. Taken literally, that's two
places that could independently record which household a user belongs to and
what role they hold there — a data-consistency hazard (they could disagree),
not a deliberate design.

The spec itself explains why `household_members` exists: "membership as its
own table (users may belong to one household in V1; the join table
future-proofs multi-household)." That statement only makes sense if
`household_members` is authoritative — a `users.household_id` column would be
actively wrong the moment a user belongs to more than one household, which is
exactly the case the join table exists to support later.

## Decision

`household_members(household_id, user_id, role)` is the sole source of truth
for membership and role. `users` holds only identity: `email` (globally
unique — one account per email across the instance), `display_name`,
`password_hash`, `totp_secret`, timestamps. No `household_id` or `role` column
on `users`.

## Consequences

- Every authorization check derives `household_id` and `role` from
  `household_members` (in M1, cached into the Redis session payload at login
  time — see `app/core/security.py`'s `SessionData` — not re-queried per
  request).
- When multi-household support actually lands, no migration is needed to
  "remove the now-wrong `users.household_id`" — the schema was already correct
  for N households from M1 onward.
- A user with zero `household_members` rows (shouldn't normally happen in V1,
  since accounts are only created via `/setup` or invite-accept, both of which
  create the membership row atomically) is, by construction, not a member of
  anything and every household-scoped route correctly rejects them.
