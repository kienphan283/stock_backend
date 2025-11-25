"""
Configuration settings for Kafka Producer and Consumers
Loads from environment variables with sensible defaults
"""
import os

from etl.common.env_loader import load_root_env

load_root_env()

# Alpaca API Configuration
ALPACA_API_KEY = os.getenv('ALPACA_API_KEY', '')
ALPACA_API_SECRET = os.getenv('ALPACA_API_SECRET', '')
ALPACA_API_BASE_URL = os.getenv('ALPACA_API_BASE_URL', 'https://paper-api.alpaca.markets/v2')
ALPACA_DATA_WS_URL = os.getenv('ALPACA_DATA_WS_URL', 'wss://stream.data.alpaca.markets/v2/iex')

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9093')
TOPIC_TRADES = 'stock_trades_realtime'
TOPIC_BARS = 'stock_bars_staging'

# Redis Configuration (for real-time streaming)
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_DB = int(os.getenv('REDIS_DB', '0'))
REDIS_STREAM_TRADES = 'stock:trades:stream'  # Redis Stream key for trades
REDIS_CHANNEL_TRADES = 'stock:trades:pubsub'  # Redis PubSub channel (alternative)

# Database Configuration
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
if not POSTGRES_PASSWORD:
    raise ValueError("POSTGRES_PASSWORD environment variable is required")
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', '5432')),
    'database': os.getenv('POSTGRES_DB', 'Web_quan_li_danh_muc'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': POSTGRES_PASSWORD
}

# Consumer Configuration
CONSUMER_GROUP_TRADES = 'trades-persistence-group'
CONSUMER_GROUP_BARS = 'bars-persistence-group'
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '100'))

# Subscribed Symbols
SUBSCRIBED_SYMBOLS = os.getenv('SUBSCRIBED_SYMBOLS', 'AAPL,MSFT,GOOGL').split(',')

