"""
Kafka Consumer for Bars - Database Persistence
Reads bar data from Kafka and writes to PostgreSQL
"""
import json
import logging
import sys
from datetime import datetime

from kafka import KafkaConsumer

from etl.common.logging import configure_logging
from etl.streaming.config.settings import (
    KAFKA_BOOTSTRAP_SERVERS,
    TOPIC_BARS,
    CONSUMER_GROUP_BARS,
    DB_CONFIG,
    BATCH_SIZE
)
from etl.streaming.infrastructure.database_client import DatabaseClient

configure_logging()
logger = logging.getLogger(__name__)


class BarsConsumer:
    """Consumer for processing bar messages from Kafka"""
    
    def __init__(self):
        """Initialize Kafka consumer and database client"""
        # Initialize database client
        self.db_client = DatabaseClient(DB_CONFIG)
        
        # Initialize Kafka consumer
        self.consumer = KafkaConsumer(
            TOPIC_BARS,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id=CONSUMER_GROUP_BARS,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            api_version=(0, 10, 1)
        )
        logger.info(f"✓ Kafka Consumer connected: {CONSUMER_GROUP_BARS}")
        logger.info(f"  Subscribed to: {TOPIC_BARS}")
        
        self.bar_batch = []
        self.batch_size = BATCH_SIZE
    
    def process_bar(self, bar_data: dict):
        """
        Process a single bar message
        
        Args:
            bar_data: Bar data dictionary
        """
        try:
            symbol = bar_data.get('symbol')
            if not symbol:
                logger.warning("Bar data missing symbol, skipping")
                return
            
            # Get or create stock_id
            stock_id = self.db_client.get_or_create_stock_id(symbol)
            if not stock_id:
                logger.warning(f"Could not get stock_id for {symbol}, skipping")
                return
            
            # Convert timestamp from milliseconds to datetime
            timestamp_ms = bar_data.get('timestamp')
            if not timestamp_ms:
                logger.warning(f"Bar data missing timestamp for {symbol}, skipping")
                return
            
            ts = datetime.fromtimestamp(timestamp_ms / 1000)
            
            # Add to batch
            self.bar_batch.append((
                stock_id,
                '1m',  # timeframe
                ts,
                bar_data.get('open'),
                bar_data.get('high'),
                bar_data.get('low'),
                bar_data.get('close'),
                bar_data.get('volume'),
                bar_data.get('trade_count'),
                bar_data.get('vwap')
            ))
            
            logger.debug(f"← Bar: {symbol} OHLC [{bar_data.get('open')}->{bar_data.get('close')}]")
            
            # Batch insert when batch is full
            if len(self.bar_batch) >= self.batch_size:
                self.flush_bars()
        
        except Exception as e:
            logger.error(f"Error processing bar: {e}")
    
    def flush_bars(self):
        """Flush bar batch to database"""
        if not self.bar_batch:
            return
        
        try:
            self.db_client.batch_insert_bars(self.bar_batch)
            self.bar_batch = []
        except Exception as e:
            logger.error(f"Error flushing bars: {e}")
            self.bar_batch = []
    
    def consume(self):
        """Start consuming messages from Kafka"""
        logger.info("\n" + "=" * 60)
        logger.info("Bars Consumer Started - Listening for messages...")
        logger.info("=" * 60 + "\n")
        
        try:
            for message in self.consumer:
                bar_data = message.value
                self.process_bar(bar_data)
        
        except KeyboardInterrupt:
            logger.info("\n\nShutting down consumer...")
            self.flush_bars()
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
        logger.info("Bars consumer closed")


def main():
    """Main entry point"""
    consumer = BarsConsumer()
    
    try:
        consumer.consume()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

