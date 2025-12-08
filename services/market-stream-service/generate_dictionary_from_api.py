import requests
import psycopg2
from psycopg2.extras import execute_values
import re

# Use user's quarterlyReports-based logic to build dictionary,
# but connect to Postgres inside Docker.
import os

# Use environment variables injected by Docker (or defaults)
API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
if not API_KEY:
    raise ValueError("ALPHA_VANTAGE_API_KEY environment variable is not set")
SYMBOL = "IBM"

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "postgres"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", "Web_quan_li_danh_muc"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD"),
}


def normalize_item_name(name: str) -> str:
    """Normalize raw Alpha Vantage keys into human-friendly names."""
    name = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name)
    name = name.replace("_", " ")
    return name.title()


def collect_numeric_keys(symbol: str, api_key: str):
    """
    Reuse user's BCTC logic to scan quarterly reports and collect
    (item_code, item_name) pairs for all numeric fields.
    """
    mapping = {
        "IS": "INCOME_STATEMENT",
        "BS": "BALANCE_SHEET",
        "CF": "CASH_FLOW",
    }

    meta_keys = {
        "fiscalDateEnding",
        "reportedCurrency",
        "filedDate",
        "acceptedDate",
        "period",
    }

    dictionary_items = {}

    for statement_code, api_function in mapping.items():
        url = (
            f"https://www.alphavantage.co/query"
            f"?function={api_function}&symbol={symbol}&apikey={api_key}"
        )
        resp = requests.get(url)
        data = resp.json()

        if "quarterlyReports" not in data:
            continue

        quarterly_reports = sorted(
            data["quarterlyReports"],
            key=lambda x: x.get("fiscalDateEnding", ""),
            reverse=True,
        )[:20]

        for q in quarterly_reports:
            for key, value in q.items():
                if key in meta_keys:
                    continue
                if value in (None, "", "None"):
                    continue
                try:
                    float(value)
                except (TypeError, ValueError):
                    continue

                item_code = key  # same as user's script
                item_name = normalize_item_name(key)
                dictionary_items[item_code] = item_name

    return [(code, name) for code, name in dictionary_items.items()]


def insert_dict():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    keys = collect_numeric_keys(SYMBOL, API_KEY)

    execute_values(
        cur,
        """
        INSERT INTO financial_oltp.line_item_dictionary (item_code, item_name)
        VALUES %s
        ON CONFLICT (item_code) DO NOTHING
        """,
        keys,
    )

    conn.commit()
    cur.close()
    conn.close()


if __name__ == "__main__":
    insert_dict()
    print("Dictionary generation complete!")
