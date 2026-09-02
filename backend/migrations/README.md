# Migrations

Autogenerate a revision:

```bash
MESSAGE="describe the change" docker compose --profile autorevision up alembic-autorevision
```

## Before you merge: N-1 compatibility

Migrations run while the old application is still serving (`run_migration`
comes before `recreate_services`), and a failed deploy is left in place for
an operator to recover from by putting the previous version's containers
back — with the schema still at N. Either way, a migration shipped in
release N must leave the schema usable by application N-1.

There is no reverse migration, deliberately. `downgrade()` cannot return the
data a `DROP COLUMN` removed, it is never executed in CI or in production so
it would run for the first time during an incident, and a failed
`upgrade head` already rolls back whole (one transaction) so there is
nothing to undo. Going back is a container swap, never a schema change —
which only holds if drops wait a release.

Full policy, the review checklist and why N+2 -> N+1 does not trip over the
dropped column: `docs/architecture/database.md`.

Short version: **never drop in the same release you stop using something.**
Add and backfill in N, stop reading the old shape in N+1, drop in N+2.
