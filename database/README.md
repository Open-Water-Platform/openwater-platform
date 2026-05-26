# Open Water Platform - Database

This directory holds the platform's **database schema** and the
**migrations** that evolve it. The database itself runs as a container
under [`infra/docker/`](../infra/docker/) (per [`docs/system_architecture.md`](../docs/system_architecture.md#database)); this directory describes what lives inside that database.

Migrations are written in plain SQL and applied with
[dbmate](https://github.com/amacneil/dbmate). dbmate runs as a one-shot
Docker Compose service so contributors do not need to install anything
new beyond Docker.

## Rules

- **`migrations/`** - one SQL file per change, ordered by a UTC timestamp
  prefix (`YYYYMMDDHHMMSS`). dbmate applies any file in this folder whose
  version is not yet recorded in the `schema_migrations` table.
- **`schema.sql`** - the full current schema as one readable SQL file.
  Auto-maintained by dbmate via `pg_dump` after every migration, and the
  source of truth when you want a single-file view of the data model.

## Prerequisites

The Postgres + TimescaleDB container from
[`infra/docker/`](../infra/docker/) must be running:

```bash
cd infra/docker
cp .env.example .env       # one-time
docker compose up -d
```

The TimescaleDB extension is enabled by
[`infra/docker/postgres/init.sql`](../infra/docker/postgres/init.sql) at
first container start, which is what `migrations/...initial_devices_and_readings.sql` relies on when it calls `create_hypertable`.

## Workflow

All commands run from `infra/docker/`. The `tools` profile keeps dbmate
out of the default `docker compose up` while still letting it share the
compose network so it can reach the `postgres` service by name.

### Apply pending migrations

```bash
docker compose --profile tools run --rm dbmate up
```

After every successful apply, dbmate rewrites
[`schema.sql`](schema.sql) via `pg_dump`. Commit the updated file
together with the new migration.

### Create a new migration

```bash
docker compose --profile tools run --rm dbmate new <slug>
```

Produces an empty migration file at
`database/migrations/<timestamp>_<slug>.sql`. Edit it to add your
`-- migrate:up` and `-- migrate:down` sections, then `dbmate up`.

Each new migration **must** include a top-of-file comment block:

```sql
-- Owner: <service that owns the tables touched>
-- Created: YYYY-MM-DD UTC
-- Tables touched: <table> (create|alter|drop), ...
```

### Check status

```bash
docker compose --profile tools run --rm dbmate status
```

Lists pending and applied migrations.

### Reset everything

```bash
docker compose down -v                                          # drops the data volume
docker compose up -d                                            # fresh DB
docker compose --profile tools run --rm dbmate up               # reapplies all migrations
```

### Running dbmate natively (optional)

If you would rather not go through Docker, install dbmate locally and
point it at the running container:

```bash
# install (Windows: scoop install dbmate; macOS: brew install dbmate; Linux: see project README)
export DATABASE_URL="postgres://owp:owp@127.0.0.1:5432/owp?sslmode=disable"
cd database
dbmate up
```

The compose-based path stays the recommended default because it pins the
dbmate version for every contributor.


## License

Apache-2.0 - see the repository [`LICENSE`](../LICENSE).
