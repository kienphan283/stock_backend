from db.quote_repo import QuoteRepository
from data_loaders.data_loader import StockDataLoader  # Keep data loader for fallback
from services.alpaca_eod_service import EODFetchService
from utils.market_hours import get_latest_trading_date
from typing import List, Dict
from datetime import date, datetime
import logging

logger = logging.getLogger(__name__)

class QuoteService:
    def __init__(self):
        self.repo = QuoteRepository()
        self.eod_fetch_service = EODFetchService()

    def get_quote(self, ticker: str):
        try:
            stock_id = self.repo.get_stock_id(ticker)
            if not stock_id:
                # Fallback
                return self._get_fallback_quote(ticker)

            latest = self.repo.get_latest_price(stock_id)
            if not latest:
                return self._get_fallback_quote(ticker)

            # Fix: get_previous_close fetches the LATEST close, which creates 0 change if we overlap.
            # Ideally we should fetch the record before this one.
            # But for now, let's trust the 'change' or 'percent_change' in the DB record if available,
            # or infer it.
            
            curr_price = float(latest['current_price'])
            percent_change = float(latest['percent_change'] or 0)
            
            # Get profile data for additional fields (Beta, Growth, etc.)
            try:
                # Use data loader to get profile data (csv based)
                loader = StockDataLoader(ticker.upper())
                profile_data = loader.get_company_profile()
            except Exception as e:
                logger.warning(f"Could not load profile data for {ticker}: {e}")
                profile_data = {}

            # P/E and EPS logic:
            # 1. Try to get from Quote DB record (if we stored it, but currently we don't for EOD)
            # 2. Try to get from StockDataLoader (which reads stock_quote.csv)
            # 3. Fallback to 0 (avoid random generation)
            
            pe = 0.0
            eps = 0.0
            
            # Try to get from CSV via loader fallback logic for consistent mock data
            try:
                quote_csv_data = loader.get_quote()
                pe = quote_csv_data.get('pe', 0)
                eps = quote_csv_data.get('eps', 0)
            except Exception as e:
                logger.error(f"Error loading CSV quote data for {ticker}: {e}")

            if pe == 0 and curr_price > 0:
                 # Last resort fallback if CSV missing: calculate from price if EPS known, or leave 0
                 pass

            # Calculate change if needed (same logic as before)
            if percent_change != 0:
                prev_close_inferred = curr_price / (1 + percent_change / 100)
                change = curr_price - prev_close_inferred
                previous_close = prev_close_inferred
            else:
                change = 0.0
                previous_close = curr_price

            result = {
                "currentPrice": round(curr_price, 2),
                "change": round(change, 2),
                "percentChange": round(percent_change, 2),
                "high": round(float(latest['high_price'] or 0), 2),
                "low": round(float(latest['low_price'] or 0), 2),
                "open": round(float(latest['open_price'] or 0), 2),
                "previousClose": round(previous_close, 2),
                "pe": round(pe, 2),
                "eps": round(eps, 2),
                # Add profile fields
                "beta": profile_data.get('beta'),
                "revenueGrowth": profile_data.get('revenueGrowth'),
                "netIncomeGrowth": profile_data.get('netIncomeGrowth'),
                "fcfGrowth": profile_data.get('fcfGrowth')
            }
            
            # Enrich with mock data for missing fields if DB has zeros
            # If DB has zero change but mock has value, use mock (common in dev)
            if result['change'] == 0 and quote_csv_data.get('change', 0) != 0:
                 result['change'] = quote_csv_data.get('change', 0)
                 result['percentChange'] = quote_csv_data.get('percentChange', 0)
                 result['previousClose'] = quote_csv_data.get('previousClose', 0)

            return result
        except Exception as e:
            logger.error(f"Error in get_quote for {ticker}: {e}")
            # Fallback on error
            return self._get_fallback_quote(ticker)

    def get_previous_closes_batch(self, tickers: List[str]) -> Dict[str, float]:
        """
        Batch query để lấy previousClose cho nhiều symbols cùng lúc (tối ưu performance).
        
        Returns:
            Dict {ticker: previousClose} - previousClose từ record đầu tiên (ngày mới nhất) của mỗi symbol
        """
        return self.repo.get_previous_closes_batch(tickers)
    
    def get_latest_eod_batch(self, tickers: List[str], auto_fetch: bool = True) -> Dict[str, Dict]:
        """
        Batch query để lấy latest EOD data cho nhiều symbols.
        Dùng khi market đóng để hiển thị dữ liệu của phiên vừa kết thúc.
        
        Nếu auto_fetch=True và không có dữ liệu của ngày mới nhất, sẽ tự động fetch từ API và insert vào DB.
        
        Args:
            tickers: List of ticker symbols
            auto_fetch: If True, automatically fetch and insert EOD if missing
            
        Returns:
            Dict {ticker: {price, volume, changePercent, previousClose}}
        """
        # First, get latest EOD data from DB
        result = self.repo.get_latest_eod_batch(tickers)
        
        # Check if we need to fetch missing data
        if auto_fetch:
            # Get latest trading date based on market hours
            target_date = get_latest_trading_date()
            logger.info(f"[QuoteService] Latest trading date determined: {target_date}")
            
            # Check which tickers are missing latest EOD data or have outdated data
            missing_tickers = []
            for ticker in tickers:
                ticker_upper = ticker.upper()
                if ticker_upper not in result:
                    # No data at all
                    missing_tickers.append(ticker_upper)
                    logger.debug(f"[QuoteService] {ticker_upper}: No EOD data found")
                else:
                    # Check if trading_date is older than target_date
                    trading_date_str = result[ticker_upper].get('tradingDate')
                    if trading_date_str:
                        try:
                            trading_date = date.fromisoformat(trading_date_str)
                            if trading_date < target_date:
                                # Data is outdated, need to fetch
                                missing_tickers.append(ticker_upper)
                                logger.info(f"[QuoteService] {ticker_upper}: EOD data outdated (DB: {trading_date}, Target: {target_date})")
                            else:
                                logger.debug(f"[QuoteService] {ticker_upper}: EOD data is up-to-date (DB: {trading_date}, Target: {target_date})")
                        except (ValueError, TypeError) as e:
                            # Invalid date format, treat as missing
                            logger.warning(f"[QuoteService] {ticker_upper}: Invalid trading_date format '{trading_date_str}': {e}")
                            missing_tickers.append(ticker_upper)
                    else:
                        # No trading_date field, treat as missing
                        logger.warning(f"[QuoteService] {ticker_upper}: No trading_date field in result")
                        missing_tickers.append(ticker_upper)
            
            # If there are missing/outdated tickers, fetch from API and insert
            if missing_tickers:
                logger.info(f"[QuoteService] Missing/outdated EOD data for {len(missing_tickers)} tickers, fetching from API for date {target_date}...")
                logger.info(f"[QuoteService] Missing tickers: {missing_tickers[:10]}..." if len(missing_tickers) > 10 else f"[QuoteService] Missing tickers: {missing_tickers}")
                try:
                    # Fetch EOD data from external API
                    logger.info(f"[QuoteService] Calling fetch_eod_bars for {len(missing_tickers)} tickers, target_date={target_date}")
                    eod_data = self.eod_fetch_service.fetch_eod_bars(missing_tickers, target_date)
                    logger.info(f"[QuoteService] fetch_eod_bars returned {len(eod_data)} records")
                    
                    if eod_data:
                        logger.info(f"[QuoteService] Sample EOD data: {list(eod_data.items())[:3]}")
                        # Insert into DB
                        logger.info(f"[QuoteService] Calling insert_eod_to_db...")
                        inserted_count = self.eod_fetch_service.insert_eod_to_db(self.repo, eod_data)
                        logger.info(f"[QuoteService] ✅ Fetched and inserted {inserted_count} EOD records for date {target_date}")
                        
                        # Re-query to get the newly inserted data
                        logger.info(f"[QuoteService] Re-querying latest EOD data...")
                        result = self.repo.get_latest_eod_batch(tickers)
                        logger.info(f"[QuoteService] Re-query returned {len(result)} records")
                    else:
                        logger.warning(f"[QuoteService] No EOD data fetched from API for date {target_date}")
                except Exception as e:
                    logger.error(f"[QuoteService] ❌ Error auto-fetching EOD data: {e}", exc_info=True)
                    # Continue with existing result even if fetch failed
            else:
                logger.info(f"[QuoteService] All tickers have up-to-date EOD data (target_date: {target_date})")
        
        # Remove tradingDate from result before returning (not needed by frontend)
        for ticker in result:
            if 'tradingDate' in result[ticker]:
                del result[ticker]['tradingDate']
        
        return result

    def _get_fallback_quote(self, ticker: str):
        temp_loader = StockDataLoader(ticker.upper())
        quote = temp_loader.get_quote()
        
        # Also enrich fallback with profile data
        try:
            profile = temp_loader.get_company_profile()
            quote['beta'] = profile.get('beta')
            quote['revenueGrowth'] = profile.get('revenueGrowth')
            quote['netIncomeGrowth'] = profile.get('netIncomeGrowth')
            quote['fcfGrowth'] = profile.get('fcfGrowth')
        except:
             pass
             
        return quote
