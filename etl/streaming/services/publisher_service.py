"""
Publisher Service - Coordinates publishing to Redis and Kafka
Business logic for data distribution
"""
import logging
from typing import Dict, Any

from etl.common.clients.kafka_client import KafkaClient
from etl.common.clients.redis_client import RedisClient
from etl.streaming.config.settings import (
    TOPIC_TRADES, TOPIC_BARS,
    REDIS_CHANNEL_TRADES, REDIS_STREAM_TRADES
)

logger = logging.getLogger(__name__)


class PublisherService:
    """Service for publishing data to Redis and Kafka"""
    
    def __init__(self, kafka_client: KafkaClient, redis_client: RedisClient):
        """
        Initialize publisher service
        
        Args:
            kafka_client: Kafka client instance
            redis_client: Redis client instance
        """
        self.kafka_client = kafka_client
        self.redis_client = redis_client
    
    def publish_trade(self, trade_data: Dict[str, Any]):
        """
        Publish trade to both Redis (real-time) and Kafka (persistence)
        
        Args:
            trade_data: Trade data dictionary
        """
        symbol = trade_data.get('symbol')
        if not symbol:
            logger.warning("Trade data missing symbol, skipping")
            return
        
        # Publish to Redis for ultra low-latency UI delivery
        try:
            self.redis_client.publish(REDIS_CHANNEL_TRADES, trade_data)
            # Alternative: use Redis Streams
            # self.redis_client.add_to_stream(REDIS_STREAM_TRADES, trade_data)
        except Exception as e:
            logger.error(f"Error publishing trade to Redis: {e}")
        
        # Publish to Kafka for durable persistence
        try:
            self.kafka_client.publish(TOPIC_TRADES, symbol, trade_data)
            logger.debug(f"✓ Trade {symbol} @ ${trade_data.get('price')} -> Kafka")
        except Exception as e:
            logger.error(f"Error publishing trade to Kafka: {e}")
    
    def publish_bar(self, bar_data: Dict[str, Any]):
        """
        Publish bar to Kafka (for persistence and charting)
        
        Args:
            bar_data: Bar data dictionary
        """
        symbol = bar_data.get('symbol')
        if not symbol:
            logger.warning("Bar data missing symbol, skipping")
            return
        
        # Publish to Kafka for persistence
        try:
            self.kafka_client.publish(TOPIC_BARS, symbol, bar_data)
            logger.debug(f"✓ Bar {symbol} OHLC [{bar_data.get('open')}->{bar_data.get('close')}] -> Kafka")
        except Exception as e:
            logger.error(f"Error publishing bar to Kafka: {e}")
    
    def close(self):
        """Close all connections"""
        self.kafka_client.close()
        self.redis_client.close()

