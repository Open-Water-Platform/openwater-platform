"""Open Water Platform ingestion service.

Subscribes to MQTT, validates sensor readings against the v1 payload schema,
and dispatches them downstream. See ``ingestion/README.md`` for the topic
and payload contract.
"""

__version__ = "0.1.0"
