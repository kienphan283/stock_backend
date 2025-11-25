"""
Financial Transformer
Normalizes and maps AlphaVantage API responses to database schema
"""

import re
import logging
from typing import Dict, Any, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


def normalize_item_name(name: str) -> str:
    """
    Normalize AlphaVantage field names to human-readable format
    
    Example:
        "totalRevenue" -> "Total Revenue"
        "costOfRevenue" -> "Cost Of Revenue"
        "grossProfit" -> "Gross Profit"
    
    Args:
        name: Raw field name from AlphaVantage API
        
    Returns:
        Normalized item name (Title Case)
    """
    # Insert space before capital letters (camelCase -> camel Case)
    name = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', name)
    # Replace underscores with spaces
    name = name.replace("_", " ")
    # Convert to Title Case
    return name.title()


def parse_fiscal_date(fiscal_date: str) -> Tuple[int, str]:
    """
    Parse fiscal date string to year and quarter
    
    Args:
        fiscal_date: Date string in format "YYYY-MM-DD"
        
    Returns:
        Tuple of (fiscal_year, fiscal_quarter) where quarter is "Q1", "Q2", "Q3", or "Q4"
    """
    try:
        date_obj = datetime.strptime(fiscal_date, "%Y-%m-%d")
        fiscal_year = date_obj.year
        month = date_obj.month
        # Calculate quarter: Q1 (Jan-Mar), Q2 (Apr-Jun), Q3 (Jul-Sep), Q4 (Oct-Dec)
        quarter = f"Q{((month - 1) // 3) + 1}"
        return fiscal_year, quarter
    except ValueError as e:
        logger.error(f"Invalid fiscal date format: {fiscal_date}, error: {e}")
        raise ValueError(f"Invalid fiscal date format: {fiscal_date}")


def transform_quarterly_report(
    quarterly_report: Dict[str, Any],
    statement_code: str
) -> Tuple[Dict[str, Any], List[Tuple[str, str, float, str]]]:
    """
    Transform a single quarterly report from AlphaVantage into database format
    
    Args:
        quarterly_report: Raw quarterly report dictionary from AlphaVantage API
        statement_code: Statement type code ("IS", "BS", or "CF")
        
    Returns:
        Tuple of:
        - Statement metadata: {
            "fiscal_date": str,
            "fiscal_year": int,
            "fiscal_quarter": str,
            "reported_currency": str,
            "report_date": str
          }
        - Line items: List of tuples (item_code, item_name, item_value, unit)
    """
    # Extract metadata
    fiscal_date = quarterly_report.get("fiscalDateEnding", "")
    if not fiscal_date:
        raise ValueError("Missing fiscalDateEnding in quarterly report")
    
    fiscal_year, fiscal_quarter = parse_fiscal_date(fiscal_date)
    reported_currency = quarterly_report.get("reportedCurrency", "USD")
    report_date = quarterly_report.get("filedDate") or quarterly_report.get("acceptedDate") or fiscal_date
    
    statement_metadata = {
        "fiscal_date": fiscal_date,
        "fiscal_year": fiscal_year,
        "fiscal_quarter": fiscal_quarter,
        "reported_currency": reported_currency,
        "report_date": report_date
    }
    
    # Extract line items
    line_items = []
    
    # Fields to skip (metadata fields, not financial line items)
    skip_fields = {
        "fiscalDateEnding",
        "reportedCurrency",
        "filedDate",
        "acceptedDate",
        "period"
    }
    
    for key, value in quarterly_report.items():
        # Skip metadata fields
        if key in skip_fields:
            continue
        
        # Skip empty or None values
        if value in (None, "", "None"):
            continue
        
        # Try to convert to float
        try:
            item_value = float(value)
        except (ValueError, TypeError):
            # Skip non-numeric values
            continue
        
        # Normalize item name
        item_name = normalize_item_name(key)
        
        # item_code is the original key from AlphaVantage
        # item_name is the normalized human-readable name
        # item_value is the numeric value
        # unit is the reported currency
        line_items.append((key, item_name, item_value, reported_currency))
    
    logger.debug(
        f"Transformed quarterly report: {fiscal_year} {fiscal_quarter}, "
        f"{len(line_items)} line items"
    )
    
    return statement_metadata, line_items


def transform_all_quarterly_reports(
    api_response: Dict[str, Any],
    statement_code: str,
    max_quarters: int = 20
) -> List[Tuple[Dict[str, Any], List[Tuple[str, str, float, str]]]]:
    """
    Transform all quarterly reports from AlphaVantage API response
    
    Args:
        api_response: Raw API response dictionary
        statement_code: Statement type code
        max_quarters: Maximum number of quarters to process (default: 20)
        
    Returns:
        List of tuples (statement_metadata, line_items) for each quarter
    """
    if "quarterlyReports" not in api_response:
        logger.warning(f"No quarterlyReports found in API response for {statement_code}")
        return []
    
    quarterly_reports = api_response["quarterlyReports"]
    
    # Sort by fiscal date (newest first) and limit
    sorted_reports = sorted(
        quarterly_reports,
        key=lambda x: x.get("fiscalDateEnding", ""),
        reverse=True
    )[:max_quarters]
    
    transformed_reports = []
    
    for report in sorted_reports:
        try:
            metadata, line_items = transform_quarterly_report(report, statement_code)
            transformed_reports.append((metadata, line_items))
        except Exception as e:
            logger.error(f"Failed to transform quarterly report: {e}")
            continue
    
    logger.info(
        f"Transformed {len(transformed_reports)} quarterly reports for {statement_code}"
    )
    
    return transformed_reports

