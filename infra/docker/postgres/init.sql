-- Postgres bootstrap script for the local-dev container.
--
-- The official TimescaleDB image runs every .sql file in
-- /docker-entrypoint-initdb.d/ exactly once, on the very first container
-- start when the data directory is empty. This file's job is strictly
-- engine-level: enable the TimescaleDB extension so application
-- migrations can create hypertables.
--
-- Application schema (devices, readings, ...) does NOT live here. Per
-- docs/system_architecture.md, each service owns its own tables, and
-- those are managed by versioned migrations alongside the owning
-- service (e.g. ingestion/migrations/).
--
-- To rerun this script after the database already exists, recreate the
-- container with a fresh volume: docker compose down -v.

CREATE EXTENSION IF NOT EXISTS timescaledb;
