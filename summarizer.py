"""
summarizer.py
Takes a question + its SQL result table, and returns a short,
plain-English summary using Gemini 3 Flash.
"""

import os
import pandas as pd
from google import genai

# ---------- CONFIG ----------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "PASTE_YOUR_KEY_HERE")
MODEL_ID = "gemini-3-flash-preview"

client = genai.Client(api_key=GEMINI_API_KEY)

SUMMARY_PROMPT = """
You are a data analyst assistant. Given a user's question and the resulting
data table (as CSV text), write a short, plain-English answer.

Rules:
1. Maximum 2 sentences.
2. Use actual numbers from the data, formatted naturally (e.g. "₹7,021" not "7021.127962").
3. No SQL, no column names, no technical jargon — just answer like a helpful analyst would speak.
4. If the table is empty, say no matching data was found.
"""


def summarize(question: str, result_df: pd.DataFrame) -> str:
    if result_df is None or result_df.empty:
        return "No matching data was found for that question."

    # Cap rows sent to the model to keep prompts small or costs down
    csv_snippet = result_df.head(20).to_csv(index=False)

    prompt = f"""{SUMMARY_PROMPT}

Question: {question}

Data (CSV):
{csv_snippet}

Answer:"""

    response = client.models.generate_content(
        model=MODEL_ID,
        contents=prompt,
    )
    return response.text.strip()


if __name__ == "__main__":
    # Quick manual test with a fake result table
    sample_df = pd.DataFrame({
        "state_name": ["Mizoram", "Manipur", "Keralam", "Meghalaya", "Karnataka"],
        "avg_price": [26666.67, 8245.83, 7839.19, 7772.73, 7021.13],
    })

    question = "Which states have the highest average commodity prices?"
    print("Question:", question)
    print("Summary:", summarize(question, sample_df))