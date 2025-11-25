"""
Alpaca WebSocket Adapter
Handles Alpaca protocol messages and transforms to internal format
"""
import json
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class AlpacaAdapter:
    """Adapter for Alpaca WebSocket protocol"""
    
    @staticmethod
    def parse_message(message: str) -> Optional[List[Dict[str, Any]]]:
        """
        Parse Alpaca WebSocket message
        
        Args:
            message: Raw JSON string from Alpaca
            
        Returns:
            List of message objects or None if invalid
        """
        try:
            data = json.loads(message)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return [data]
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return None
    
    @staticmethod
    def is_authentication_success(data: Dict[str, Any]) -> bool:
        """Check if message is authentication success"""
        return data.get('T') == 'success' and data.get('msg') == 'authenticated'
    
    @staticmethod
    def is_subscription_confirmation(data: Dict[str, Any]) -> bool:
        """Check if message is subscription confirmation"""
        return data.get('T') == 'subscription'
    
    @staticmethod
    def is_trade(data: Dict[str, Any]) -> bool:
        """Check if message is trade data"""
        return data.get('T') == 't'
    
    @staticmethod
    def is_bar(data: Dict[str, Any]) -> bool:
        """Check if message is bar data"""
        return data.get('T') == 'b'
    
    @staticmethod
    def transform_trade(trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform Alpaca trade message to internal format
        
        Args:
            trade_data: Raw Alpaca trade message
            
        Returns:
            Transformed trade dictionary
        """
        return {
            'symbol': trade_data.get('S'),  # Ticker symbol
            'price': trade_data.get('p'),   # Price
            'size': trade_data.get('s'),    # Size
            'timestamp': trade_data.get('t'),  # Timestamp (milliseconds)
            'exchange': trade_data.get('x'),   # Exchange
            'conditions': trade_data.get('c', [])  # Trade conditions
        }
    
    @staticmethod
    def transform_bar(bar_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform Alpaca bar message to internal format
        
        Args:
            bar_data: Raw Alpaca bar message
            
        Returns:
            Transformed bar dictionary
        """
        return {
            'symbol': bar_data.get('S'),      # Ticker symbol
            'open': bar_data.get('o'),        # Open price
            'high': bar_data.get('h'),        # High price
            'low': bar_data.get('l'),         # Low price
            'close': bar_data.get('c'),        # Close price
            'volume': bar_data.get('v'),       # Volume
            'timestamp': bar_data.get('t'),   # Timestamp (milliseconds)
            'trade_count': bar_data.get('n'), # Number of trades
            'vwap': bar_data.get('vw')        # Volume-weighted average price
        }
    
    @staticmethod
    def create_auth_message(api_key: str, secret_key: str) -> str:
        """Create authentication message"""
        return json.dumps({
            "action": "auth",
            "key": api_key,
            "secret": secret_key
        })
    
    @staticmethod
    def create_subscribe_message(symbols: List[str]) -> str:
        """Create subscription message for trades and bars"""
        return json.dumps({
            "action": "subscribe",
            "trades": symbols,
            "bars": symbols
        })

