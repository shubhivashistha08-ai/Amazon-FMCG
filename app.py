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
    "This app fetches live Amazon data for viral peanut / nut butter products via SerpAPI, "
    "shows basic retail insights, and lets you chat with an AI agent about campaigns, "
    "promotion strategies, and product performance."
)

# ------------------------------------------------
# Overview / basic insights
# ------------------------------------------------
st.markdown("### Current Amazon Snapshot for Peanut / Nut Butters")

with st.spinner("Loading latest products from Amazon via SerpAPI..."):
    df = fetch_amazon_peanut_data()

if df.empty:
    st.warning("No live products returned from SerpAPI. Check your API key or quota.")
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

# Build agent once
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
    # log user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markmarkdown(prompt)

    # agent response
    with st.chat_message("assistant"):
        with st.spinner("Agent is analyzing live Amazon data..."):
            try:
                result = st.session_state.agent({"input": prompt})
                # result is an AIMessage; get its text
                answer = getattr(result, "content", str(result))
            except Exception as e:
                answer = f"Error from agent: {e}"
            st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
