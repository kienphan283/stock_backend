# MODULE: Alpaca WebSocket client.
# PURPOSE: Consume Alpaca realtime feed and publish normalized messages to Kafka.

import websocket
import json
import threading
import time
import sys
from pathlib import Path

from broker.producer import KafkaProducerWrapper
from config.settings import settings
from shared.python.utils.error_handlers import safe_kafka_call
from shared.python.utils.logging_config import get_logger
from shared.realtime.kafka_topics import STOCK_TRADES_TOPIC, STOCK_BARS_TOPIC

logger = get_logger(__name__)

class AlpacaWebSocketClient:
    def __init__(self):
        self.producer = None
        self.ws = None
        self.is_authenticated = False
        self.should_run = True
        
        # Initialize Kafka Producer
        try:
            self.producer = KafkaProducerWrapper()
            logger.info(f"Kafka Producer initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")

    def on_open(self, ws):
        logger.info("WebSocket CONNECTED to Alpaca")
        
        # Validate API keys
        if not settings.ALPACA_API_KEY or not settings.ALPACA_SECRET_KEY:
            logger.error("ALPACA_API_KEY or ALPACA_SECRET_KEY not configured")
            ws.close()
            return
        
        auth_message = {
            "action": "auth",
            "key": settings.ALPACA_API_KEY,
            "secret": settings.ALPACA_SECRET_KEY
        }
        
        ws.send(json.dumps(auth_message))
        logger.info("Sent authentication to Alpaca")

    def on_message(self, ws, message):
        try:
            data_list = json.loads(message)
            if not isinstance(data_list, list): 
                return

            for data in data_list:
                msg_type = data.get('T')
                if msg_type == 'success' and data.get('msg') == 'authenticated':
                    self.is_authenticated = True
                    subscribe_message = {
                        "action": "subscribe",
                        "trades": settings.SUBSCRIBE_SYMBOLS,
                        "bars": settings.SUBSCRIBE_SYMBOLS
                    }
                    ws.send(json.dumps(subscribe_message))
                    logger.info(f"Subscribed to trades and bars for {settings.SUBSCRIBE_SYMBOLS}")
                elif msg_type == 't':
                    self.handle_trade(data)
                elif msg_type == 'b':
                    self.handle_bar(data)
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def handle_trade(self, trade_data):
        if not self.producer:
            return

        symbol = trade_data.get("S")
        message = {
            "symbol": symbol,
            "price": trade_data.get("p"),
            "size": trade_data.get("s"),
            "timestamp": trade_data.get("t"),
            "type": "trade",
        }

        safe_kafka_call(
            lambda: self.producer.send_trade(STOCK_TRADES_TOPIC, symbol, message),
            context="handle_trade",
            on_error=lambda exc: logger.error(f"Error handling trade: {exc}"),
        )

    def handle_bar(self, bar_data):
        if not self.producer:
            return

        symbol = bar_data.get("S")
        message = {
            "symbol": symbol,
            "open": bar_data.get("o"),
            "high": bar_data.get("h"),
            "low": bar_data.get("l"),
            "close": bar_data.get("c"),
            "volume": bar_data.get("v"),
            "timestamp": bar_data.get("t"),
            "type": "bar",
        }

        safe_kafka_call(
            lambda: self.producer.send_bar(STOCK_BARS_TOPIC, symbol, message),
            context="handle_bar",
            on_error=lambda exc: logger.error(f"Error handling bar: {exc}"),
        )

    def on_error(self, ws, error):
        logger.error(f"WebSocket ERROR: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        logger.info(f"WebSocket CLOSED: {close_status_code} - {close_msg}")

    def start(self):
        websocket.enableTrace(False)
        self.ws = websocket.WebSocketApp(
            settings.ALPACA_WS_URL,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        self.ws.run_forever()

    def stop(self):
        self.should_run = False
        if self.ws:
            self.ws.close()
        if self.producer:
            self.producer.close()

