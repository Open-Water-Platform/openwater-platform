# Open Water Platform - Ingestion Service

A Python service that subscribes to the MQTT broker, validates incoming
sensor readings against the v1 payload contract, and writes them to the
database. See [`docs/system_architecture.md`](../docs/system_architecture.md#ingestion-service)
for where this component sits in the overall system.

> **Status.** Subscription, validation, and durable database writes are
> implemented. The `status` and `commands` topics, broker authentication
> hardening, and service-specific Postgres roles are tracked as
> follow-ups.

Durability: each event is written under a two-layer policy. In-process
retries (exponential backoff) handle short DB blips locally; if those
are exhausted the message is **not** acknowledged to the broker, so MQTT
QoS 1 redelivers it on the next reconnect. The composite primary key on
`readings` makes redelivery a free no-op.

## Requirements

- Python 3.11 or newer.
- An MQTT broker the service can reach (any MQTT v3.1.1/v5 broker; locally
  [Mosquitto](https://mosquitto.org/) from [`infra/docker/`](../infra/docker/) is the easiest).
- A reachable PostgreSQL database with the project's migrations applied.
  Locally: bring up the stack in [`infra/docker/`](../infra/docker/) and
  apply migrations via the `dbmate` tools profile (see
  [`database/README.md`](../database/README.md)).

## Install

From the repository root:

```bash
pip install -e ingestion/
```

This installs the runtime dependencies (`aiomqtt`, `asyncpg`, `pydantic`,
`pydantic-settings`) and registers the `owp-ingestion` console script.

## Run

Two settings have no defaults: the broker hostname and the database URL.
Everything else is optional.

```bash
export OWP_MQTT_HOST=broker.example.com
export OWP_DATABASE_URL=postgresql://owp:owp@127.0.0.1:5432/owp
owp-ingestion
```

For the default local stack from [`infra/docker/`](../infra/docker/):

```bash
OWP_MQTT_HOST=127.0.0.1 \
OWP_DATABASE_URL=postgresql://owp:owp@127.0.0.1:5432/owp \
owp-ingestion
```

The service opens its database pool at startup; if the database is
unreachable, startup fails fast. Once running, transient DB and broker
failures are handled in-process with exponential backoff and (for the
broker) automatic reconnect, so the service stays up across blips.

## Configuration

All settings are read from environment variables prefixed `OWP_`. A local
`.env` file is also honoured (and is excluded from git via
[`.gitignore`](.gitignore)).

| Variable | Default | Description |
|---|---|---|
| `OWP_MQTT_HOST` | _required_ | Hostname or IP of the MQTT broker. |
| `OWP_MQTT_PORT` | `1883` | TCP port of the MQTT broker. |
| `OWP_MQTT_USERNAME` | _unset_ | Optional username for broker auth. |
| `OWP_MQTT_PASSWORD` | _unset_ | Optional password for broker auth. |
| `OWP_MQTT_TOPIC` | `owp/v1/devices/+/readings` | Topic filter to subscribe to. |
| `OWP_MQTT_CLIENT_ID` | `owp-ingestion` | MQTT client identifier. |
| `OWP_MQTT_QOS` | `1` | QoS level for the subscription (0, 1, or 2). |
| `OWP_RECONNECT_INITIAL_DELAY` | `1.0` | Initial backoff (seconds) after MQTT disconnect. |
| `OWP_RECONNECT_MAX_DELAY` | `30.0` | Maximum backoff between MQTT reconnects. |
| `OWP_DATABASE_URL` | _required_ | PostgreSQL connection URL for the asyncpg pool. |
| `OWP_DB_POOL_MIN_SIZE` | `1` | Minimum asyncpg pool size. |
| `OWP_DB_POOL_MAX_SIZE` | `5` | Maximum asyncpg pool size. |
| `OWP_DB_COMMAND_TIMEOUT` | `10.0` | Per-statement timeout (seconds); surfaces as a retryable error. |
| `OWP_DB_WRITE_MAX_ATTEMPTS` | `10` | Max in-process write attempts before relying on broker redelivery. |
| `OWP_DB_WRITE_INITIAL_DELAY` | `1.0` | Initial backoff (seconds) between write retries. |
| `OWP_DB_WRITE_MAX_DELAY` | `30.0` | Maximum backoff between write retries. |
| `OWP_LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`). |

## MQTT contract (v1)

This is the contract the firmware on each sensor device must follow. It
lives here until the dedicated `schemas/` directory exists; at that point
the canonical JSON Schema will be generated from
[`owp_ingestion/models.py`](owp_ingestion/models.py).

### Topics

| Topic | Direction | QoS | Notes |
|---|---|---|---|
| `owp/v1/devices/{device_id}/readings` | device publishes | 1 | Sensor data. Subscribed to by this service. |
| `owp/v1/devices/{device_id}/status` | device publishes, retained | 1 | Online/offline LWT. **Not yet handled by this service.** |
| `owp/v1/devices/{device_id}/commands` | device subscribes | 1 | Phase 2 downlink (calibration, sleep, OTA). |

Why this shape:

- `owp/` namespace keeps the broker free for other tenants and tooling.
- `v1/` lets the payload evolve without breaking deployed firmware.
- `devices/{device_id}/...` is a per-device subtree, which makes per-device
  ACLs straightforward when broker authentication lands.
- One topic per **event** (not per parameter) keeps a single reading
  atomic and aligns all parameters under one timestamp.

### Reading payload (v1)

Payload is UTF-8 JSON. Example:

```json
{
  "device_id": "owp-0001",
  "timestamp": "2026-05-24T19:22:30Z",
  "firmware_version": "0.1.0",
  "location": { "lat": 12.34, "lon": 56.78 },
  "readings": [
    { "parameter": "temperature", "value": 21.5,  "unit": "C" },
    { "parameter": "ph",          "value": 7.2,   "unit": "pH" },
    { "parameter": "flow_rate",   "value": 1.4,   "unit": "L/min" },
    { "parameter": "volume",      "value": 124.0, "unit": "L" }
  ]
}
```

Rules:

- `device_id` is required and must match the `{device_id}` segment of the
  topic. The service logs a warning on mismatch but still accepts the
  event so deployments are not blocked by minor topic/payload drift.
- `timestamp` is ISO-8601. UTC (with `Z` or `+00:00`) is strongly
  preferred; naive timestamps are accepted but downstream consumers may
  assume UTC.
- `firmware_version` and `location` are optional.
- `readings` is a non-empty list of `{parameter, value, unit}`. Devices
  include only the parameters they actually measure.
- Unknown top-level or per-reading fields are **rejected** so new payload
  versions surface as validation errors rather than silently losing data.

## For the firmware contributor

If you are writing the device firmware:

- Publish JSON reading events to `owp/v1/devices/{your_device_id}/readings`
  at QoS 1.
- Use the payload shape documented above. The authoritative model is
  [`owp_ingestion/models.py`](owp_ingestion/models.py); when in doubt, the
  Pydantic model wins.
- The `status` topic (LWT) and the `commands` topic are part of the design
  but **not yet consumed** by this service. They will be wired up in
  follow-up changes; you can publish a retained `status` payload now and
  it will simply sit on the broker harmlessly.
- For local testing you can use any MQTT broker. With Mosquitto installed
  you can sanity-check this service without firmware via `mosquitto_pub`:

  ```bash
  mosquitto_pub -h 127.0.0.1 -t 'owp/v1/devices/owp-0001/readings' -m '{
    "device_id": "owp-0001",
    "timestamp": "2026-05-24T19:22:30Z",
    "readings": [{"parameter":"temperature","value":21.5,"unit":"C"}]
  }'
  ```

## Layout

```
ingestion/
├── pyproject.toml
├── README.md
└── owp_ingestion/
    ├── __init__.py
    ├── config.py        # Settings (pydantic-settings)
    ├── models.py        # ReadingEvent / Reading / Location
    ├── db.py            # asyncpg pool, idempotent writes, retry wrapper
    ├── mqtt_client.py   # aiomqtt subscribe + validate + manual ack
    └── main.py          # asyncio entrypoint + reconnect supervisor
```

## License

Apache-2.0 - see the repository [`LICENSE`](../LICENSE).
