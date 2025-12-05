from .base_repo import BaseRepository
from typing import List, Dict

class QuoteRepository(BaseRepository):
    def get_stock_id(self, ticker):
        query = """
            SELECT stock_id 
            FROM market_data_oltp.stocks 
            WHERE stock_ticker = %s
        """
        result = self.execute_query(query, (ticker.upper(),), fetch_one=True)
        return result['stock_id'] if result else None

    def get_latest_price(self, stock_id):
        query = """
            SELECT 
                close_price as current_price,
                open_price,
                high_price,
                low_price,
                volume,
                pct_change as percent_change
            FROM market_data_oltp.stock_eod_prices 
            WHERE stock_id = %s 
            ORDER BY trading_date DESC 
            LIMIT 1
        """
        return self.execute_query(query, (stock_id,), fetch_one=True)

    def get_previous_close(self, stock_id):
        """
        Lấy giá close của record đầu tiên (ngày mới nhất) sau khi sắp xếp theo trading_date DESC.
        
        Logic:
        1. Sắp xếp theo trading_date DESC (từ mới nhất đến cũ nhất)
        2. Lấy record đầu tiên (LIMIT 1) = ngày mới nhất
        3. Đây là previousClose để tính change so với giá realtime hiện tại
        """
        query = """
            SELECT close_price
            FROM market_data_oltp.stock_eod_prices 
            WHERE stock_id = %s 
            ORDER BY trading_date DESC 
            LIMIT 1
        """
        result = self.execute_query(query, (stock_id,), fetch_one=True)
        return float(result['close_price']) if result else None

    def get_previous_closes_batch(self, tickers: List[str]) -> Dict[str, float]:
        """
        Batch query để lấy previousClose cho nhiều symbols cùng lúc (tối ưu performance).
        
        Returns:
            Dict {ticker: previousClose} - previousClose từ record đầu tiên (ngày mới nhất) của mỗi symbol
        """
        if not tickers:
            return {}
        
        # Batch query: lấy previousClose cho tất cả symbols trong 1 query
        placeholders = ','.join(['%s'] * len(tickers))
        query = f"""
            SELECT 
                s.stock_ticker AS ticker,
                eod.close_price AS previous_close
            FROM market_data_oltp.stocks AS s
            LEFT JOIN LATERAL (
                SELECT close_price
                FROM market_data_oltp.stock_eod_prices
                WHERE stock_id = s.stock_id
                ORDER BY trading_date DESC
                LIMIT 1
            ) AS eod ON true
            WHERE s.stock_ticker IN ({placeholders})
                AND s.delisted IS FALSE
        """
        
        rows = self.execute_query(query, [t.upper() for t in tickers], fetch_all=True)
        
        # Convert to dict {ticker: previousClose}
        result: Dict[str, float] = {}
        for row in rows or []:
            ticker = row['ticker'] if isinstance(row, dict) else row[0]
            prev_close = row['previous_close'] if isinstance(row, dict) else row[1]
            if prev_close is not None:
                result[ticker.upper()] = float(prev_close)
        
        return result
