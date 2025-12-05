#!/usr/bin/env python3
"""
Debug script để kiểm tra volume API và database.
Chạy: python debug_volume_api.py
"""

import sys
from pathlib import Path

# Add shared path
SHARED_PATH = Path(__file__).resolve().parent / "shared"
if str(SHARED_PATH) not in sys.path:
    sys.path.insert(0, str(SHARED_PATH))

import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

# Load env
load_dotenv(Path(__file__).parent / ".env")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", "Web_quan_li_danh_muc"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

def check_volume_column():
    """Kiểm tra xem cột volume có tồn tại không"""
    print("\n=== 1. Kiểm tra cột volume trong stock_trades_realtime ===")
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT column_name, data_type, column_default
                FROM information_schema.columns
                WHERE table_schema = 'market_data_oltp'
                  AND table_name = 'stock_trades_realtime'
                  AND column_name = 'volume'
            """)
            result = cur.fetchone()
            if result:
                print(f"✅ Cột volume tồn tại: {dict(result)}")
                return True
            else:
                print("❌ Cột volume KHÔNG tồn tại! Cần chạy migration 003_add_volume_to_trades.sql")
                return False
    finally:
        conn.close()

def check_trade_data():
    """Kiểm tra dữ liệu trong stock_trades_realtime"""
    print("\n=== 2. Kiểm tra dữ liệu trong stock_trades_realtime ===")
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Tổng số records
            cur.execute("SELECT COUNT(*) as count FROM market_data_oltp.stock_trades_realtime")
            total = cur.fetchone()['count']
            print(f"📊 Tổng số records: {total}")
            
            if total == 0:
                print("⚠️  KHÔNG có dữ liệu trong stock_trades_realtime!")
                return False
            
            # Sample records với volume
            cur.execute("""
                SELECT 
                    s.stock_ticker,
                    t.trade_id,
                    t.ts,
                    t.price,
                    t.size,
                    t.volume
                FROM market_data_oltp.stock_trades_realtime t
                JOIN market_data_oltp.stocks s ON s.stock_id = t.stock_id
                ORDER BY t.ts DESC
                LIMIT 10
            """)
            rows = cur.fetchall()
            print(f"\n📋 Sample 10 records mới nhất:")
            for row in rows:
                print(f"  {row['stock_ticker']}: trade_id={row['trade_id']}, "
                      f"ts={row['ts']}, price={row['price']}, "
                      f"size={row['size']}, volume={row['volume']}")
            
            # Kiểm tra records có volume > 0
            cur.execute("""
                SELECT COUNT(*) as count
                FROM market_data_oltp.stock_trades_realtime
                WHERE volume > 0
            """)
            with_volume = cur.fetchone()['count']
            print(f"\n📈 Records có volume > 0: {with_volume}/{total}")
            
            return with_volume > 0
    finally:
        conn.close()

def test_query():
    """Test query giống như trong repository"""
    print("\n=== 3. Test query giống như trong repository ===")
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            symbols = ['AAPL', 'MSFT', 'GOOGL']
            placeholders = ','.join(['%s'] * len(symbols))
            query = f"""
                SELECT 
                    s.stock_ticker AS symbol,
                    COALESCE(t.volume, 0) AS volume
                FROM market_data_oltp.stocks AS s
                LEFT JOIN LATERAL (
                    SELECT volume
                    FROM market_data_oltp.stock_trades_realtime
                    WHERE stock_id = s.stock_id
                    ORDER BY ts DESC, trade_id DESC
                    LIMIT 1
                ) AS t ON true
                WHERE s.stock_ticker IN ({placeholders})
                    AND s.delisted IS FALSE
            """
            cur.execute(query, [s.upper() for s in symbols])
            rows = cur.fetchall()
            
            print(f"📊 Kết quả query cho {symbols}:")
            if rows:
                for row in rows:
                    print(f"  {row['symbol']}: volume={row['volume']}")
            else:
                print("  ❌ Không có kết quả!")
            
            return rows
    finally:
        conn.close()

def main():
    print("🔍 Debug Volume API")
    print("=" * 60)
    
    # 1. Check column
    has_column = check_volume_column()
    
    # 2. Check data
    has_data = check_trade_data()
    
    # 3. Test query
    if has_column and has_data:
        test_query()
    
    print("\n" + "=" * 60)
    print("✅ Debug hoàn tất!")
    
    if not has_column:
        print("\n⚠️  CẦN CHẠY MIGRATION:")
        print("   docker exec -i stock_postgres psql -U postgres -d Web_quan_li_danh_muc -f /docker-entrypoint-initdb.d/market_data_oltp/migrations/003_add_volume_to_trades.sql")
    
    if not has_data:
        print("\n⚠️  KHÔNG CÓ DỮ LIỆU!")
        print("   Kiểm tra xem market-stream-service có đang chạy và insert data không?")

if __name__ == "__main__":
    main()

