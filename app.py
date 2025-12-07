import streamlit as st
import pandas as pd
from agent import build_agent, fetch_google_shopping_peanut_data

st.set_page_config(page_title="FMCG Promo Intelligence Agent", layout="wide")

st.markdown(
    "<h2 style='text-align:center;'>FMCG Campaign & Promotion Intelligence (Google Shopping → Amazon Signal)</h2>",
    unsafe_allow_html=True,
)

st.write(
    "This app analyzes live **Google Shopping market data** for peanut / nut butter products as a proxy for **Amazon demand**, "
    "shows **campaign readiness metrics**, and lets you chat with an AI agent about promotion strategies like BOGO, influencer marketing, and samples. "
    "Click **Refresh market data** to update."
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
# Campaign-focused Overview / KPIs
# ------------------------------------------------
st.markdown("### Campaign Market Snapshot (Google Shopping → Amazon Proxy)")

if df.empty:
    st.warning("No data available yet. Click **Refresh market data** above.")
else:
    # Campaign-focused metrics
    total_products = df["product_id"].nunique()
    avg_price = df["price"].dropna().mean()
    avg_rating = df["rating"].dropna().mean()
    avg_reviews = df["review_count"].dropna().mean()
    sponsored_pct = (df["is_sponsored"].sum() / len(df) * 100) if len(df) > 0 else 0

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("🛍️ Products", total_products)
    col2.metric("💰 Avg Price", f"${avg_price:,.0f}" if pd.notna(avg_price) else "N/A")
    col3.metric("⭐ Avg Rating", f"{avg_rating:.2f}" if pd.notna(avg_rating) else "N/A")
    col4.metric("💬 Avg Reviews", f"{avg_reviews:.0f}" if pd.notna(avg_reviews) else "N/A")
    col5.metric("📢 Sponsored %", f"{sponsored_pct:.1f}%")

    # Campaign insights
    st.markdown("#### Strategic Insights for Campaign Planning")
    
    insight_cols = st.columns(2)
    
    with insight_cols[0]:
        st.markdown("**Top-Rated Products** (Best for Influencer Marketing)")
        top_rated = df.nlargest(5, "rating")[["title", "brand", "rating", "review_count"]]
        st.dataframe(top_rated, use_container_width=True)
    
    with insight_cols[1]:
        st.markdown("**Most-Reviewed Products** (High Social Proof)")
        most_reviewed = df.nlargest(5, "review_count")[["title", "brand", "review_count", "rating"]]
        st.dataframe(most_reviewed, use_container_width=True)

    # Full product table
    st.markdown("#### All Products by Search Visibility (Campaign Priority)")
    top_df = (
        df.sort_values("sales_proxy", ascending=False)
          .head(15)[
              [
                  "product_id",
                  "title",
                  "brand",
                  "price",
                  "rating",
                  "review_count",
                  "search_position",
                  "is_sponsored",
              ]
          ]
    )
    st.dataframe(top_df, use_container_width=True)

# ------------------------------------------------
# Chat agent section
# ------------------------------------------------
st.markdown("---")
st.markdown("### AI Agent: Campaign & Promo Strategy Advisor")
st.caption("Ask about BOGO offers, influencer partnerships, free samples, seasonal campaigns, or discount strategies.")

if "agent" not in st.session_state:
    st.session_state.agent = build_agent()
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask about BOGO, influencer marketing, samples, or campaigns..."):
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
