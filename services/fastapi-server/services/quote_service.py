from db.quote_repo import QuoteRepository
from services.data_loader import StockDataLoader # Keep legacy loader for fallback

class QuoteService:
    def __init__(self):
        self.repo = QuoteRepository()

    def get_quote(self, ticker: str):
        try:
            stock_id = self.repo.get_stock_id(ticker)
            if not stock_id:
                # Fallback
                return self._get_fallback_quote(ticker)

            latest = self.repo.get_latest_price(stock_id)
            if not latest:
                return self._get_fallback_quote(ticker)

            previous_close = self.repo.get_previous_close(stock_id)
            if previous_close is None:
                previous_close = float(latest['current_price'])

            current_price = float(latest['current_price'])
            change = current_price - previous_close

            return {
                "currentPrice": round(current_price, 2),
                "change": round(change, 2),
                "percentChange": round(float(latest['percent_change'] or 0), 2),
                "high": round(float(latest['high_price'] or 0), 2),
                "low": round(float(latest['low_price'] or 0), 2),
                "open": round(float(latest['open_price'] or 0), 2),
                "previousClose": round(previous_close, 2)
            }
        except Exception as e:
            # Log error
            raise e

    def _get_fallback_quote(self, ticker: str):
        temp_loader = StockDataLoader(ticker.upper())
        return temp_loader.get_quote()
