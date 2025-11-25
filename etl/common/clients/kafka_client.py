"""
Shared Kafka producer wrapper.
"""
import json
import logging
from typing import Any, Dict, Optional

from kafka import KafkaProducer
from kafka.errors import KafkaError

logger = logging.getLogger(__name__)


class KafkaClient:
    def __init__(self, bootstrap_servers: str, **kwargs: Any):
        self.bootstrap_servers = bootstrap_servers
        self.kwargs = kwargs
        self.producer: Optional[KafkaProducer] = None
        self._connect()

    def _connect(self) -> None:
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks="all",
                retries=3,
                max_in_flight_requests_per_connection=1,
                **self.kwargs,
            )
            logger.info("Kafka producer connected to %s", self.bootstrap_servers)
        except Exception:
            logger.exception("Failed to connect to Kafka")
            raise

    def publish(self, topic: str, key: str, value: Dict[str, Any]) -> bool:
        if not self.producer:
            logger.error("Kafka producer not initialized")
            return False

        try:
            self.producer.send(topic, key=key, value=value)
            return True
        except KafkaError:
            logger.exception("Error publishing to Kafka topic %s", topic)
            return False

    def flush(self) -> None:
        if self.producer:
            self.producer.flush()

    def close(self) -> None:
        if self.producer:
            self.producer.flush()
            self.producer.close()
            logger.info("Kafka producer closed")

