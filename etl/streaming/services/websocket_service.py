"""
WebSocket Service - Handles Alpaca WebSocket connection
Business logic for WebSocket lifecycle management
"""
import json
import logging
from typing import Callable, Optional

import websocket

from etl.common.clients.alpaca import AlpacaCredentials
from etl.streaming.adapters.alpaca_adapter import AlpacaAdapter

logger = logging.getLogger(__name__)


class WebSocketService:
    """Service for managing Alpaca WebSocket connection"""
    
    def __init__(
        self,
        on_trade: Callable[[dict], None],
        on_bar: Callable[[dict], None],
        credentials: AlpacaCredentials,
    ):
        """
        Initialize WebSocket service
        
        Args:
            on_trade: Callback function for trade messages
            on_bar: Callback function for bar messages
        """
        self.on_trade = on_trade
        self.on_bar = on_bar
        self.ws: Optional[websocket.WebSocketApp] = None
        self.is_authenticated = False
        self.adapter = AlpacaAdapter()
        self.credentials = credentials
    
    def _on_open(self, ws):
        """Callback when WebSocket opens"""
        logger.info("### WebSocket CONNECTED ###")
        
        # Send authentication
        auth_message = self.adapter.create_auth_message(
            self.credentials.api_key, self.credentials.api_secret
        )
        ws.send(auth_message)
        logger.info("--> Sent authentication")
    
    def _on_message(self, ws, message: str):
        """Callback when message received"""
        try:
            messages = self.adapter.parse_message(message)
            if not messages:
                return
            
            for data in messages:
                # Handle authentication success
                if self.adapter.is_authentication_success(data):
                    logger.info("\n### AUTHENTICATED ###")
                    self.is_authenticated = True
                    
                    # Subscribe to channels
                    subscribe_message = self.adapter.create_subscribe_message(self.credentials.symbols)
                    ws.send(subscribe_message)
                    logger.info(f"--> Subscribed to trades and bars for {self.credentials.symbols}")
                
                # Handle subscription confirmation
                elif self.adapter.is_subscription_confirmation(data):
                    logger.info("\n### SUBSCRIPTION CONFIRMED ###")
                    logger.info(f"    Trades: {data.get('trades', [])}")
                    logger.info(f"    Bars: {data.get('bars', [])}")
                    logger.info("=" * 50)
                    logger.info("Streaming data...")
                    logger.info("=" * 50)
                
                # Handle trade data
                elif self.adapter.is_trade(data):
                    trade = self.adapter.transform_trade(data)
                    self.on_trade(trade)
                
                # Handle bar data
                elif self.adapter.is_bar(data):
                    bar = self.adapter.transform_bar(data)
                    self.on_bar(bar)
        
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")
    
    def _on_error(self, ws, error):
        """Callback when WebSocket error occurs"""
        logger.error(f"### WebSocket ERROR ###\n{error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Callback when WebSocket closes"""
        logger.warning(f"### WebSocket CLOSED (Code: {close_status_code}, Msg: {close_msg}) ###")
    
    def start(self):
        """Start WebSocket connection"""
        logger.info(f"Connecting to {self.credentials.data_ws_url}...")
        
        self.ws = websocket.WebSocketApp(
            self.credentials.data_ws_url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )
        
        # Run forever (will auto-reconnect on disconnect)
        self.ws.run_forever()
    
    def close(self):
        """Close WebSocket connection"""
        if self.ws:
            self.ws.close()
        logger.info("WebSocket service closed")

