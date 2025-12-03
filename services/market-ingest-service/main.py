# SERVICE BOUNDARY: This service must NOT access Postgres or Redis.
# It only consumes Alpaca WebSocket and publishes to Kafka.

"""
Market Ingest Service
Receives Alpaca WebSocket data and publishes to Kafka
"""

from alpaca.manager import AlpacaStreamingManager
import signal
import sys
from shared.python.utils.logging_config import get_logger
from shared.python.utils.env import validate_env

validate_env(["KAFKA_BOOTSTRAP_SERVERS"])

logger = get_logger(__name__)

def main():
    manager = AlpacaStreamingManager()
    
    def signal_handler(sig, frame):
        logger.info("Shutting down...")
        manager.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        logger.info("Starting Market Ingest Service...")
        manager.start()
        
        # Keep main thread alive
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        manager.stop()
        logger.info("Market Ingest Service stopped")

if __name__ == "__main__":
    main()

