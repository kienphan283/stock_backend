# SERVICE BOUNDARY: This service must NOT expose HTTP APIs.
# It only handles Kafka → Postgres → Redis Streams and ETL pipelines.

"""
Market Stream Service
Kafka Consumer + ETL Batch Jobs
"""

import threading
import signal
import sys
from infrastructure.kafka.consumer import KafkaMessageConsumer
from application.services.event_router import EventRouter as MessageProcessor
from infrastructure.redis.publisher import RedisStreamsPublisher
from scheduler import ETLJobScheduler
from shared.python.utils.logging_config import get_logger

# Import shared realtime Kafka topics
from pathlib import Path
ROOT_PATH = Path(__file__).resolve().parent.parent
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))
from shared.realtime.kafka_topics import STOCK_TRADES_TOPIC, STOCK_BARS_TOPIC
from shared.python.utils.env import validate_env

validate_env(["KAFKA_BOOTSTRAP_SERVERS", "DB_PASSWORD"])

logger = get_logger(__name__)

class MarketStreamService:
    def __init__(self):
        self.consumer = None
        self.processor = None
        self.publisher = None
        self.scheduler = None
        self.running = False
    
    def start(self):
        """Start the service"""
        logger.info("Starting Market Stream Service...")
        
        # Initialize components
        self.processor = MessageProcessor()
        self.publisher = RedisStreamsPublisher()
        
        # Start Kafka consumer in background thread
        self.consumer = KafkaMessageConsumer(
            topics=[STOCK_TRADES_TOPIC, STOCK_BARS_TOPIC],
            group_id='market-stream-service'
        )
        self.consumer.connect()
        
        # Start consumer thread
        self.running = True
        consumer_thread = threading.Thread(target=self._consume_loop, daemon=True)
        consumer_thread.start()
        
        # Start ETL scheduler
        self.scheduler = ETLJobScheduler()
        self.scheduler.start()
        
        logger.info("Market Stream Service started")
    
    def _consume_loop(self):
        """Consume messages from Kafka"""
        def process_and_publish(topic, key, value):
            # Process message (write to DB)
            self.processor.process_message(topic, key, value)
            
            # Publish to Redis Streams
            symbol = value.get('symbol')
            if topic == STOCK_TRADES_TOPIC:
                logger.info(f"[Redis] Publishing trade for {symbol}")
                self.publisher.publish_trade(symbol, value)
            elif topic == STOCK_BARS_TOPIC:
                logger.info(f"[Redis] Publishing bar for {symbol}")
                self.publisher.publish_bar(symbol, value)
        
        while self.running:
            try:
                self.consumer.consume(process_and_publish)
            except Exception as e:
                logger.error(f"Error in consume loop: {e}")
                import time
                time.sleep(5)
    
    def stop(self):
        """Stop the service"""
        logger.info("Stopping Market Stream Service...")
        self.running = False
        
        if self.consumer:
            self.consumer.close()
        
        if self.publisher:
            self.publisher.close()
        
        if self.scheduler:
            self.scheduler.stop()
        
        logger.info("Market Stream Service stopped")

def main():
    service = MarketStreamService()
    
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal")
        service.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        service.start()
        
        # Keep main thread alive
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        service.stop()

if __name__ == "__main__":
    main()

