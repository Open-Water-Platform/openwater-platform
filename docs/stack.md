# Stack

The technology choices for each component of the Open Water Platform. The [system architecture](system_architecture.md) is the source of truth for *what* each component does; this document records *what we build it with*.

| Layer | Stack | Why |
|---|---|---|
| Sensor firmware | ESP32 + PlatformIO (C++) | Cheap hardware, built-in Wi-Fi and MQTT, large community. |
| MQTT broker | Eclipse Mosquitto | Off-the-shelf, lightweight, Apache/EPL-licensed. EMQX if clustering is needed. |
| Ingestion service | Python + `aiomqtt` + Pydantic | Same language as the API and future ML service; strong validation. |
| Database | PostgreSQL + TimescaleDB (Apache-licensed features only) | One DB for time-series readings and relational data, per the architecture. |
| API backend | Python + FastAPI | Shares models and migrations with the ingestion service. |
| Dashboard | React + TypeScript + Vite | Standard frontend stack, fully open source, no vendor lock-in. |
| ML service (Phase 2) | Python + scikit-learn / PyTorch + FastAPI | Where the ML ecosystem lives; reuses backend schemas. |
|

Python across ingestion, API, and ML keeps the backend in one language and matches the audience of utilities, researchers, and community groups.
