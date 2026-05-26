--
-- Open Water Platform - database schema (baseline).
--
-- Hand-written snapshot matching
-- migrations/20260526000000_initial_devices_and_readings.sql. dbmate
-- auto-maintains this file from `dbmate up` onwards via pg_dump; the
-- first applied migration will replace this baseline with the canonical
-- pg_dump output. The diff will be cosmetic (formatting, ordering).
--

--
-- Required extensions.
--

CREATE EXTENSION IF NOT EXISTS timescaledb;

--
-- Tables.
--

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

--
-- TimescaleDB hypertable conversion.
--

SELECT create_hypertable('readings', 'recorded_at');

--
-- Indexes.
--

CREATE INDEX idx_readings_parameter_recorded_at
    ON readings (parameter, recorded_at DESC);

--
-- dbmate migration tracking. Records the initial migration as already
-- applied so a database seeded directly from this baseline is in sync
-- with migrations/. On a clean database, the first `dbmate up` will
-- create this row naturally.
--

CREATE TABLE schema_migrations (
    version VARCHAR(255) PRIMARY KEY
);

INSERT INTO schema_migrations (version) VALUES ('20260526000000');
