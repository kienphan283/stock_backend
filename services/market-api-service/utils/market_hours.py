"""
Market Hours Utility for Python Backend
Check if US Stock Market is currently open and get latest trading date
"""
from datetime import datetime, date, timedelta
try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Fallback for Python < 3.9
    from backports.zoneinfo import ZoneInfo

# US Eastern Time (ET) - New York
try:
    MARKET_TIMEZONE = ZoneInfo("America/New_York")
except Exception:
    # Fallback: use UTC offset calculation
    import pytz
    MARKET_TIMEZONE = pytz.timezone("America/New_York")

# Regular trading hours in ET
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 30
MARKET_CLOSE_HOUR = 16
MARKET_CLOSE_MINUTE = 0


def is_market_open(check_date: datetime = None) -> bool:
    """
    Check if the US stock market is currently open for regular trading.
    Considers weekends and regular trading hours in ET.
    
    Args:
        check_date: The date/time to check, defaults to now in UTC.
        
    Returns:
        True if the market is open, False otherwise.
    """
    if check_date is None:
        check_date = datetime.now(ZoneInfo("UTC"))
    
    # Convert to ET
    et_time = check_date.astimezone(MARKET_TIMEZONE)
    
    # Check for weekends (Saturday = 5, Sunday = 6)
    if et_time.weekday() >= 5:
        return False
    
    # Check if within market hours (9:30 AM - 4:00 PM ET)
    market_open = et_time.replace(hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MINUTE, second=0, microsecond=0)
    market_close = et_time.replace(hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MINUTE, second=0, microsecond=0)
    
    return market_open <= et_time < market_close


def get_latest_trading_date(check_date: datetime = None) -> date:
    """
    Get the latest trading date (most recent market close).
    
    Logic:
    - If market is currently open today → return today
    - If market closed today (after 4 PM ET) → return today
    - If market hasn't opened yet today (before 9:30 AM ET) → return yesterday
    - If weekend → return Friday
    
    Args:
        check_date: The date/time to check, defaults to now in UTC.
        
    Returns:
        The latest trading date as a date object.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    if check_date is None:
        try:
            check_date = datetime.now(ZoneInfo("UTC"))
        except:
            import pytz
            check_date = datetime.now(pytz.UTC)
    
    # Convert to ET
    if check_date.tzinfo is None:
        import pytz
        check_date = pytz.UTC.localize(check_date)
    et_time = check_date.astimezone(MARKET_TIMEZONE)
    et_date = et_time.date()
    
    logger.debug(f"[get_latest_trading_date] UTC time: {check_date}, ET time: {et_time}, ET date: {et_date}")
    
    # Check for weekends
    if et_time.weekday() >= 5:  # Saturday = 5, Sunday = 6
        # Go back to Friday
        days_back = et_time.weekday() - 4  # Saturday: 1 day, Sunday: 2 days
        friday_date = et_date - timedelta(days=days_back)
        logger.info(f"[get_latest_trading_date] Weekend detected, returning Friday: {friday_date}")
        return friday_date
    
    # Check if market has closed today
    market_close_today = et_time.replace(hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MINUTE, second=0, microsecond=0)
    
    if et_time >= market_close_today:
        # Market has closed today → return today
        logger.info(f"[get_latest_trading_date] Market closed today (ET: {et_time} >= {market_close_today}), returning today: {et_date}")
        return et_date
    else:
        # Market hasn't closed yet today → return yesterday (or Friday if today is Monday)
        if et_time.weekday() == 0:  # Monday
            # Return Friday (3 days back)
            friday_date = et_date - timedelta(days=3)
            logger.info(f"[get_latest_trading_date] Monday before market close, returning Friday: {friday_date}")
            return friday_date
        else:
            # Return yesterday
            yesterday_date = et_date - timedelta(days=1)
            logger.info(f"[get_latest_trading_date] Market not closed yet today (ET: {et_time} < {market_close_today}), returning yesterday: {yesterday_date}")
            return yesterday_date

