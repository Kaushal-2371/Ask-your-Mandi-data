# 🌾 Ask Your Mandi Data

A natural-language analytics tool for Indian commodity market (mandi) prices. Ask a question in plain English, get back a SQL-backed answer with an auto-generated chart — no SQL knowledge required.

**Live app:** https://ask-your-mandi-data-936fcbkgm6kfkucplavezc.streamlit.app/#ask-your-mandi-data

**GitHub:** https://github.com/Kaushal-2371/Ask-your-Mandi-data

---

## What it does

Type a question like *"What is the average modal price of onion in Maharashtra?"* and the app:

1. Converts your question into SQL using an LLM, grounded in the actual database schema
2. Runs the query safely against a live BigQuery database (read-only, single-SELECT only)
3. Self-corrects automatically if the generated SQL fails — the error is fed back to the model for a retry, without ever falling back to write operations
4. Auto-generates the right chart type (bar, line, or number card) based on the shape of the result
5. Summarizes the result in a short, plain-English answer

Full conversational history is kept in-session so you can ask follow-up questions.

---

## Architecture

```
User question
     │
     ▼
┌─────────────┐     schema-aware prompt      ┌──────────────┐
│  nl_to_sql   │ ───────────────────────────▶ │  Groq LLM     │
│              │ ◀─────────────────────────── │ (Llama 3.3)   │
└─────────────┘         generated SQL         └──────────────┘
     │
     ▼
┌─────────────────┐
│ query_executor   │  ── blocks non-SELECT / unsafe SQL
│ (BigQuery)       │  ── on failure, error is sent back to
└─────────────────┘     nl_to_sql for a self-healing retry
     │
     ▼ result table
     ├──────────────┐
     ▼              ▼
┌───────────┐  ┌────────────┐
│ visualizer │  │ summarizer │
│ (Plotly)   │  │ (LLM)      │
└───────────┘  └────────────┘
     │              │
     └──────┬───────┘
            ▼
      Streamlit UI
```

**Data pipeline (one-time / refreshable):**
Government open data (data.gov.in Agmarknet API) → normalized into a 5-table relational schema (states, districts, markets, commodities, prices) → loaded into Google BigQuery.

---

## Tech stack

| Layer | Tool |
|---|---|
| Data source | data.gov.in Agmarknet API (live daily mandi prices) |
| Database | Google BigQuery |
| NL → SQL | Groq API (Llama 3.3 70B) |
| Query safety | Custom guardrails — SELECT-only, keyword blocklist, no chained statements |
| Self-healing | Failed queries are automatically retried with the database error fed back to the model |
| Summarization | Groq API (Llama 3.3 70B) |
| Visualization | Plotly (auto-selects bar / line / number card based on result shape) |
| UI | Streamlit |
| Deployment | Streamlit Community Cloud |

---

## Database schema

The data is normalized into 5 relational tables rather than one flat file, to reflect real-world relational modeling and enable genuine multi-table JOIN queries:

- `states(state_id, state_name)`
- `districts(district_id, district_name, state_id)`
- `markets(market_id, market_name, district_id)`
- `commodities(commodity_id, commodity_name, variety, grade)`
- `prices(price_id, market_id, commodity_id, arrival_date, min_price, max_price, modal_price)`

---

## Example questions

- "What is the average modal price of onion in Maharashtra?"
- "Show top 5 commodities by max price in Gujarat"
- "Compare average prices of garlic and onion"
- "For each state, show the commodity with the highest average modal price, but only include states with more than 5 different commodities recorded"

The last example requires a multi-table join, grouped aggregation, and a HAVING-style filter — handled correctly by the self-healing SQL generation layer.

---

## Safety design

This project intentionally treats the LLM as untrusted input:

- Only single `SELECT` statements are ever executed
- A keyword blocklist rejects `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `TRUNCATE`, `MERGE`, `GRANT`, `REVOKE` even if the LLM attempts to generate them
- Chained statements (`SELECT ...; DROP ...`) are rejected
- The BigQuery service account itself is scoped to read-only access as a second layer of defense

---

## Known limitations

- The underlying dataset is a live daily snapshot (not full historical data), so some commodity/state combinations may return no results on a given day
- Very complex multi-step ranking questions occasionally require the self-healing retry to succeed — a known constraint of smaller, free-tier open models compared to larger proprietary ones

---

## Running locally

```bash
pip install -r requirements.txt

# Set environment variables (or use a .env file)
export GROQ_API_KEY="your_key"
export DATA_GOV_API_KEY="your_key"
export GOOGLE_APPLICATION_CREDENTIALS="path/to/bigquery-key.json"

streamlit run app.py
```
