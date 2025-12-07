"""
Kafka Producer Wrapper
Publishes normalized messages to Kafka topics
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure project root is on sys.path (Docker: /app)
ROOT_PATH = Path(__file__).resolve().parent.parent
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

from kafka import KafkaProducer

from config.settings import settings
from shared.python.utils.error_handlers import safe_kafka_call
from shared.python.utils.logging_config import get_logger
from shared.python.utils.retry import retryable

logger = get_logger(__name__)


class KafkaProducerWrapper:
    def __init__(self):
        def _create_producer() -> KafkaProducer:
            return KafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks="all",
                retries=3,
                max_in_flight_requests_per_connection=1,
                api_version=(0, 10, 1),
            )

        producer = safe_kafka_call(
            _create_producer,
            context="producer_init",
            on_error=lambda exc: logger.error(f"Failed to connect to Kafka: {exc}"),
        )
        if producer is None:
            raise RuntimeError("Kafka producer initialization failed")

        self.producer = producer
        logger.info("Kafka Producer connected to %s", settings.KAFKA_BOOTSTRAP_SERVERS)

    @retryable()
    def _send(self, topic: str, key: str, message: dict) -> None:
        self.producer.send(topic, key=key, value=message)
        self.producer.flush()

    def send_trade(self, topic: str, key: str, message: dict):
        """Send trade message to Kafka"""
        safe_kafka_call(
            lambda: self._send(topic, key, message),
            context="send_trade",
            on_error=lambda exc: logger.error(f"Error sending trade to Kafka: {exc}"),
        )

    def send_bar(self, topic: str, key: str, message: dict):
        """Send bar message to Kafka"""
        safe_kafka_call(
            lambda: self._send(topic, key, message),
            context="send_bar",
            on_error=lambda exc: logger.error(f"Error sending bar to Kafka: {exc}"),
        )

    def close(self):
        """Close Kafka producer"""
        safe_kafka_call(
            lambda: self.producer.close(),
            context="producer_close",
            on_error=lambda exc: logger.error(f"Error closing Kafka producer: {exc}"),
        )
        logger.info("Kafka producer closed")

