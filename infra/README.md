# Open Water Platform - Infrastructure

This directory holds the deployment artefacts the platform's services
depend on (broker, database, eventually production manifests). It does
**not** hold application schema or migrations - those live alongside the
owning service per [docs/system_architecture.md](../docs/system_architecture.md#database).

| Subdirectory | Purpose | Target environment |
|---|---|---|
| [`docker/`](docker/) | Docker Compose stack for the MQTT broker and the database. | Local development. |
| _(future)_ `helm/` | Kubernetes charts for production deployment. | Production. |
| _(future)_ `terraform/` | Cloud infrastructure provisioning. | Production. |

> Production deployment is intentionally not part of this slice. When it
> lands it will be a sibling subdirectory of `docker/`, not a
> replacement for it - local dev via Docker Compose stays the standard
> contributor onboarding path.

## `docker/` - local development stack

Two containers, both pinned to specific image versions for
reproducibility:

- **`mosquitto`** - the [Eclipse Mosquitto](https://mosquitto.org/) MQTT
  broker on `tcp://127.0.0.1:1883`. Anonymous access for local dev only;
  see the explicit warning in
  [`docker/mosquitto/mosquitto.conf`](docker/mosquitto/mosquitto.conf).
- **`postgres`** - [TimescaleDB](https://www.timescale.com/) (PostgreSQL +
  Timescale extension) on `tcp://127.0.0.1:5432`. Initial bootstrap
  enables the TimescaleDB extension; application tables are added by
  service migrations.

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or
  Docker Engine + Compose on Linux). Docker Compose v2 is required for
  the `docker compose` CLI used below.

### Bring the stack up

```bash
cd infra/docker
cp .env.example .env          # one-time, sets the Postgres credentials
docker compose up -d          # pull images on first run; subsequent runs are instant
```

On the first run Docker pulls the images (~150 MB combined). Subsequent
runs start in a few seconds because images are cached locally.

`restart: unless-stopped` on both services means the containers come
back automatically when Docker Desktop restarts (e.g. after a Windows
reboot), but `docker compose down` will keep them stopped until you
bring them back up explicitly.

### Verify it works

Mosquitto:

```bash
# In one terminal:
docker compose exec mosquitto mosquitto_sub -h 127.0.0.1 -t test/hello

# In another terminal:
docker compose exec mosquitto mosquitto_pub -h 127.0.0.1 -t test/hello -m "it works"
```

Postgres:

```bash
docker compose exec postgres psql -U owp -d owp -c "SELECT extname FROM pg_extension WHERE extname = 'timescaledb';"
```

The `psql` output should list `timescaledb`.

### Stop the stack

```bash
docker compose down           # stop containers, keep data
docker compose down -v        # stop containers AND wipe volumes (nukes the database and retained MQTT messages)
```

### Connection details for services

Other services in this monorepo can connect to the stack with these
defaults (matching `infra/docker/.env.example`):

| Service | Default URL |
|---|---|
| MQTT broker | `tcp://127.0.0.1:1883` (no auth) |
| Postgres | `postgresql://owp:owp@127.0.0.1:5432/owp` |

For the ingestion service specifically, set:

```bash
export OWP_MQTT_HOST=127.0.0.1
# (Postgres wiring lands in a follow-up; the service does not connect to
# the database yet.)
```

## License

Apache-2.0 - see the repository [`LICENSE`](../LICENSE).
