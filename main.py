import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os

st.set_page_config(page_title="FinTrack", page_icon="🪙", layout="wide")
st.markdown(
        """
        <h1 style='text-align: center; color: #1ABC9C;'>
            🪙 FinTrack
        </h1>
        <p style='text-align: center; color: white; font-size: 22px;'>
            Track your monthly expenses and visualize your spending patterns
        </p>
        <hr style='margin-top: 10px;'>
        """,
        unsafe_allow_html=True
    )

CATEGORY_FILE = "categories.json"

if "categories" not in st.session_state:
    st.session_state.categories = {
        "Uncategorized": []
    }

if os.path.exists(CATEGORY_FILE):
    with open(CATEGORY_FILE, "r") as f:
        st.session_state.categories = json.load(f)


def save_categories():
    with open(CATEGORY_FILE, "w") as f:
        json.dump(st.session_state.categories, f)


def categorize_transactions(df):
    df["Category"] = "Uncategorized"
    for cat, keywords in st.session_state.categories.items():
        if not keywords or cat == "Uncategorized":
            continue
        lower_keywords = [kw.lower().strip() for kw in keywords]
        for idx, row in df.iterrows():
            details = row["Details"].lower().strip()
            if details in lower_keywords:
                df.at[idx, "Category"] = cat
    return df


def load_transactions(file):
    try:
        df = pd.read_csv(file)
        df.columns = [c.strip() for c in df.columns]
        df["Amount"] = df["Amount"].str.replace(",", "").astype(float)
        df["Date"] = pd.to_datetime(df["Date"], format="%d %b %Y")
        return categorize_transactions(df)
    except Exception as e:
        st.error(f"Failed to load file: {e}")
        return None


def add_keyword_to_category(category, keyword):
    keyword = keyword.strip()
    if keyword and keyword not in st.session_state.categories[category]:
        st.session_state.categories[category].append(keyword)
        save_categories()
        return True
    return False


def main():
    st.title("Dashboard")
    uploaded_file = st.file_uploader("Upload your Transactions CSV", type=["csv"])

    if uploaded_file:
        df = load_transactions(uploaded_file)
        if df is None:
            return

        expenses_df = df[df["Debit/Credit"] == "Debit"].copy()
        income_df = df[df["Debit/Credit"] == "Credit"].copy()

        total_expense = expenses_df["Amount"].sum()
        total_income = income_df["Amount"].sum()
        net_balance = total_income - total_expense

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Expenses", f"{total_expense:,.2f} AED")
        col2.metric("Total Income", f"{total_income:,.2f} AED")
        col3.metric("Net Balance", f"{net_balance:,.2f} AED")

        st.session_state.expenses_df = expenses_df.copy()

        tab_exp, tab_inc = st.tabs(["Expenses", "Income"])

        with tab_exp:
            new_cat = st.text_input("Add New Category")
            add_btn = st.button("Add Category")
            if add_btn and new_cat:
                if new_cat not in st.session_state.categories:
                    st.session_state.categories[new_cat] = []
                    save_categories()
                    st.rerun()

            st.subheader("Your Expenses Table")
            edited_exp = st.data_editor(
                st.session_state.expenses_df[["Date", "Details", "Amount", "Category"]],
                column_config={
                    "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                    "Amount": st.column_config.NumberColumn("Amount", format="%.2f AED"),
                    "Category": st.column_config.SelectboxColumn(
                        "Category", options=list(st.session_state.categories.keys())
                    )
                },
                hide_index=True,
                use_container_width=True,
                key="exp_editor"
            )

            apply_btn = st.button("Apply Changes", type="primary")
            if apply_btn:
                for idx, row in edited_exp.iterrows():
                    cat = row["Category"]
                    if cat != st.session_state.expenses_df.at[idx, "Category"]:
                        st.session_state.expenses_df.at[idx, "Category"] = cat
                        add_keyword_to_category(cat, row["Details"])

            st.subheader("Expense Summary")
            cat_totals = st.session_state.expenses_df.groupby("Category")["Amount"].sum().reset_index()
            cat_totals = cat_totals.sort_values("Amount", ascending=False)
            st.dataframe(cat_totals, use_container_width=True, hide_index=True)
            fig = px.pie(cat_totals, values="Amount", names="Category", title="Expenses by Category")
            st.plotly_chart(fig, use_container_width=True)

        with tab_inc:
            st.subheader("Income Details")
            st.metric("Total Income", f"{total_income:,.2f} AED")
            st.write(income_df)


main()
