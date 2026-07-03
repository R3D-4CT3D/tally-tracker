# TALLY — Household Finance Tracker
## Build Specification for Claude Code

**Version:** 1.1 (V1 MVP Spec — product-scale mindset)
**Initial deployment:** Brandon & Gina's household, self-hosted on Raspberry Pi 5 via Tailscale
**Product ambition:** Build every layer as if this ships to millions of users. V1 runs on a Pi; nothing in the architecture, data model, or code quality should need rework to become a hosted consumer product.
**Working name:** "Tally" — rename freely; keep the name in a single config constant.

---

## 1. Project Overview & Vision

Tally is a web-based household finance tracker for bills, debt, and savings, designed for **solo use by default with optional partner/household sharing**. Its defining design constraint: **users abandon spreadsheets within two months out of boredom.** Therefore retention is the primary product goal, achieved through:

1. **High visual polish** — this must feel like a designed product, not a CRUD app.
2. **Moderate gamification** — weekly check-in streaks, debt "boss" HP bars, savings quests, and a monthly "Close the Books" ceremony. No XP/levels in V1.
3. **Frictionless data entry** — CSV import with saved per-bank mappings, paste-to-parse, and a rules engine that auto-categorizes.

**Product positioning:** privacy-first personal finance. Tally never asks for bank credentials — manual CSV/paste import is a *trust feature*, not a gap. Many users distrust bank-linking apps; "your money data, entered on your terms, stored where you choose" is the differentiator. Bank sync may arrive later as strictly opt-in.

**Platform:** web-first, shipped as an installable **PWA**. One codebase serves phone, tablet, and desktop; users add it to their home screen and it behaves like a native app (own icon, full-screen, fast). Native App Store wrappers are a possible future distribution channel, not a V1 concern.

V1 is deployed on a home lab (Raspberry Pi 5) via Docker Compose and accessed exclusively over a Tailscale tailnet (no public exposure). Despite private deployment, it must be **built to public-internet security standards** (OWASP ASVS L1) because the explicit ambition is a hosted product later. Treat DevSecOps rigor as a first-class requirement, not an afterthought.

### Non-goals for V1 (deferred, but architecture must not preclude them)
- No bank sync / Plaid / screen scraping. Manual import is intentional and on-brand (the import *is* the check-in ritual). Future bank sync, if ever, is opt-in.
- No investment portfolio tracking.
- No AI spending analysis or budgeting advice engine.
- No native mobile apps — installable PWA only.
- No public multi-tenant signup or billing — but the entire stack must be multi-tenant-*ready*: household-scoped data, stateless API, no assumptions of "exactly two users" anywhere in code, copy, or UI.

---

## 2. Users & Access Model

**Core principle: solo-first, sharing optional.** A household has 1..N members. Every feature must work perfectly for a household of one; partner features appear only when a second member exists.

- **First-run setup:** creates the instance, the first household, and its `owner` account.
- **Invite flow (build the real thing, not a seed script):** the owner generates a single-use, expiring invite link/code from Settings → Members. The invitee opens it, creates their account, and joins the household as `member`. This is the exact flow a future hosted product needs — dogfood it now: Brandon sets up, Gina joins via invite.
- Public self-registration is disabled by instance config (`ALLOW_SIGNUP=false` default). The flag exists so a hosted deployment flips it on without code changes.
- Roles: `owner` (manage members, delete household, instance settings) and `member` (full financial access). Enforce on the API, not just UI.
- All financial data is household-scoped and visible to all members. Each user keeps their own login, streak record, and attribution on actions ("Gina imported 34 transactions").
- Member removal and voluntary leave must be handled (reassign nothing — data belongs to the household; audit-log it).
- **Adaptive copy:** UI language never assumes a partner exists. Solo: "Your streak." Two+ members: cooperative framing ("Team streaks"). Gate partner widgets (dual streak display, "review the close" prompt) on member count > 1.

---

## 3. Product & Design Principles

1. **Ritual over chore.** Every session should end with a sense of progress. The app should always surface "what changed since you were last here."
2. **Forgiveness mechanics.** Never punish. A missed week costs a streak freeze, not shame. Copy tone: warm, encouraging, lightly playful. Never guilt-trip about spending.
3. **Motion as feedback.** Micro-animations on key actions (transaction logged, payment applied, goal contribution). Satisfying, fast (< 300ms), respect `prefers-reduced-motion`.
4. **One-glance dashboard.** The home screen answers in 5 seconds: How are we doing? What's due soon? What needs categorizing?
5. **Trust through accuracy.** Deduplication must be bulletproof. One double-counted transaction destroys confidence in the whole tool.
6. **Design system first.** Build a small token-based design system (colors, spacing, type scale, motion durations) before feature UI. Gina (professional motion designer/illustrator) will iterate on it — make tokens easy to edit in one file.

### Visual direction (starting point — expect iteration)
- Warm, cozy, "tally" palette: deep charcoal backgrounds with warm ember/amber accents, or a light "linen" mode. Ship dark + light themes from day one.
- Typography: a characterful display face for numbers/headings (e.g., a geometric or humanist sans with distinctive numerals), quiet sans for body. Tabular numerals for all currency.
- Data viz: consistent, custom-styled charts (Recharts is fine) — no default library styling. Sparklines everywhere numbers trend over time.
- Empty states and celebration screens are designed moments, not afterthoughts. Debt payoff celebration is the crown jewel screen.

---

## 4. Feature Specification — V1

### 4.1 Authentication & Session
- Username/email + password login. Argon2id hashing (via `argon2-cffi`), per-OWASP parameters.
- Sessions: HTTP-only, Secure, SameSite=Lax cookies backed by server-side session store (Redis or DB table). No JWTs in localStorage.
- CSRF protection on all state-changing requests (double-submit token or FastAPI middleware).
- Login rate limiting (e.g., 5 attempts / 15 min per IP+account via `slowapi`).
- Optional TOTP 2FA (nice-to-have; stub the model fields even if UI ships in V2).
- First-run setup wizard: create household, create both user accounts, set currency (USD).

### 4.2 Core financial entities

**Accounts** — checking, savings, credit card, loan, cash. Fields: name, type, institution, current balance (derived or manually set with reconciliation), display color/icon.

**Transactions** — the atomic unit. Fields: date, amount (store as integer cents; never floats), description (raw), normalized_description, category, account, notes, import_batch_id, dedupe_hash, created_by, source (`csv`, `paste`, `manual`).

**Bills (recurring)** — name, amount (fixed or variable), due day, frequency (monthly/quarterly/annual/custom), linked account, autopay flag, category. Bills generate upcoming-due items on the dashboard; marking one paid can create/link a transaction.

**Debts** — name, type (credit card, auto loan, student loan, personal), original balance, current balance, APR, minimum payment, due day. Payments (transactions linked to the debt) reduce current balance. This powers the boss HP bar.

**Savings goals ("Quests")** — name, target amount, target date (optional), linked account (optional), current amount, icon/emoji, cover color. Contributions are transactions or manual entries linked to the goal.

**Categories** — seeded sensible defaults (Housing, Utilities, Groceries, Dining, Transport, Insurance, Subscriptions, Health, Entertainment, Debt Payment, Savings, Income, Misc), user-editable, each with icon + color. Support one level of subcategories max.

**Budgets (light)** — optional monthly target per category. Dashboard shows actual vs. target as a subtle bar, not a nag.

### 4.3 Data ingestion (highest-engineering-quality area)

**CSV Import Wizard:**
1. Upload file (max 5 MB, `.csv` only, validated server-side by content sniffing, not extension).
2. Server parses with tolerant parser (handle BOM, quoted fields, thousands separators, `$`, parentheses-negatives, DD/MM vs MM/DD ambiguity — ask user when ambiguous).
3. Column-mapping UI: auto-detect date/amount/description columns with heuristics; user confirms/corrects.
4. **Saved mapping profiles:** persist mapping per (user-named) source, e.g. "Chase Checking," "Schwab." Next import from that source is one click.
5. Preview table with per-row validation errors and duplicate flags before commit.
6. Commit as an `import_batch` (atomic; batch can be undone/deleted wholesale within 24h).

**Paste-to-parse:** textarea accepting tab- or comma-delimited rows copied from bank sites/emails. Same pipeline as CSV after normalization.

**Deduplication:** `dedupe_hash = SHA-256(household_id | account_id | date | amount_cents | normalized_description)`. On import, exact-hash matches are flagged as duplicates (default: skip, user can override). Also fuzzy-flag same date+amount with similar description for review.

**Rules engine:** rules of the form `IF description matches (contains/starts-with/regex) AND [optional amount range / account] THEN set category [and rename display description]`. Rules run on import. When a user manually recategorizes a transaction, offer one-click "Create rule from this?" Rules are ordered; first match wins; UI to reorder.

**CSV formula-injection defense:** any future CSV *export* must prefix cells starting with `= + - @` with `'`. Note this in code even though export is V2.

### 4.4 Dashboard (home screen)
- Hero row: total cash, total debt, net position — each with 90-day sparkline.
- "Since you were here": new transactions imported by partner, upcoming bills (next 14 days), uncategorized count with one-click triage.
- Debt bosses strip: each debt as a card with HP bar (current/original), APR badge, next due date.
- Quests strip: savings goals with progress bars, milestone ticks at 25/50/75%, projected completion date based on trailing 3-month contribution rate.
- This-month category donut + budget bars.
- Streak widget (both users' weekly streaks side by side, cooperative framing).

### 4.5 Gamification (moderate tier — this exact scope, no more)

**Weekly check-in streak (per user):**
- A week is "checked in" if the user performs ≥1 meaningful action (import, categorize ≥5, log a payment, contribute to a goal, complete monthly close) Mon–Sun.
- Streak freezes: earn 1 per 4 consecutive weeks, bank max 2. A missed week auto-consumes a freeze. Copy: "Streak freeze used — we've got you."
- Streak display: flame/ember motif, current + best.

**Debt bosses:**
- HP bar animates damage on each payment (number ticker + bar chunk). Show "damage dealt this month."
- Payoff = full-screen celebration: confetti/ember burst animation, stats recap (total paid, interest saved vs. minimum-payments-only estimate, days fought), and a permanent trophy in a "Hall of Victories" page. This screen should be genuinely delightful — budget real design time here.
- Milestones at 25/50/75% paid trigger smaller toasts.

**Savings quests:** progress bars, milestone toasts, completion celebration (smaller than debt payoff), trophy on completion.

**Monthly "Close the Books" ceremony:**
- Available from the 1st for the prior month; dashboard nudges until done.
- 4–6 step guided flow: (1) resolve uncategorized, (2) income vs. spend recap with category deltas vs. prior month, (3) debt damage recap, (4) quest progress recap, (5) net-worth delta, (6) month grade (A–D, formula: weighted score of budget adherence, debt paydown vs. minimums, savings rate — tune later; never below D, copy stays kind) + one auto-generated "highlight of the month."
- Completing it counts as check-in for both streaks if both users view it (partner gets a "review the close" prompt).
- Produces a saved monthly report page (V1: in-app only; V2: export/share card).

**Explicitly deferred to V2:** XP, levels, cosmetic unlocks, achievements beyond trophies above.

---

## 5. Data Model (initial schema sketch)

All tables carry `id (UUIDv7)`, `household_id`, `created_at`, `updated_at`. Money is `BIGINT` cents. Use SQLAlchemy 2.x + Alembic migrations from the first commit.

- `households(id, name, currency, settings JSONB)`
- `household_members(id, household_id, user_id, role, joined_at)` — membership as its own table (users may belong to one household in V1; the join table future-proofs multi-household)
- `invites(id, household_id, code_hash, created_by, expires_at, used_by NULL, used_at NULL)`
- `users(id, household_id, email, display_name, password_hash, role, totp_secret NULL, created_at)`
- `sessions(id, user_id, expires_at, ip, user_agent)` (if DB-backed sessions)
- `accounts(id, household_id, name, type, institution, balance_cents, color, icon, archived)`
- `categories(id, household_id, name, parent_id NULL, icon, color, is_system)`
- `transactions(id, household_id, account_id, date, amount_cents, description_raw, description_display, category_id NULL, notes, source, import_batch_id NULL, dedupe_hash UNIQUE(household_id, dedupe_hash), debt_id NULL, goal_id NULL, created_by)`
- `import_batches(id, household_id, user_id, source_profile_id NULL, filename, row_count, imported_count, skipped_dupes, created_at)`
- `import_profiles(id, household_id, name, column_mapping JSONB, date_format, source_hint)`
- `rules(id, household_id, priority, match_type, match_value, amount_min NULL, amount_max NULL, account_id NULL, set_category_id, set_display_name NULL, enabled)`
- `bills(id, household_id, name, amount_cents NULL, is_variable, frequency, due_day, account_id NULL, category_id, autopay, next_due_date, archived)`
- `bill_payments(id, bill_id, transaction_id NULL, due_date, paid_date NULL, amount_cents, status)`
- `debts(id, household_id, name, type, original_balance_cents, current_balance_cents, apr_bps, min_payment_cents, due_day, paid_off_at NULL, archived)`
- `goals(id, household_id, name, target_cents, current_cents, target_date NULL, icon, color, completed_at NULL)`
- `goal_contributions(id, goal_id, transaction_id NULL, amount_cents, date, user_id)`
- `streaks(id, user_id, current_weeks, best_weeks, freezes_banked, last_checkin_week)`
- `checkins(id, user_id, iso_week, actions_count)`
- `monthly_closes(id, household_id, month, completed_by, completed_at, grade, snapshot JSONB)`
- `balance_snapshots(id, household_id, date, cash_cents, debt_cents)` (nightly job; powers sparklines)
- `trophies(id, household_id, kind, ref_id, earned_at, stats JSONB)`
- `audit_log(id, household_id, user_id, action, entity, entity_id, meta JSONB, ip, created_at)` — log auth events, imports, deletions, settings changes.

---

## 6. Architecture & Stack

### Stack
- **Backend:** Python 3.12+, FastAPI, SQLAlchemy 2.x (async), Alembic, Pydantic v2, `argon2-cffi`, `slowapi`, APScheduler (or a lightweight cron container) for nightly snapshot/bill-rollover jobs.
- **Frontend:** React 18 + TypeScript + Vite. TanStack Query for server state, TanStack Router or React Router, Tailwind CSS + design tokens file, Recharts for charts, Framer Motion for micro-animations. Component primitives: Radix UI (accessible) styled with Tailwind.
- **PWA (required in V1):** `vite-plugin-pwa` — web app manifest (name, icons incl. maskable, theme color), service worker with cache-first static assets and network-first API (never cache financial data stale-dangerously; show clear "offline — data may be outdated" state), installable on iOS/Android home screen, proper `apple-touch-icon` and splash handling. Test the add-to-home-screen experience on both iOS Safari and Android Chrome as an acceptance criterion.
- **Database:** PostgreSQL 16.
- **Reverse proxy:** Caddy (automatic internal TLS, security headers) in front of API + static frontend.
- **Deployment:** Docker Compose (`caddy`, `api`, `db`, optional `redis`). Single `.env` for config. Target host: home-lab VM or Raspberry Pi 5 (build multi-arch images: amd64 + arm64).
- **Access:** Tailscale on the host; app bound to tailnet interface only (or host firewall restricting to `tailscale0`). Optionally use Tailscale Serve for TLS + MagicDNS hostname (e.g., `https://tally.tailnet-name.ts.net`). **Nothing listens on public interfaces.**

### Portability requirement
No code may assume Tailscale. All access control lives in the app (auth) + deploy config. Moving to a VPS + Cloudflare Tunnel later must require only infra changes.

### API design
- REST, versioned under `/api/v1/`. OpenAPI docs auto-generated but **disabled outside dev** (`/docs` off in prod).
- Consistent envelope, cursor pagination on transactions, server-side filtering (date range, account, category, uncategorized, search).
- All writes validated with Pydantic; all money as integer cents end-to-end.

### Repo structure (monorepo)
```
tally/
  backend/        # FastAPI app: app/{api,models,schemas,services,jobs,core}
  frontend/       # Vite React app: src/{components,features,design-system,lib}
  deploy/         # docker-compose.yml, Caddyfile, .env.example, backup scripts
  .github/workflows/
  docs/           # this spec, ADRs, runbook
```

---

## 6b. Product-Scale Readiness (build-for-millions checklist)

These cost little now and prevent a rewrite later:

- **Stateless API:** no in-process state (sessions in Redis/DB, jobs in scheduler). Any number of API replicas behind a load balancer must work. The Pi runs one replica; the architecture must not care.
- **12-factor config:** all environment differences via env vars. Zero code branches on "self-hosted vs hosted" beyond documented flags (`ALLOW_SIGNUP`, `INSTANCE_MODE`).
- **Feature flags:** a minimal flags table/config (household-level overrides) so future features can roll out gradually. Ship with 2–3 real flags (e.g., `totp_enabled`, `paste_import`).
- **No two-user assumptions:** code review rule — any constant, query, or copy string assuming exactly two members is a defect.
- **i18n-ready:** all user-facing strings through a translation layer (react-i18next) with English as the only V1 locale. Currency/date formatting via `Intl` APIs keyed to household settings. Retrofitting i18n is brutal; wiring it is cheap.
- **Accessibility:** WCAG 2.1 AA target. Radix primitives help; add keyboard navigation tests for core flows, visible focus states, chart data available in accessible table form, respect `prefers-reduced-motion`.
- **Telemetry stance:** self-hosted instances send **nothing** anywhere, ever — this is a brand promise. Define a thin internal analytics interface (`track(event, props)`) that is a no-op in self-hosted mode, so a future hosted product can add privacy-respecting, opt-in product analytics without touching call sites.
- **Deletion & export:** users can export their household's full data (JSON + CSVs) and delete their account/household completely. This is a GDPR/CCPA requirement for a future hosted product and a trust feature today. (CSV export must implement the formula-injection defense from §4.3.)
- **Performance budgets:** dashboard interactive < 2s on a mid-range phone over Tailscale; transaction list virtualized (assume 10k+ rows after a few years); DB indexes on `(household_id, date)`, `(household_id, category_id)`, dedupe hash.
- **Migration discipline:** every schema change via Alembic, reversible where feasible, tested from a clean database in CI. A hosted product with millions of rows lives or dies on migration hygiene.
- **Ethical gamification constraint (brand-defining):** retention mechanics must serve the user's financial health, never engagement for its own sake. No dark patterns, no fake urgency, no pay-to-win anything, no shame mechanics. Write this into `docs/product-principles.md`.

## 7. Security & DevSecOps Requirements (non-negotiable)

Target: **OWASP ASVS Level 1** compliance. Build as if internet-facing.

**Application security**
- Argon2id password hashing; generic auth error messages; constant-time comparisons.
- Server-side sessions in HTTP-only/Secure/SameSite cookies; session rotation on login; idle timeout 30 days (household app, be reasonable), absolute timeout 90 days.
- CSRF tokens on all mutating routes.
- Authorization check on every query: every ORM query filters by `household_id` derived from the session — never from client input. Write a reusable dependency for this.
- Input validation: Pydantic everywhere; CSV upload limited to 5 MB, content-type sniffed, parsed with hardened parser, per-row validation; reject files with > 10,000 rows in V1.
- Security headers via Caddy: CSP (no inline scripts; Vite build configured accordingly), X-Content-Type-Options, X-Frame-Options DENY, Referrer-Policy, Permissions-Policy.
- Rate limiting on auth and import endpoints.
- No secrets in code or images. `.env` git-ignored; `.env.example` documented; gitleaks pre-commit hook.
- Structured JSON logging (no sensitive values logged — never log passwords, session tokens, or full transaction descriptions at INFO), request IDs, audit_log table for sensitive actions.

**Supply chain & CI (GitHub Actions)**
- Pipeline on every PR: `ruff` + `mypy` (backend), `eslint` + `tsc` (frontend), `pytest` with coverage gate (≥ 80% on services/import pipeline), `npm run test` (Vitest), **Semgrep** SAST, `pip-audit` + `npm audit --audit-level=high`, **Trivy** scan on built images, gitleaks scan.
- Dependabot enabled for pip, npm, docker, and actions.
- Pinned dependencies (`uv` lock or `pip-tools`; `package-lock.json` committed). Pinned action SHAs.
- Images: slim/distroless bases, non-root user, read-only root filesystem where possible, healthchecks defined.
- `main` branch protected; deploys from tagged releases via a small `deploy.sh` (pull images, `docker compose up -d`, run Alembic migrations).

**Data protection & ops**
- Nightly `pg_dump` → encrypted with `age` → shipped off-box via `restic` to Backblaze B2 (or local NAS as fallback). **Test restore procedure and document it in `docs/runbook.md`.** Backups are the single most important ops task for a finance app.
- DB not exposed outside the compose network. Redis (if used) password-protected, internal only.
- Write 3–5 short ADRs (Architecture Decision Records) as decisions are made — good hygiene and portfolio value.

---

## 8. Build Order (suggested milestones for Claude Code)

1. **M0 — Skeleton & pipeline:** repo scaffold, Docker Compose, CI green with all scanners, health endpoints, Caddy + security headers, Alembic baseline. *(Security rails first.)*
2. **M1 — Auth & household:** setup wizard (creates owner + household), login/logout, sessions, CSRF, rate limiting, audit log, **member invite flow (generate/consume single-use expiring invites)**, roles enforcement, household scoping dependency + tests proving cross-household isolation and solo-household behavior.
3. **M2 — Core entities:** accounts, categories (seeded), transactions CRUD, manual entry, transaction list with filters/search/pagination.
4. **M3 — Import pipeline:** CSV wizard, paste-to-parse, mapping profiles, dedupe, import batches with undo, rules engine + "create rule from correction." *(Heaviest testing here — property-based tests on the parser with Hypothesis encouraged.)*
5. **M4 — Bills, debts, goals:** entities, payment linking, bill due generation, nightly snapshot job.
6. **M5 — Dashboard & design system:** tokens, themes, hero metrics with sparklines, strips, donut, uncategorized triage.
7. **M6 — Gamification & polish:** streaks + freezes, boss HP bars + payoff celebration + Hall of Victories, quest milestones, monthly close ceremony, micro-animations, empty states, reduced-motion support.
8. **M7 — Hardening & launch:** backup/restore drill, runbook, seed demo-data command, Lighthouse pass (mobile responsiveness), final ASVS L1 self-checklist in `docs/security-checklist.md`.

Each milestone should end with passing CI, migrations applied cleanly from scratch, and a short demo note in the PR description.

---

## 9. Acceptance Criteria (V1 "done")

- Owner completes first-run setup solo; partner joins via invite link. All features function correctly in a one-member household (no partner-assuming copy or broken widgets).
- Both users can log in from phones via Tailscale hostname; app is fully usable at 390px width; **PWA installs to home screen on iOS Safari and Android Chrome** and launches full-screen.
- Full household data export (JSON + CSVs) downloads successfully; export CSVs are formula-injection safe.
- A Chase CSV and a pasted bill table import correctly; re-importing the same file yields zero duplicates.
- A rule created from a manual correction auto-applies on the next import.
- Recording debt payments animates the HP bar; simulated payoff triggers the celebration and Hall of Victories entry.
- Weekly streak increments, freeze auto-consumes on a missed week (unit-tested with frozen time).
- Monthly close completes end-to-end and stores a snapshot report.
- CI fully green including SAST, dependency and container scans; no HIGH/CRITICAL findings.
- Backup created, encrypted, shipped, and **successfully restored** in a drill.
- No service listens on a public interface; `docs/runbook.md` documents deploy, backup, restore, and user reset.

---

## 10. Open Items for Build-Time Decisions

- Redis vs. DB-backed sessions (either acceptable; prefer simpler unless rate limiting wants Redis anyway).
- Exact grade formula for monthly close (ship a v0 formula behind a single tunable function).
- Final name + logo (Gina). Keep branding in tokens/config.
- Whether bill "mark paid" auto-creates a transaction or links an imported one (recommend: link-first with quick-create fallback).
