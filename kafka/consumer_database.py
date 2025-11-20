"""
Kafka Consumer #1 - Database Persistence
Đọc data từ Kafka và lưu vào PostgreSQL
"""
import json
import os
import psycopg2
from psycopg2.extras import execute_batch
from kafka import KafkaConsumer
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9093')
TOPIC_TRADES = 'stock_trades_realtime'
TOPIC_BARS = 'stock_bars_staging'
CONSUMER_GROUP = 'database-persistence-group'

# Database Configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'Web_quan_li_danh_muc'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '123456')
}


class DatabaseConsumer:
    def __init__(self):
        """Initialize Kafka consumer and database connection"""
        # Kết nối PostgreSQL
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.conn.autocommit = False
        self.cursor = self.conn.cursor()
        print(f"✓ Connected to PostgreSQL: {DB_CONFIG['database']}")
        
        # Khởi tạo Kafka Consumer
        self.consumer = KafkaConsumer(
            TOPIC_TRADES,
            TOPIC_BARS,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id=CONSUMER_GROUP,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',  # Đọc từ đầu nếu chưa có offset
            enable_auto_commit=True,
            api_version=(0, 10, 1)
        )
        print(f"✓ Kafka Consumer connected: {CONSUMER_GROUP}")
        print(f"  Subscribed to: {TOPIC_TRADES}, {TOPIC_BARS}")
        
        self.trade_batch = []
        self.bar_batch = []
        self.batch_size = 100  # Insert mỗi 100 records
        
    def get_or_create_stock_id(self, symbol):
        """Lấy hoặc tạo stock_id từ symbol"""
        try:
            # Kiểm tra symbol đã tồn tại chưa
            self.cursor.execute(
                "SELECT stock_id FROM market_data_oltp.stocks WHERE ticker = %s",
                (symbol,)
            )
            result = self.cursor.fetchone()
            
            if result:
                return result[0]
            
            # Tạo mới nếu chưa có
            self.cursor.execute(
                """
                INSERT INTO market_data_oltp.stocks (ticker, company_name, status)
                VALUES (%s, %s, 'active')
                ON CONFLICT (ticker) DO UPDATE SET ticker = EXCLUDED.ticker
                RETURNING stock_id
                """,
                (symbol, symbol)
            )
            self.conn.commit()
            return self.cursor.fetchone()[0]
            
        except Exception as e:
            self.conn.rollback()
            print(f"Error getting stock_id for {symbol}: {e}")
            return None
    
    def insert_trade(self, trade_data):
        """Insert trade vào database"""
        try:
            symbol = trade_data['symbol']
            stock_id = self.get_or_create_stock_id(symbol)
            
            if not stock_id:
                return
            
            # Chuyển timestamp từ milliseconds sang datetime
            ts = datetime.fromtimestamp(trade_data['timestamp'] / 1000)
            
            self.trade_batch.append((
                stock_id,
                ts,
                trade_data['price'],
                trade_data['size']
            ))
            
            # Batch insert khi đủ số lượng
            if len(self.trade_batch) >= self.batch_size:
                self.flush_trades()
                
        except Exception as e:
            print(f"Error inserting trade: {e}")
    
    def flush_trades(self):
        """Batch insert trades vào database"""
        if not self.trade_batch:
            return
            
        try:
            execute_batch(
                self.cursor,
                """
                INSERT INTO market_data_oltp.stock_trades_realtime 
                (stock_id, ts, price, size)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                self.trade_batch
            )
            self.conn.commit()
            print(f"✓ Inserted {len(self.trade_batch)} trades into database")
            self.trade_batch = []
            
        except Exception as e:
            self.conn.rollback()
            print(f"Error flushing trades: {e}")
            self.trade_batch = []
    
    def insert_bar(self, bar_data):
        """Insert bar vào database"""
        try:
            symbol = bar_data['symbol']
            stock_id = self.get_or_create_stock_id(symbol)
            
            if not stock_id:
                return
            
            # Chuyển timestamp
            ts = datetime.fromtimestamp(bar_data['timestamp'] / 1000)
            
            self.bar_batch.append((
                stock_id,
                '1m',  # timeframe
                ts,
                bar_data['open'],
                bar_data['high'],
                bar_data['low'],
                bar_data['close'],
                bar_data['volume'],
                bar_data.get('trade_count'),
                bar_data.get('vwap')
            ))
            
            # Batch insert khi đủ số lượng
            if len(self.bar_batch) >= self.batch_size:
                self.flush_bars()
                
        except Exception as e:
            print(f"Error inserting bar: {e}")
    
    def flush_bars(self):
        """Batch insert bars vào database"""
        if not self.bar_batch:
            return
            
        try:
            execute_batch(
                self.cursor,
                """
                INSERT INTO market_data_oltp.stock_bars_staging 
                (stock_id, timeframe, ts, open_price, high_price, low_price, 
                 close_price, volume, trade_count, vwap)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (stock_id, ts, timeframe) DO NOTHING
                """,
                self.bar_batch
            )
            self.conn.commit()
            print(f"✓ Inserted {len(self.bar_batch)} bars into database")
            self.bar_batch = []
            
        except Exception as e:
            self.conn.rollback()
            print(f"Error flushing bars: {e}")
            self.bar_batch = []
    
    def consume(self):
        """Bắt đầu consume messages từ Kafka"""
        print("\n" + "=" * 60)
        print("Database Consumer Started - Listening for messages...")
        print("=" * 60 + "\n")
        
        try:
            for message in self.consumer:
                topic = message.topic
                data = message.value
                
                if topic == TOPIC_TRADES:
                    self.insert_trade(data)
                    print(f"← Trade: {data['symbol']} @ ${data['price']}")
                    
                elif topic == TOPIC_BARS:
                    self.insert_bar(data)
                    print(f"← Bar: {data['symbol']} OHLC [{data['open']}->{data['close']}]")
                    
        except KeyboardInterrupt:
            print("\n\nShutting down consumer...")
            self.flush_trades()
            self.flush_bars()
            self.close()
    
    def close(self):
        """Đóng connections"""
        if self.consumer:
            self.consumer.close()
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("Consumer closed")


def main():
    """Main entry point"""
    consumer = DatabaseConsumer()
    
    try:
        consumer.consume()
    except Exception as e:
        print(f"Error: {e}")
        consumer.close()


if __name__ == "__main__":
    main()
