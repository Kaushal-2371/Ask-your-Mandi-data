"""
visualizer.py
Automatically picks and builds a Plotly chart based on the shape
of the query result DataFrame — bar, line, or plain table.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def auto_chart(df: pd.DataFrame):
    """
    Decides the best chart type based on column types and returns
    a Plotly figure. Falls back to a table if no good chart fits.
    """
    if df is None or df.empty:
        return None

    # Identify column types
    date_cols = [c for c in df.columns if "date" in c.lower()]
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    text_cols = df.select_dtypes(include=["object", "string"]).columns.tolist()

    # Case 1: time series -> line chart
    if date_cols and numeric_cols:
        x_col = date_cols[0]
        y_col = numeric_cols[0]
        df_sorted = df.sort_values(by=x_col)
        fig = px.line(df_sorted, x=x_col, y=y_col, markers=True,
                       title=f"{y_col.replace('_', ' ').title()} over {x_col.replace('_', ' ').title()}")
        return fig

    # Case 2: one category column + one numeric column, few rows -> bar chart
    if text_cols and numeric_cols and len(df) <= 30:
        x_col = text_cols[0]
        y_col = numeric_cols[0]
        df_sorted = df.sort_values(by=y_col, ascending=False)
        fig = px.bar(df_sorted, x=x_col, y=y_col,
                     title=f"{y_col.replace('_', ' ').title()} by {x_col.replace('_', ' ').title()}")
        fig.update_layout(xaxis_tickangle=-45)
        return fig

    # Case 3: single numeric value (e.g. AVG query with 1 row, 1 column) -> big number display
    if len(df) == 1 and len(numeric_cols) == 1:
        col_name = numeric_cols[0]
        value = df[col_name].iloc[0]
        is_price = "price" in col_name.lower()
        fig = go.Figure(go.Indicator(
            mode="number",
            value=value,
            number={"prefix": "₹" if is_price else "", "valueformat": ",.0f"},
            title={"text": col_name.replace("_", " ").title()},
        ))
        return fig

    # Fallback: no chart, caller should just show the table
    return None


if __name__ == "__main__":
    # Test 1: category + numeric -> bar chart
    df1 = pd.DataFrame({
        "state_name": ["Mizoram", "Manipur", "Keralam", "Meghalaya", "Karnataka"],
        "avg_price": [26666.67, 8245.83, 7839.19, 7772.73, 7021.13],
    })
    fig1 = auto_chart(df1)
    print("Test 1 (bar chart):", "Figure created" if fig1 else "No chart")
    fig1.write_html("test_bar_chart.html")

    # Test 2: single value -> number indicator
    df2 = pd.DataFrame({"avg_price": [7021.13]})
    fig2 = auto_chart(df2)
    print("Test 2 (number indicator):", "Figure created" if fig2 else "No chart")
    fig2.write_html("test_number.html")

    print("\nOpen test_bar_chart.html and test_number.html in your browser to check them visually.")