# app.py
import streamlit as st
import pandas as pd
from agent import build_agent, fetch_amazon_peanut_data

st.set_page_config(page_title="FMCG Amazon Promo Agent", layout="wide")

st.markdown(
    "<h2 style='text-align:center;'>FMCG Amazon Promotion Agent (Peanut Butter)</h2>",
    unsafe_allow_html=True,
)

st.write(
    "This app can fetch live Amazon data for viral peanut / nut butter products via SerpAPI, "
    "show basic retail insights, and let you chat with an AI agent about campaigns and promotions. "
    "To avoid using API quota on every page load, click **Refresh data** when you want to update."
)

# ------------------------------------------------
# Data refresh control
# ------------------------------------------------
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame()

col_refresh, col_info = st.columns([1, 3])
with col_refresh:
    refresh_clicked = st.button("🔄 Refresh data from Amazon")
with col_info:
    if st.session_state.df.empty:
        st.caption("No data loaded yet. Click **Refresh data from Amazon** to fetch live products.")
    else:
        st.caption("Using cached data from the last refresh. Click **Refresh** to update if needed.")

if refresh_clicked:
    with st.spinner("Calling SerpAPI and loading latest products..."):
        st.session_state.df = fetch_amazon_peanut_data()

df = st.session_state.df

# ------------------------------------------------
# Overview / basic insights (only if we have data)
# ------------------------------------------------
st.markdown("### Current Amazon Snapshot for Peanut / Nut Butters")

if df.empty:
    st.warning("No data available yet. Click **Refresh data from Amazon** above to fetch live data.")
else:
    # High-level KPIs
    unique_products = df["asin"].nunique()
    avg_price = df["price"].dropna().mean()
    avg_discount = df["discount_pct"].mean()
    avg_rating = df["rating"].dropna().mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Products fetched", unique_products)
    c2.metric("Avg price", f"{avg_price:,.2f}")
    c3.metric("Avg discount (%)", f"{avg_discount:.1f}")
    c4.metric("Avg rating", f"{avg_rating:.2f}" if pd.notna(avg_rating) else "N/A")

    # Small table of top products
    st.markdown("#### Top products by visibility (sales proxy)")
    top_df = (
        df.sort_values("sales_proxy", ascending=False)
          .head(10)[
              [
                  "asin",
                  "title",
                  "brand",
                  "price",
                  "discount_pct",
                  "rating",
                  "review_count",
                  "search_position",
              ]
          ]
    )
    st.dataframe(top_df, use_container_width=True)

# ------------------------------------------------
# Chat agent section
# ------------------------------------------------
st.markdown("---")
st.markdown("### Ask the AI agent about campaigns, products, or promo strategies")

if "agent" not in st.session_state:
    st.session_state.agent = build_agent()
if "messages" not in st.session_state:
    st.session_state.messages = []

# Show history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User input
if prompt := st.chat_input("Ask about campaigns, products, or promo strategies..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Agent is analyzing data (using last fetched snapshot)..."):
            try:
                # Agent still fetches live inside tools if you call them;
                # this keeps the structure but you can later change tools to use st.session_state.df.
                result = st.session_state.agent({"input": prompt})
                answer = getattr(result, "content", str(result))
            except Exception as e:
                answer = f"Error from agent: {e}"
            st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
