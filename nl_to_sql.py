"""
nl_to_sql.py
Converts a plain-English question into a BigQuery SQL query
using Groq's free API (Llama 3.3 70B).
"""

import os
from groq import Groq

# ---------- CONFIG ----------
def get_groq_key():
    try:
        import streamlit as st
        if "GROQ_API_KEY" in st.secrets:
            return st.secrets["GROQ_API_KEY"]
    except Exception:
        pass
    return os.environ.get("GROQ_API_KEY", "PASTE_YOUR_KEY_HERE")

GROQ_API_KEY = get_groq_key()
MODEL_ID = "llama-3.3-70b-versatile"  # free tier, no billing required

client = Groq(api_key=GROQ_API_KEY)

# ---------- SCHEMA CONTEXT ----------
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
6. In any query that uses GROUP BY, every column in ORDER BY must either appear in the
   GROUP BY clause or be wrapped in an aggregate function (SUM, AVG, MAX, MIN, COUNT).
   Never ORDER BY a raw, non-aggregated column when GROUP BY is present.
7. For questions that require a multi-step ranking (e.g. "find the state with the most X,
   then find the Y within that state"), use a WITH clause (CTE) to compute the first ranking,
   then join or filter against it in a second step. Do not try to do both steps in one
   flat GROUP BY query.
8. If the question is unclear or unrelated to this data, return exactly: INVALID_QUESTION
"""


def question_to_sql(question: str) -> str:
    response = client.chat.completions.create(
        model=MODEL_ID,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Question: {question}\n\nSQL:"},
        ],
        temperature=0,
    )
    sql = response.choices[0].message.content.strip()

    # Strip accidental markdown fences if the model adds them anyway
    sql = sql.replace("```sql", "").replace("```", "").strip()

    return sql


def fix_sql(question: str, failed_sql: str, error_message: str) -> str:
    """
    Self-healing retry: shows the model its own broken SQL plus the exact
    database error, and asks it to produce a corrected query.
    """
    fix_prompt = f"""{SYSTEM_PROMPT}

The following SQL query was generated for this question but failed to run:

Question: {question}

SQL that failed:
{failed_sql}

Database error:
{error_message}

Do not simply repeat the same query structure that caused this error. If the error is about
ORDER BY referencing a non-aggregated column, restructure the query using a WITH clause (CTE)
to compute the ranking/aggregation first, then select from it. Return ONLY the corrected SQL
query, no explanation, no markdown, no backticks.

Corrected SQL:"""

    response = client.chat.completions.create(
        model=MODEL_ID,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": fix_prompt},
        ],
        temperature=0.4,
    )
    sql = response.choices[0].message.content.strip()
    sql = sql.replace("```sql", "").replace("```", "").strip()
    return sql


if __name__ == "__main__":
    test_questions = [
        "What is the average modal price of onion in Maharashtra?",
        "Show top 5 commodities by max price in Gujarat",
        "What is the capital of France?",
    ]

    for q in test_questions:
        print(f"\nQ: {q}")
        print(f"SQL: {question_to_sql(q)}")
