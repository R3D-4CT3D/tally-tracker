# 1. Record architecture decisions

## Status

Accepted

## Context

Tally is built with an explicit ambition to become a hosted product. Decisions made
early (session storage, dependency tooling, deployment shape) are expensive to
reverse once real user data exists. `docs/TALLY_BUILD_SPEC.md` §7 asks for 3-5 short ADRs as
decisions are made.

## Decision

We use lightweight Architecture Decision Records, one file per decision, numbered
sequentially in `docs/adr/`. Each ADR has four sections: Status, Context, Decision,
Consequences. Superseding a decision means writing a new ADR that references the old
one, not editing history.

## Consequences

Future contributors (including future us) can see *why* something is the way it is
without archaeology through commit history.
