"""
Kafka Producer - Modular Architecture
Receives data from Alpaca WebSocket and publishes to:
- Redis (for real-time UI delivery)
- Kafka (for durable persistence)
"""
import logging
import sys

from etl.common.clients.alpaca import get_alpaca_credentials
from etl.common.clients.kafka_client import KafkaClient
from etl.common.clients.redis_client import RedisClient
from etl.common.logging import configure_logging
from etl.streaming.config.settings import (
    KAFKA_BOOTSTRAP_SERVERS,
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
)
from etl.streaming.services.websocket_service import WebSocketService
from etl.streaming.services.publisher_service import PublisherService

configure_logging()
logger = logging.getLogger(__name__)


def main():
    """Main entry point for producer"""
    try:
        credentials = get_alpaca_credentials()
    except ValueError as exc:
        logger.error(str(exc))
        sys.exit(1)
    
    # Initialize infrastructure clients
    try:
        kafka_client = KafkaClient(KAFKA_BOOTSTRAP_SERVERS)
        redis_client = RedisClient(REDIS_HOST, REDIS_PORT, REDIS_DB)
    except Exception as e:
        logger.error(f"Failed to initialize clients: {e}")
        sys.exit(1)
    
    # Initialize publisher service
    publisher = PublisherService(kafka_client, redis_client)
    
    # Define callbacks for WebSocket messages
    def on_trade(trade_data):
        """Callback when trade received"""
        publisher.publish_trade(trade_data)
    
    def on_bar(bar_data):
        """Callback when bar received"""
        publisher.publish_bar(bar_data)
    
    # Initialize WebSocket service
    websocket_service = WebSocketService(on_trade, on_bar, credentials)
    
    try:
        logger.info("Starting producer...")
        websocket_service.start()
    except KeyboardInterrupt:
        logger.info("\n\nShutting down...")
    finally:
        websocket_service.close()
        publisher.close()
        logger.info("Producer stopped")


if __name__ == "__main__":
    main()
