"""
query_executor.py
Safely executes a SQL string against BigQuery.
- Blocks any write/DDL statement (only SELECT allowed)
- Returns results as a pandas DataFrame
- Catches and reports errors cleanly (so the caller can retry / show a message)
"""

import re
from google.cloud import bigquery

PROJECT_ID = "gov-marketdata"
LOCATION = "asia-south1"

# Any of these keywords appearing means we refuse to run it
FORBIDDEN_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER",
    "CREATE", "TRUNCATE", "MERGE", "GRANT", "REVOKE",
]

_client = None


LOCATION = "asia-south1"  # must match the region your dataset was created in


def get_client():
    global _client
    if _client is None:
        _client = bigquery.Client(project=PROJECT_ID, location=LOCATION)
    return _client


def is_safe_query(sql: str) -> bool:
    """Only allow single SELECT statements, no write/DDL keywords."""
    stripped = sql.strip().rstrip(";")

    if not stripped.upper().startswith("SELECT"):
        return False

    upper_sql = stripped.upper()
    for keyword in FORBIDDEN_KEYWORDS:
        # word-boundary match so e.g. "created_date" doesn't false-trigger on CREATE
        if re.search(rf"\b{keyword}\b", upper_sql):
            return False

    # Disallow chained statements (e.g. "SELECT ...; DROP ...")
    if ";" in sql.strip().rstrip(";"):
        return False

    return True


def run_query(sql: str):
    """
    Executes SQL safely.
    Returns: (success: bool, result_df_or_error_message)
    """
    if sql.strip() == "INVALID_QUESTION":
        return False, "That question doesn't seem related to the mandi price data. Try asking about commodities, prices, markets, or states."

    if not is_safe_query(sql):
        return False, "Blocked: only single SELECT queries are allowed."

    try:
        client = get_client()
        query_job = client.query(sql)
        df = query_job.result().to_dataframe()
        return True, df
    except Exception as e:
        return False, f"Query failed: {str(e)}"


if __name__ == "__main__":
    # Quick manual tests
    good_sql = """
    SELECT s.state_name, AVG(p.modal_price) AS avg_price
    FROM `gov-marketdata.Market_Price.prices` p
    JOIN `gov-marketdata.Market_Price.markets` m ON p.market_id = m.market_id
    JOIN `gov-marketdata.Market_Price.districts` d ON m.district_id = d.district_id
    JOIN `gov-marketdata.Market_Price.states` s ON d.state_id = s.state_id
    GROUP BY s.state_name
    ORDER BY avg_price DESC
    LIMIT 5
    """
    bad_sql = "DROP TABLE `gov-marketdata.Market_Price.prices`"

    print("Testing safe SELECT query...")
    ok, result = run_query(good_sql)
    print("Success:", ok)
    print(result)

    print("\nTesting blocked DROP query...")
    ok, result = run_query(bad_sql)
    print("Success:", ok)
    print(result)