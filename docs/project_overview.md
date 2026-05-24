# Open Water Platform

Open Water Platform is an open-source water quality monitoring system. A hardware sensor device measures water quality parameters along with flow rate and volume level, transmits readings over MQTT, and exposes them through a dashboard for operators and the wider community.

The project is hosted by the Linux Foundation.

## Scope

Sensor devices deployed in the field measure parameters relevant to water quality and movement. Readings are published over MQTT to a broker, ingested into a shared database, and made available through a dashboard so operators can monitor what is happening across their deployments.

The MVP consists of:

- A sensor device that publishes readings over MQTT to the ingestion service
- An ingestion service that gets the data and writes readings to a database
- An API backend that serves data to clients from the database
- A dashboard that displays current and historical readings

Machine learning for anomaly detection, predictive analysis, and many more usecases is a planned for future phases, built on the data the MVP collects.

## Why open source

Open Water Platform exists to provide an open alternative to closed water monitoring platforms. The hardware specifications, data schemas, and code are all open, so utilities, researchers, community groups, and other organisations can deploy, modify, audit, and integrate the system without vendor lock-in.

## See also

- [System Architecture](system_architecture.md)