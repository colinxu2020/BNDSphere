# Migrations

Autogenerate a revision:

```bash
MESSAGE="describe the change" docker compose --profile autorevision up alembic-autorevision
```

## Before you merge: N-1 compatibility

The deploy workflow can roll the application back one version without
rolling back the database. A migration shipped in release N must leave the
schema usable by application N-1.

Full policy and review checklist: `docs/architecture/database.md`.

Short version: **never drop in the same release you stop using something.**
Add and backfill in N, stop reading the old shape in N+1, drop in N+2.
