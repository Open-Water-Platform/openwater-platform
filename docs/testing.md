# Testing

This document is the single source of truth for how the Open Water
Platform is tested. It explains *why* we test, *what* is tested today,
*how* contributors run the suite, and *what* is planned next so each
layer lands deliberately rather than ad-hoc.

It is expected to evolve. When you add a new service or a new test
layer, update this file in the same PR.

## Why we test

The ingestion service makes a hard durability promise documented in
[`ingestion/owp_ingestion/db.py`](../ingestion/owp_ingestion/db.py):
sensor data is never silently dropped. Transient database failures
retry in-process; if those are exhausted the MQTT subscriber withholds
its ack and the broker redelivers later. That kind of behaviour is the
exact kind of thing future contributors will accidentally regress, so
the test suite exists to pin it.

Open Water Platform is also an open source project hosted by the
Linux Foundation. A working test suite plus green CI on every PR is
the baseline a project at this scope is expected to meet, both for
contributor confidence and for downstream operators who need to trust
the code their utility or community deployment depends on.

## Test pyramid for this project

Each service has its own column. Status reflects what is implemented
today versus what is planned in the [Planned next steps](#planned-next-steps)
section below.

| Service / Component | Unit | Integration | End-to-end |
|---|---|---|---|
| Ingestion ([`ingestion/`](../ingestion/)) | implemented | planned | planned |
| Database / migrations ([`database/`](../database/)) | n/a | planned | planned |
| API backend ([`backend/`](../backend/)) | implemented | planned | planned |
| Dashboard | not yet built | not yet built | not yet built |
| Sensor firmware | not yet built | not yet built | not yet built |

Layer definitions used here:

- **Unit** — fast, in-process, no external services. Mocks the
  database, broker, network, and filesystem where needed.
- **Integration** — exercises real adjacent components (a real
  Postgres+TimescaleDB container, a real Mosquitto broker, real
  migrations) but still inside one service boundary.
- **End-to-end** — multiple services running together (ingestion +
  database + API + dashboard) with realistic data flowing through.

## Current state

### Ingestion service unit tests

Live in [`ingestion/tests/unit/`](../ingestion/tests/unit/):

| File | Pins |
|---|---|
| `test_models.py` | The v1 MQTT payload contract: required fields, length/range constraints, `extra="forbid"`, ISO timestamp parsing, the README example payload round-trip. |
| `test_config.py` | The operator-facing `Settings` contract: required env vars, defaults, `OWP_` prefix enforcement, numeric validators, `.env` file loading. |
| `test_db.py` | The "no silent data loss" rule: idempotent connect/close, the device-upsert and reading-insert SQL parameters, the retry budget, exponential backoff with cap, and which exception types are retryable vs. propagated. |
| `test_mqtt_client.py` | The ack/no-ack matrix: ACK on success and on permanently-invalid payloads (non-bytes, malformed JSON, schema violation); no ACK on `WriteFailedError` and on unexpected handler exceptions. |

86 tests total at time of writing; the suite finishes in under a
second.

### Backend service unit tests

Live in [`backend/tests/unit/`](../backend/tests/unit/):

| File | Pins |
|---|---|
| `test_config.py` | The operator-facing `Settings` contract: required env vars, defaults, `OWP_` prefix enforcement, pagination limit validators. |
| `test_schemas.py` | API response models, pagination envelopes, readings query time-range validation. |
| `test_db.py` | Read-only query SQL wiring: pool lifecycle, device and reading list/count/latest helpers. |
| `test_routes.py` | HTTP layer: health probes, device and readings endpoints, 404/422/200 behaviour with mocked database. |

29 tests total at time of writing; the suite finishes in under a
second.

### CI

`.github/workflows/ci.yml` runs the ingestion and backend unit suites on every push
to `main` and every pull request, against Python 3.11 and 3.12, using
uv (`astral-sh/setup-uv@v3`). The lockfile is enforced with
`uv sync --locked`, so a missed `uv lock` after a dependency change
fails CI rather than going unnoticed.

## How to run tests

The recommended workflow is uv-driven so CI and local development run
the exact same commands.

### Prerequisites

- Install uv per the [official installation guide](https://docs.astral.sh/uv/getting-started/installation/).
- Clone the repository.

### Run the ingestion unit suite

```bash
cd ingestion
uv sync --all-extras
uv run pytest tests/unit
```

The first `uv sync` creates `ingestion/.venv/` and installs the
locked versions of every runtime and dev dependency in a few seconds.
Subsequent runs are near-instant because uv caches.

Useful variants:

```bash
uv run pytest tests/unit -v                 # verbose per-test output
uv run pytest tests/unit -k retry           # only tests matching "retry"
uv run pytest tests/unit -m unit            # explicit marker filter
uv run pytest tests/unit --lf               # rerun last failed
uv run pytest tests/unit --cov=owp_ingestion  # one-off coverage report
```

### pip fallback

For contributors who prefer not to install uv, plain pip also works:

```bash
cd ingestion
pip install -e ".[dev]"
pytest tests/unit
```

uv is still the path CI uses; the fallback is documented so the door
stays open for contributors with constrained environments.

### Run the backend unit suite

```bash
cd backend
uv sync --all-extras
uv run pytest tests/unit
```

The first `uv sync` creates `backend/.venv/` and installs the locked
versions of every runtime and dev dependency.

## How CI runs the tests

CI is defined in [`.github/workflows/ci.yml`](../.github/workflows/ci.yml).
On every push to `main` and every pull request:

1. The workflow checks out the repository.
2. `astral-sh/setup-uv@v3` installs uv and warms its cache, keyed on
   `ingestion/uv.lock` so cache invalidation tracks real dependency
   changes.
3. The requested Python version (3.11 or 3.12) is installed by uv.
4. `uv sync --all-extras --locked` installs runtime and dev
   dependencies. The `--locked` flag fails the build if `uv.lock` is
   stale relative to `pyproject.toml`.
5. `uv run pytest tests/unit -v` runs the suite.

`fail-fast: false` lets a failure on one Python version still report
the other; a `concurrency` group cancels stale PR runs when a new
commit is pushed.

### Required-checks and branch protection

The workflow file alone does not block merges. To enforce green CI as
a merge gate, configure branch protection on `main`:

- Repo Settings -> Branches -> Branch protection rules -> *Require status
  checks to pass before merging*.
- Add `ingestion / unit (py3.11)` and `ingestion / unit (py3.12)` as
  required checks.
- Add `backend / unit (py3.11)` and `backend / unit (py3.12)` when
  branch protection is updated for the new service.

For OSS hygiene, also leave *Approval for first-time contributors* on
in repo Settings -> Actions -> General. Workflows on PRs from new
forks then require a one-time maintainer click before running, which
prevents random forks from burning runner minutes.

## Conventions

- Test files are named `test_*.py` and live under `ingestion/tests/unit/`
  (and, later, `ingestion/tests/integration/`).
- Cross-cutting fixtures (`test_settings`, `sample_reading_event`,
  `sample_reading_event_minimal`) live in
  [`ingestion/tests/conftest.py`](../ingestion/tests/conftest.py).
- Mark fast tests `@pytest.mark.unit` and tests that need real services
  `@pytest.mark.integration`. Markers are declared in
  [`ingestion/pyproject.toml`](../ingestion/pyproject.toml); `--strict-markers`
  is enabled so typos fail the run.
- Prefer `@pytest.mark.parametrize` over copy-pasted near-duplicate
  tests.
- Each test should pin one observable contract. Long
  multi-assertion tests are usually a sign the test is doing too much.
- When a test exists to enforce an architectural rule (e.g. "no
  silent data loss"), call that out in the test docstring so the
  *intent* is preserved when the implementation changes.

## For contributors

The contributor rule is short:

- **If you change behaviour, add or update a test.**
- **If you fix a bug, add a regression test that fails on the old
  code and passes on the new code.**

The CI workflow runs on every PR; a green CI is the minimum bar for
merge.

## Planned next steps

The current scope is intentionally narrow so the harness lands
quickly. Each of these is tracked as a follow-up.

1. **Integration tests with `testcontainers-python`.** Spin up real
   Postgres+TimescaleDB and Mosquitto containers in CI, apply
   migrations with `dbmate`, and exercise the full
   "MQTT -> validate -> Postgres" path. The three highest-leverage
   tests to start with are: end-to-end happy path; idempotency under
   duplicate delivery; no-silent-data-loss when the database is
   temporarily unreachable.
2. **Migration round-trip tests via dbmate.** Use the existing
   `dbmate` tools profile in
   [`infra/docker/docker-compose.yml`](../infra/docker/docker-compose.yml)
   to run `dbmate up`, `dbmate down`, then `dbmate up` again in CI.
   Catches broken down-migrations early.
3. **`ruff` lint job.** Replace the ad-hoc style guidance with a
   ruff config in `pyproject.toml` and a CI job that runs
   `uv run ruff check`. Adds a `format` job mirroring `ruff format
   --check`.
4. **`mypy --strict` typecheck job.** The ingestion code already has
   thorough type hints; locking that in with strict mypy in CI is the
   logical next step.
5. **Coverage reporting and a soft `--fail-under` floor.** Start with
   a low floor (e.g. 60%) and ratchet upward. Publish HTML coverage
   as a CI artifact.
6. **Pre-commit hooks.** ruff, mypy on changed files, large-file and
   secret detection, and a check that `uv.lock` is in sync with
   `pyproject.toml`.
7. **End-to-end tests once the API backend and dashboard exist.**
   Compose all services together against the same testcontainers
   stack, drive synthetic devices, and assert dashboard-visible
   state.

When an item from this list lands, move its entry into [Current
state](#current-state), update the [Test pyramid](#test-pyramid-for-this-project)
status, and update the relevant CI workflow file in the same PR.
