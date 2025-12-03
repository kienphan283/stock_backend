from .base_repo import BaseRepository

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
        query = """
            SELECT close_price
            FROM market_data_oltp.stock_eod_prices 
            WHERE stock_id = %s 
            ORDER BY trading_date DESC 
            OFFSET 1
            LIMIT 1
        """
        result = self.execute_query(query, (stock_id,), fetch_one=True)
        return float(result['close_price']) if result else None
