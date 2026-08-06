"""
nl_to_sql.py
Converts a plain-English question into a BigQuery SQL query
using Gemini 3 Flash (current free-tier model as of 2026).
"""

import os
from google import genai

# ---------- CONFIG ----------
def get_gemini_key():
    try:
        import streamlit as st
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    return os.environ.get("GEMINI_API_KEY", "PASTE_YOUR_KEY_HERE")

GEMINI_API_KEY = get_gemini_key()
MODEL_ID = "gemini-2.5-flash"  # higher free-tier quota (1,500 req/day) vs gemini-3-flash-preview (20/day)

client = genai.Client(api_key=GEMINI_API_KEY)

# ---------- SCHEMA CONTEXT ----------
# Give the model your exact table/column names so it doesn't hallucinate.
SCHEMA = """
You are querying a Google BigQuery dataset called `gov-marketdata.Market_Price`
with these tables:

states(state_id, state_name)
districts(district_id, district_name, state_id)
markets(market_id, market_name, district_id)
commodities(commodity_id, commodity_name, variety, grade)
prices(price_id, market_id, commodity_id, arrival_date, min_price, max_price, modal_price)

Relationships:
- prices.market_id -> markets.market_id
- prices.commodity_id -> commodities.commodity_id
- markets.district_id -> districts.district_id
- districts.state_id -> states.state_id
"""

SYSTEM_PROMPT = f"""
{SCHEMA}

Rules:
1. Return ONLY a valid BigQuery Standard SQL SELECT query. No explanation, no markdown, no backticks.
2. Always fully qualify table names as `gov-marketdata.Market_Price.table_name`.
3. Only generate SELECT statements. Never write INSERT, UPDATE, DELETE, DROP, or ALTER.
4. Use JOINs across the relationships above when the question needs data from multiple tables.
5. The commodities table has a separate row per variety/grade combination, so the same
   commodity_name can appear multiple times with different commodity_id values. When a question
   asks for "top commodities" or similar by name, GROUP BY commodity_name (not commodity_id) and
   aggregate the price (e.g. MAX or AVG) so each commodity name appears only once in the result.
6. If the question is unclear or unrelated to this data, return exactly: INVALID_QUESTION
"""


def question_to_sql(question: str) -> str:
    response = client.models.generate_content(
        model=MODEL_ID,
        contents=f"{SYSTEM_PROMPT}\n\nQuestion: {question}\n\nSQL:",
    )
    sql = response.text.strip()

    # Strip accidental markdown fences if the model adds them anyway
    sql = sql.replace("```sql", "").replace("```", "").strip()

    return sql


if __name__ == "__main__":
    # Quick manual test
    test_questions = [
        "What is the average modal price of onion in Maharashtra?",
        "Show top 5 commodities by max price in Gujarat",
        "What is the capital of France?",  # should return INVALID_QUESTION
    ]

    for q in test_questions:
        print(f"\nQ: {q}")
        print(f"SQL: {question_to_sql(q)}")
