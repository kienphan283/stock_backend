"""
Kafka Producer - Nhận data từ Alpaca WebSocket và gửi vào Kafka
"""
import websocket
import json
import threading
import time
import os
from kafka import KafkaProducer
from kafka.errors import KafkaError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
ALPACA_WEBSOCKET_URL = "wss://stream.data.alpaca.markets/v2/iex"
API_KEY = os.getenv('ALPACA_API_KEY', 'YOUR_API_KEY_HERE')
SECRET_KEY = os.getenv('ALPACA_SECRET_KEY', 'YOUR_SECRET_KEY_HERE')

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9093')
TOPIC_TRADES = 'stock_trades_realtime'
TOPIC_BARS = 'stock_bars_staging'


class AlpacaKafkaProducer:
    def __init__(self):
        """Initialize Kafka producer and WebSocket connection"""
        # Khởi tạo Kafka Producer
        self.producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            acks='all',  # Đảm bảo message được ghi vào Kafka
            retries=3,
            max_in_flight_requests_per_connection=1,
            api_version=(0, 10, 1)  # Tương thích với Kafka 7.5.0
        )
        print(f"✓ Kafka Producer connected to {KAFKA_BOOTSTRAP_SERVERS}")
        
        self.ws = None
        self.is_authenticated = False
        
    def on_open(self, ws):
        """Callback khi WebSocket mở"""
        print("### WebSocket CONNECTED ###")
        
        # Gửi authentication
        auth_message = {
            "action": "auth",
            "key": API_KEY,
            "secret": SECRET_KEY
        }
        ws.send(json.dumps(auth_message))
        print("--> Sent authentication")
        
    def on_message(self, ws, message):
        """Callback khi nhận message từ Alpaca"""
        try:
            data_list = json.loads(message)
            
            if not isinstance(data_list, list):
                return
                
            for data in data_list:
                msg_type = data.get('T')
                
                # Authentication success
                if msg_type == 'success' and data.get('msg') == 'authenticated':
                    print("\n### AUTHENTICATED ###")
                    self.is_authenticated = True
                    
                    # Subscribe to channels
                    subscribe_message = {
                        "action": "subscribe",
                        "trades": ["AAPL", "MSFT", "GOOGL"],
                        "bars": ["AAPL", "MSFT", "GOOGL"]
                    }
                    ws.send(json.dumps(subscribe_message))
                    print("--> Subscribed to trades and bars")
                    
                # Subscription confirmation
                elif msg_type == 'subscription':
                    print("\n### SUBSCRIPTION CONFIRMED ###")
                    print(f"    Trades: {data.get('trades', [])}")
                    print(f"    Bars: {data.get('bars', [])}")
                    print("=" * 50)
                    print("Streaming data to Kafka...")
                    print("=" * 50)
                    
                # Trade data (t)
                elif msg_type == 't':
                    self.handle_trade(data)
                    
                # Bar data (b)
                elif msg_type == 'b':
                    self.handle_bar(data)
                    
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
        except Exception as e:
            print(f"Error processing message: {e}")
            
    def handle_trade(self, trade_data):
        """Xử lý và gửi trade data vào Kafka"""
        try:
            symbol = trade_data.get('S')  # Ticker symbol
            
            # Chuẩn bị message
            message = {
                'symbol': symbol,
                'price': trade_data.get('p'),
                'size': trade_data.get('s'),
                'timestamp': trade_data.get('t'),
                'exchange': trade_data.get('x'),
                'conditions': trade_data.get('c', [])
            }
            
            # Gửi vào Kafka topic
            future = self.producer.send(
                TOPIC_TRADES,
                key=symbol,
                value=message
            )
            
            # Callback khi gửi thành công
            future.add_callback(
                lambda metadata: print(f"✓ Trade {symbol} @ ${message['price']} -> Kafka")
            )
            future.add_errback(
                lambda e: print(f"✗ Error sending trade: {e}")
            )
            
        except Exception as e:
            print(f"Error handling trade: {e}")
            
    def handle_bar(self, bar_data):
        """Xử lý và gửi bar data vào Kafka"""
        try:
            symbol = bar_data.get('S')  # Ticker symbol
            
            # Chuẩn bị message
            message = {
                'symbol': symbol,
                'open': bar_data.get('o'),
                'high': bar_data.get('h'),
                'low': bar_data.get('l'),
                'close': bar_data.get('c'),
                'volume': bar_data.get('v'),
                'timestamp': bar_data.get('t'),
                'trade_count': bar_data.get('n'),
                'vwap': bar_data.get('vw')
            }
            
            # Gửi vào Kafka topic
            future = self.producer.send(
                TOPIC_BARS,
                key=symbol,
                value=message
            )
            
            # Callback khi gửi thành công
            future.add_callback(
                lambda metadata: print(f"✓ Bar {symbol} OHLC [{message['open']}->{message['close']}] -> Kafka")
            )
            future.add_errback(
                lambda e: print(f"✗ Error sending bar: {e}")
            )
            
        except Exception as e:
            print(f"Error handling bar: {e}")
            
    def on_error(self, ws, error):
        """Callback khi có lỗi WebSocket"""
        print(f"### WebSocket ERROR ###\n{error}")
        
    def on_close(self, ws, close_status_code, close_msg):
        """Callback khi WebSocket đóng"""
        print(f"### WebSocket CLOSED (Code: {close_status_code}, Msg: {close_msg}) ###")
        
    def start(self):
        """Bắt đầu WebSocket connection"""
        print(f"Connecting to {ALPACA_WEBSOCKET_URL}...")
        
        self.ws = websocket.WebSocketApp(
            ALPACA_WEBSOCKET_URL,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        
        # Chạy forever (sẽ tự động reconnect nếu disconnect)
        self.ws.run_forever()
        
    def close(self):
        """Đóng connections"""
        if self.ws:
            self.ws.close()
        if self.producer:
            self.producer.flush()
            self.producer.close()
        print("Producer closed")


def main():
    """Main entry point"""
    # Kiểm tra API keys
    if API_KEY == "YOUR_API_KEY_HERE" or SECRET_KEY == "YOUR_SECRET_KEY_HERE":
        print("=" * 60)
        print("!!! ERROR: Please set ALPACA_API_KEY and ALPACA_SECRET_KEY")
        print("!!! in environment variables or update in code")
        print("=" * 60)
        return
        
    # Khởi tạo và chạy producer
    producer = AlpacaKafkaProducer()
    
    try:
        producer.start()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        producer.close()


if __name__ == "__main__":
    main()
