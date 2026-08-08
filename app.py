"""
app.py
Main Streamlit UI for the "Ask Your Mandi Data" project.
Wires together: nl_to_sql -> query_executor -> summarizer -> visualizer
"""

import streamlit as st
from nl_to_sql import question_to_sql, fix_sql
from query_executor import run_query
from summarizer import summarize
from visualizer import auto_chart

st.set_page_config(page_title="Ask Your Mandi Data", page_icon="🌾", layout="centered")

st.title("🌾 Ask Your Mandi Data")
st.caption("Ask questions in plain English about Indian commodity market (mandi) prices.")

# ---------- Session state for chat history ----------
if "history" not in st.session_state:
    st.session_state.history = []  # list of dicts: {question, sql, df, chart, summary, error}


# ---------- Handle a new question ----------
def handle_question(question: str):
    with st.spinner("Thinking..."):
        sql = question_to_sql(question)
        success, result, status = run_query(sql)

        retried = False
        # Self-healing: only retry on genuine SQL errors, not blocked/invalid-question cases
        if not success and status == "sql_error":
            retried = True
            fixed_sql = fix_sql(question, sql, result)
            success2, result2, status2 = run_query(fixed_sql)
            if success2:
                sql, success, result, status = fixed_sql, success2, result2, status2

        entry = {"question": question, "sql": sql, "retried": retried and success}

        if not success:
            entry["error"] = result
        else:
            df = result
            entry["df"] = df
            entry["chart"] = auto_chart(df)
            entry["summary"] = summarize(question, df)

        st.session_state.history.append(entry)


# ---------- Input box ----------
with st.form(key="question_form", clear_on_submit=True):
    question = st.text_input("Your question", placeholder="e.g. What's the average onion price in Maharashtra?")
    submitted = st.form_submit_button("Ask")

if submitted and question.strip():
    handle_question(question.strip())

# ---------- Sample questions ----------
with st.expander("💡 Try one of these"):
    samples = [
        "What is the average modal price of onion in Maharashtra?",
        "Show top 5 commodities by max price in Gujarat",
        "Which states have the highest average commodity prices?",
    ]
    cols = st.columns(len(samples))
    for col, s in zip(cols, samples):
        if col.button(s, use_container_width=True):
            handle_question(s)

st.divider()

# ---------- Display chat history (newest first) ----------
for entry in reversed(st.session_state.history):
    st.markdown(f"**🧑 You:** {entry['question']}")

    if "error" in entry:
        st.warning(entry["error"])
    else:
        if entry.get("retried"):
            st.caption("🔧 Auto-corrected after an initial query error")
        with st.expander("Show generated SQL"):
            st.code(entry["sql"], language="sql")

        if entry.get("chart") is not None:
            st.plotly_chart(entry["chart"], use_container_width=True)

        st.dataframe(entry["df"], use_container_width=True)

        st.markdown(f"**🤖 Answer:** {entry['summary']}")

    st.divider()

if not st.session_state.history:
    st.info("Ask a question above, or try one of the sample questions to get started.")
