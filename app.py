import streamlit as st
import pandas as pd
from agent import build_agent, fetch_google_shopping_peanut_data

st.set_page_config(page_title="FMCG Promo Intelligence Agent", layout="wide")

st.markdown(
    "<h2 style='text-align:center;'>FMCG Promo Intelligence Agent (Google Shopping → Amazon Signal)</h2>",
    unsafe_allow_html=True,
)

st.write(
    "This app fetches live **Google Shopping market data** for viral peanut / nut butter products, "
    "uses it as a **proxy for Amazon demand**, shows retail insights, and lets you chat with an AI "
    "agent about campaigns and promotions. "
    "To avoid using API quota on every page load, click **Refresh Data** when you want to update."
)

# ------------------------------------------------
# Data refresh control
# ------------------------------------------------
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame()

col_refresh, col_info = st.columns([1, 3])
with col_refresh:
    refresh_clicked = st.button("🔄 Refresh market data")
with col_info:
    if st.session_state.df.empty:
        st.caption("No data loaded yet. Click **Refresh market data** to fetch live products.")
    else:
        st.caption("Using cached data from the last refresh.")

if refresh_clicked:
    with st.spinner("Calling SerpAPI (Google Shopping) and loading latest market data..."):
        st.session_state.df = fetch_google_shopping_peanut_data()

df = st.session_state.df

# ------------------------------------------------
# Overview / basic insights
# ------------------------------------------------
st.markdown("### Current Market Snapshot (Google Shopping → Amazon Proxy)")

if df.empty:
    st.warning("No data available yet. Click **Refresh market data** above.")
else:
    unique_products = df["product_id"].nunique()
    avg_price = df["price"].dropna().mean()
    avg_rating = df["rating"].dropna().mean()

    c1, c2, c3 = st.columns(3)
    c1.metric("Products fetched", unique_products)
    c2.metric("Avg price", f"{avg_price:,.2f}")
    c3.metric("Avg rating", f"{avg_rating:.2f}" if pd.notna(avg_rating) else "N/A")

    st.markdown("#### Top products by visibility (sales proxy)")
    top_df = (
        df.sort_values("sales_proxy", ascending=False)
          .head(10)[
              [
                  "product_id",
                  "title",
                  "brand",
                  "price",
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

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask about campaigns, products, or promo strategies..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Agent is analyzing live market data..."):
            try:
                result = st.session_state.agent({"input": prompt})
                answer = getattr(result, "content", str(result))
            except Exception as e:
                answer = f"Error from agent: {e}"
            st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
