-- Owner: ingestion
-- Created: 2026-05-26 UTC
-- Tables touched: devices (create), readings (create + hypertable)
--
-- Creates the two tables the ingestion service writes to. Per
-- docs/system_architecture.md, both tables are owned by ingestion:
-- other services may read but must not write. Write-side enforcement
-- (via per-service Postgres roles) is tracked as a follow-up.

-- migrate:up
CREATE TABLE devices (
    device_id         TEXT PRIMARY KEY,
    first_seen_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    firmware_version  TEXT,
    location_lat      DOUBLE PRECISION,
    location_lon      DOUBLE PRECISION,
    CONSTRAINT location_lat_range
        CHECK (location_lat IS NULL OR location_lat BETWEEN -90  AND 90),
    CONSTRAINT location_lon_range
        CHECK (location_lon IS NULL OR location_lon BETWEEN -180 AND 180)
);

COMMENT ON TABLE devices IS
    'One row per sensor device. Registered by the ingestion service on first message.';

CREATE TABLE readings (
    device_id    TEXT             NOT NULL REFERENCES devices(device_id) ON DELETE RESTRICT,
    recorded_at  TIMESTAMPTZ      NOT NULL,
    parameter    TEXT             NOT NULL,
    value        DOUBLE PRECISION NOT NULL,
    unit         TEXT             NOT NULL,
    PRIMARY KEY (device_id, recorded_at, parameter)
);

COMMENT ON TABLE readings IS
    'Time-series readings. One row per (device, time, parameter). Hypertable on recorded_at.';

-- Convert readings into a TimescaleDB hypertable partitioned on recorded_at.
-- The composite primary key (device_id, recorded_at, parameter) already
-- gives us idempotency on QoS 1 redeliveries via INSERT ... ON CONFLICT.
SELECT create_hypertable('readings', 'recorded_at');

CREATE INDEX idx_readings_parameter_recorded_at
    ON readings (parameter, recorded_at DESC);

-- migrate:down
DROP TABLE IF EXISTS readings;
DROP TABLE IF EXISTS devices;
