"""
Kafka Consumer for Trades - Database Persistence
Reads trade data from Kafka and writes to PostgreSQL
"""
import json
import logging
import sys
from datetime import datetime

from kafka import KafkaConsumer

from etl.common.logging import configure_logging
from etl.streaming.config.settings import (
    KAFKA_BOOTSTRAP_SERVERS,
    TOPIC_TRADES,
    CONSUMER_GROUP_TRADES,
    DB_CONFIG,
    BATCH_SIZE
)
from etl.streaming.infrastructure.database_client import DatabaseClient

configure_logging()
logger = logging.getLogger(__name__)


class TradesConsumer:
    """Consumer for processing trade messages from Kafka"""
    
    def __init__(self):
        """Initialize Kafka consumer and database client"""
        # Initialize database client
        self.db_client = DatabaseClient(DB_CONFIG)
        
        # Initialize Kafka consumer
        self.consumer = KafkaConsumer(
            TOPIC_TRADES,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id=CONSUMER_GROUP_TRADES,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            api_version=(0, 10, 1)
        )
        logger.info(f"✓ Kafka Consumer connected: {CONSUMER_GROUP_TRADES}")
        logger.info(f"  Subscribed to: {TOPIC_TRADES}")
        
        self.trade_batch = []
        self.batch_size = BATCH_SIZE
    
    def process_trade(self, trade_data: dict):
        """
        Process a single trade message
        
        Args:
            trade_data: Trade data dictionary
        """
        try:
            symbol = trade_data.get('symbol')
            if not symbol:
                logger.warning("Trade data missing symbol, skipping")
                return
            
            # Get or create stock_id
            stock_id = self.db_client.get_or_create_stock_id(symbol)
            if not stock_id:
                logger.warning(f"Could not get stock_id for {symbol}, skipping")
                return
            
            # Convert timestamp from milliseconds to datetime
            timestamp_ms = trade_data.get('timestamp')
            if not timestamp_ms:
                logger.warning(f"Trade data missing timestamp for {symbol}, skipping")
                return
            
            ts = datetime.fromtimestamp(timestamp_ms / 1000)
            price = trade_data.get('price')
            size = trade_data.get('size')
            
            # Add to batch
            self.trade_batch.append((
                stock_id,
                ts,
                price,
                size
            ))
            
            logger.debug(f"← Trade: {symbol} @ ${price}")
            
            # Batch insert when batch is full
            if len(self.trade_batch) >= self.batch_size:
                self.flush_trades()
        
        except Exception as e:
            logger.error(f"Error processing trade: {e}")
    
    def flush_trades(self):
        """Flush trade batch to database"""
        if not self.trade_batch:
            return
        
        try:
            self.db_client.batch_insert_trades(self.trade_batch)
            self.trade_batch = []
        except Exception as e:
            logger.error(f"Error flushing trades: {e}")
            self.trade_batch = []
    
    def consume(self):
        """Start consuming messages from Kafka"""
        logger.info("\n" + "=" * 60)
        logger.info("Trades Consumer Started - Listening for messages...")
        logger.info("=" * 60 + "\n")
        
        try:
            for message in self.consumer:
                trade_data = message.value
                self.process_trade(trade_data)
        
        except KeyboardInterrupt:
            logger.info("\n\nShutting down consumer...")
            self.flush_trades()
            self.close()
        except Exception as e:
            logger.error(f"Error in consumer loop: {e}")
            self.close()
            raise
    
    def close(self):
        """Close all connections"""
        if self.consumer:
            self.consumer.close()
        if self.db_client:
            self.db_client.close()
        logger.info("Trades consumer closed")


def main():
    """Main entry point"""
    consumer = TradesConsumer()
    
    try:
        consumer.consume()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

