# Open Water Platform — Backend

A Python service that exposes a read-only REST API for devices and sensor
readings stored by the ingestion service. See
[`docs/system_architecture.md`](../docs/system_architecture.md#api-backend)
for where this component sits in the overall system.

> **Status.** Read-only MVP endpoints for devices and readings are
> implemented. User authentication and write endpoints are planned follow-ups.

The backend never writes to `devices` or `readings`; ingestion owns those
tables per the architecture table-ownership rules.

## Requirements

- Python 3.11 or newer.
- A reachable PostgreSQL database with the project's migrations applied.
  Locally: bring up the stack in [`infra/docker/`](../infra/docker/) and
  apply migrations via the `dbmate` tools profile (see
  [`database/README.md`](../database/README.md)).

## Install

From the repository root:

```bash
cd backend
uv sync --all-extras
```

This installs runtime dependencies (`fastapi`, `uvicorn`, `asyncpg`,
`pydantic`, `pydantic-settings`) and registers the `owp-backend` console
script.

## Run

Copy [`.env.example`](.env.example) to `.env` and adjust if needed, or export
`OWP_DATABASE_URL` manually. The database URL is required in configuration;
the server starts even when Postgres is temporarily unreachable (see
`/health` vs `/health/ready`).

```bash
cp .env.example .env   # omit on Windows: copy .env.example .env
owp-backend
```

Or set the URL inline for the default local stack from
[`infra/docker/`](../infra/docker/):

```bash
OWP_DATABASE_URL=postgresql://owp:owp@127.0.0.1:5432/owp owp-backend
```

OpenAPI documentation is served at `http://127.0.0.1:8000/docs`.

With Docker Compose (from `infra/docker/` after `docker compose up -d`):

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/v1/devices
```

## Configuration

All settings are read from environment variables prefixed `OWP_`. A local
`.env` file is also honoured (and is excluded from git via
[`.gitignore`](.gitignore)).

| Variable | Default | Description |
|---|---|---|
| `OWP_DATABASE_URL` | _required_ | PostgreSQL connection URL for the asyncpg pool. |
| `OWP_HOST` | `0.0.0.0` | HTTP bind address. |
| `OWP_PORT` | `8000` | HTTP port. |
| `OWP_DB_POOL_MIN_SIZE` | `1` | Minimum asyncpg pool size. |
| `OWP_DB_POOL_MAX_SIZE` | `10` | Maximum asyncpg pool size. |
| `OWP_DB_COMMAND_TIMEOUT` | `10.0` | Per-statement timeout (seconds). |
| `OWP_LOG_LEVEL` | `INFO` | Logging level. |
| `OWP_CORS_ORIGINS` | `http://localhost:5173` | Comma-separated allowed CORS origins. |
| `OWP_READINGS_DEFAULT_LIMIT` | `100` | Default page size for readings lists. |
| `OWP_READINGS_MAX_LIMIT` | `1000` | Maximum readings page size. |
| `OWP_DEVICES_DEFAULT_LIMIT` | `50` | Default page size for device lists. |
| `OWP_DEVICES_MAX_LIMIT` | `200` | Maximum devices page size. |

## API (v1)

Base path: `/api/v1`. All list endpoints return `{ items, limit, offset, total }`.

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness probe |
| `GET` | `/health/ready` | Readiness probe (checks database) |
| `GET` | `/api/v1/devices` | Paginated device list |
| `GET` | `/api/v1/devices/{device_id}` | Single device metadata |
| `GET` | `/api/v1/devices/{device_id}/readings` | Paginated readings (`from`, `to`, `parameter`, `order`) |
| `GET` | `/api/v1/devices/{device_id}/readings/latest` | Latest reading per parameter |

## Tests

```bash
cd backend
uv run pytest tests/unit -v
```

See [`docs/testing.md`](../docs/testing.md) for project-wide test conventions.

