# MODULE: Kafka processing pipeline.
# PURPOSE: Route Kafka messages to database writes, no domain logic.

"""
Kafka Message Processor
Processes messages from Kafka and writes to PostgreSQL
"""

from db.writer import DatabaseWriter
from typing import Any, Dict

# Import shared Kafka topic constants
import sys
from pathlib import Path

ROOT_PATH = Path(__file__).resolve().parent.parent
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))
from shared.realtime.kafka_topics import STOCK_TRADES_TOPIC, STOCK_BARS_TOPIC
from shared.python.utils.logging_config import get_logger

logger = get_logger(__name__)


class MessageProcessor:
    def __init__(self):
        self.db_writer = DatabaseWriter()
    
    def process_trade(self, key: str, message: Dict[str, Any]):
        """Process trade message and write to database"""
        try:
            symbol = message.get('symbol')
            price = message.get('price')
            size = message.get('size')
            timestamp = message.get('timestamp')
            
            # Write to stock_trades_realtime table
            self.db_writer.write_trade(symbol, price, size, timestamp)
            logger.info(f"[Processor] Processed trade for {symbol}: price={price}, size={size}")
        except Exception as e:
            logger.error(f"Error processing trade: {e}")
    
    def process_bar(self, key: str, message: Dict[str, Any]):
        """Process bar message and write to database"""
        try:
            symbol = message.get('symbol')
            open_price = message.get('open')
            high = message.get('high')
            low = message.get('low')
            close = message.get('close')
            volume = message.get('volume')
            timestamp = message.get('timestamp')
            
            # Write to stock_bars_staging table
            self.db_writer.write_bar(symbol, open_price, high, low, close, volume, timestamp)
            logger.info(f"[Processor] Processed bar for {symbol}: close={close}, volume={volume}")
        except Exception as e:
            logger.error(f"Error processing bar: {e}")
    
    def process_message(self, topic: str, key: str, value: Dict[str, Any]):
        """Route message to appropriate processor"""
        if topic == STOCK_TRADES_TOPIC:
            self.process_trade(key, value)
        elif topic == STOCK_BARS_TOPIC:
            self.process_bar(key, value)
        else:
            logger.warning(f"Unknown topic: {topic}")

