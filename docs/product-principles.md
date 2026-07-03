# Product Principles

These are load-bearing constraints, not aspirations. Any feature or copy change that
violates one of these should be rejected in review, regardless of how well it drives
engagement.

## Ethical gamification constraint (brand-defining)

Retention mechanics exist to serve the user's financial health — never engagement for
its own sake. Concretely, in this codebase:

- **No dark patterns.** No countdowns, "X people looking at this," or manufactured
  friction to delay actions the user actually wants (canceling a bill, deleting an
  account, exporting data).
- **No fake urgency.** Streaks, quests, and celebrations reflect real progress the user
  made. Never simulate scarcity or invent deadlines to drive a session.
- **No pay-to-win.** There is no monetization path in V1, and if one is ever added,
  it must not gate financial-health features (categorization, dedup, budgeting,
  export) behind payment.
- **No shame mechanics.** A missed week costs a streak freeze, never a guilt message.
  Spending copy is descriptive, never judgmental. See §3.2 (Forgiveness mechanics) and
  §4.5 (streak freeze copy: "Streak freeze used — we've got you.") in `docs/spec.md`.
- **Forgiveness over punishment.** Every mechanic that can "break" (a streak, a budget,
  a grade) has a soft landing built in from the start, not bolted on after users
  complain.

## Privacy stance

- Self-hosted instances send **nothing** to any external service, ever. This is a
  brand promise, not a default that gets flipped later. See the `track()` no-op
  interface convention in `docs/adr/` once it's added in M5/M6.
- Manual CSV/paste import is a trust feature, not a limitation. Bank-credential
  linking is out of scope for V1 and opt-in only if it ever ships.

## When in doubt

If a mechanic would feel manipulative if the user found out exactly how it worked,
it doesn't ship.
