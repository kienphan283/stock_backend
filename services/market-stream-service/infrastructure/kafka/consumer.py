"""
Kafka consumer implementation for market-stream-service.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Callable

from kafka import KafkaConsumer

ROOT_PATH = Path(__file__).resolve().parents[2]
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

from config.settings import settings
from shared.python.utils.error_handlers import safe_kafka_call
from shared.python.utils.logging_config import get_logger

logger = get_logger(__name__)


class KafkaMessageConsumer:
    def __init__(self, topics: list, group_id: str = "market-stream-service"):
        self.topics = topics
        self.group_id = group_id
        self.consumer: KafkaConsumer | None = None

    def connect(self) -> None:
        """Connect to Kafka."""

        def _connect() -> KafkaConsumer:
            return KafkaConsumer(
                *self.topics,
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                group_id=self.group_id,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                key_deserializer=lambda k: k.decode("utf-8") if k else None,
                auto_offset_reset="earliest",
                enable_auto_commit=settings.KAFKA_ENABLE_AUTO_COMMIT,
                consumer_timeout_ms=1000,
            )

        consumer = safe_kafka_call(
            _connect,
            context="connect",
            on_error=lambda exc: logger.error(f"Failed to connect to Kafka: {exc}"),
        )
        if consumer is None:
            return

        self.consumer = consumer
        logger.info("Kafka Consumer connected to %s", settings.KAFKA_BOOTSTRAP_SERVERS)
        logger.info("Subscribed to topics: %s", self.topics)

    def consume(self, callback: Callable[[str, bytes | None, dict], None]) -> None:
        """
        Consume messages and call callback for each message.

        callback should be: callback(topic, key, value)
        """
        if not self.consumer:
            self.connect()

        if not self.consumer:
            logger.error("Kafka consumer not available; cannot consume messages")
            return

        def _consume_loop() -> None:
            for message in self.consumer:
                try:
                    logger.info(
                        "[Kafka] Received message on %s: %s",
                        message.topic,
                        json.dumps(message.value, ensure_ascii=False),
                    )
                    callback(message.topic, message.key, message.value)
                    if not settings.KAFKA_ENABLE_AUTO_COMMIT:
                        # Commit offsets only after successful processing
                        self.consumer.commit()
                except Exception as exc:  # noqa: BLE001
                    logger.error("Error processing message: %s", exc)

        safe_kafka_call(
            _consume_loop,
            context="consume",
            on_error=lambda exc: logger.error(f"Kafka error: {exc}"),
        )

    def close(self) -> None:
        """Close Kafka consumer."""
        if not self.consumer:
            return

        safe_kafka_call(
            lambda: self.consumer.close(),
            context="close",
            on_error=lambda exc: logger.error(f"Error closing Kafka consumer: {exc}"),
        )
        logger.info("Kafka consumer closed")

