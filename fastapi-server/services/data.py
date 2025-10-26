import requests
import psycopg2
from psycopg2.extras import execute_values
import re
import os
from dotenv import load_dotenv
from pathlib import Path

CURRENT_FILE_PATH = Path(__file__).resolve() 
ENV_PATH = CURRENT_FILE_PATH.parent.parent / ".env.local" 
load_dotenv(ENV_PATH)

API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}

def normalize_item_name(name: str) -> str:
    name = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', name)
    name = name.replace("_", " ")
    return name.title()

def import_financial_data(symbol: str, statement_code: str, api_key: str, conn):
    mapping = {"IS": "INCOME_STATEMENT", "BS": "BALANCE_SHEET", "CF": "CASH_FLOW"}
    if statement_code not in mapping:
        raise ValueError("statement_code phải là 'IS', 'BS' hoặc 'CF'")
    api_function = mapping[statement_code]
    url = f"https://www.alphavantage.co/query?function={api_function}&symbol={symbol}&apikey={api_key}"
    r = requests.get(url)
    data = r.json()
    if "quarterlyReports" not in data:
        return
    quarterly_reports = sorted(
        data["quarterlyReports"],
        key=lambda x: x.get("fiscalDateEnding", ""),
        reverse=True
    )[:20]
    cur = conn.cursor()
    cur.execute("""
        SELECT statement_type_id FROM financial_oltp.statement_type
        WHERE statement_code = %s
    """, (statement_code,))
    statement_type_id = cur.fetchone()[0]
    for q in quarterly_reports:
        fiscal_date = q["fiscalDateEnding"]
        fiscal_year = int(fiscal_date[:4])
        month = int(fiscal_date[5:7])
        quarter = f"Q{((month - 1)//3) + 1}"
        cur.execute("""
            INSERT INTO financial_oltp.financial_statement 
            (company_id, statement_type_id, fiscal_year, fiscal_quarter, report_date)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (company_id, statement_type_id, fiscal_year, fiscal_quarter)
            DO NOTHING
            RETURNING statement_id
        """, (symbol, statement_type_id, fiscal_year, quarter, fiscal_date))
        result = cur.fetchone()
        if not result:
            continue
        statement_id = result[0]
        line_items = []
        for key, value in q.items():
            if key in ["fiscalDateEnding", "reportedCurrency", "filedDate", "acceptedDate", "period"]:
                continue
            if value in (None, "", "None"):
                continue
            try:
                value = float(value)
            except ValueError:
                continue
            normalized_name = normalize_item_name(key)
            cur.execute("""
                INSERT INTO financial_oltp.line_item_dictionary (item_code, item_name)
                VALUES (%s, %s)
                ON CONFLICT (item_code) DO NOTHING
            """, (key, normalized_name))
            line_items.append((statement_id, key, normalized_name, value, "USD"))
        if line_items:
            execute_values(cur, """
                INSERT INTO financial_oltp.financial_line_item
                (statement_id, item_code, item_name, item_value, unit)
                VALUES %s
            """, line_items)
    cur.close()

def import_all_statements(symbol: str, api_key: str):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO financial_oltp.company (company_id, company_name, exchange)
        VALUES (%s, %s, %s)
        ON CONFLICT (company_id) DO NOTHING
    """, (symbol, f"{symbol} Corporation", "NYSE"))
    conn.commit()
    for code in ["IS", "BS", "CF"]:
        import_financial_data(symbol, code, api_key, conn)
        conn.commit()
    conn.close()

if __name__ == "__main__":
    top_companies = [
        "AAPL",    # Apple
        "MSFT",    # Microsoft
        "GOOGL",   # Alphabet (Google)
        "AMZN",    # Amazon
        "NVDA",    # Nvidia
        "META",    # Meta Platforms
        "TSLA",    # Tesla
        "BRK-B",   # Berkshire Hathaway
        "JNJ",     # Johnson & Johnson
        "JPM",     # JPMorgan Chase (không có)
        "IBM"      # IBM (Công ty ban đầu)
    ]
    print(f"import data for {len(top_companies)} companies...")
    for company_symbol in top_companies: 
        print(f"--- Đang import dữ liệu cho: {company_symbol} ---")
        import_all_statements(company_symbol, API_KEY)
        print(f"--- Hoàn thành import cho: {company_symbol} ---")

    print("Hoàn thành quá trình import dữ liệu.")

