import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from agent import build_agent, fetch_google_shopping_peanut_data

st.set_page_config(page_title="FMCG Promo Intelligence Agent", layout="wide")

st.markdown(
    "<h2 style='text-align:center;'>FMCG Campaign & Promotion Intelligence</h2>",
    unsafe_allow_html=True,
)

st.write(
    "Analyze live **Google Shopping market data** for peanut / nut butter products. "
    "See **brand visibility**, **product ratings**, and **review volume** to plan campaigns like BOGO, influencer marketing, and samples."
)

# ------------------------------------------------
# Data refresh control
# ------------------------------------------------
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame()

refresh_clicked = st.button("🔄 Refresh market data")

if refresh_clicked:
    with st.spinner("Fetching latest market data..."):
        st.session_state.df = fetch_google_shopping_peanut_data()

df = st.session_state.df

# ------------------------------------------------
# Campaign-focused Overview / KPIs
# ------------------------------------------------
st.markdown("### Market Overview")

if df.empty:
    st.warning("No data available. Click **Refresh market data** above.")
else:
    # Campaign-focused metrics
    total_products = df["product_id"].nunique()
    avg_rating = df["rating"].dropna().mean()
    avg_reviews = df["review_count"].dropna().mean()
    sponsored_pct = (df["is_sponsored"].sum() / len(df) * 100) if len(df) > 0 else 0
    unique_brands = df["brand"].nunique()

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("🛍️ Products", total_products)
    col2.metric("⭐ Avg Rating", f"{avg_rating:.2f}" if pd.notna(avg_rating) else "N/A")
    col3.metric("💬 Avg Reviews", f"{avg_reviews:.0f}" if pd.notna(avg_reviews) else "N/A")
    col4.metric("📢 Promoted %", f"{sponsored_pct:.1f}%")
    col5.metric("🏢 Brands", unique_brands)

    # --------- Brand Visibility Chart ---------
    st.markdown("#### Brand Market Presence")
    
    brand_counts = df["brand"].value_counts().head(10)
    
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.barh(brand_counts.index, brand_counts.values, color="#1f77b4")
    ax.set_xlabel("Number of Products Listed")
    ax.set_title("Top 10 Brands by Product Count (Market Visibility)")
    ax.invert_yaxis()
    st.pyplot(fig)

    # --------- Top-Rated Products (for influencer marketing) ---------
    st.markdown("#### Top-Rated Products (Influencer Marketing Candidates)")
    top_rated = df.nlargest(5, "rating")[["title", "brand", "rating", "review_count"]].reset_index(drop=True)
    st.dataframe(top_rated, use_container_width=True, hide_index=True)

    # --------- Most-Reviewed Products (high social proof) ---------
    st.markdown("#### Most-Reviewed Products (High Social Proof)")
    most_reviewed = df.nlargest(5, "review_count")[["title", "brand", "review_count", "rating"]].reset_index(drop=True)
    st.dataframe(most_reviewed, use_container_width=True, hide_index=True)

    # --------- Full product table ---------
    st.markdown("#### All Products by Search Visibility")
    display_df = (
        df.sort_values("sales_proxy", ascending=False)
          .head(20)[["title", "brand", "rating", "review_count", "search_position", "is_sponsored"]]
          .reset_index(drop=True)
    )
    st.dataframe(display_df, use_container_width=True, hide_index=True)

# ------------------------------------------------
# Chat agent section (with error handling)
# ------------------------------------------------
st.markdown("---")
st.markdown("### AI Campaign Advisor")
st.caption("Ask about BOGO offers, influencer partnerships, free samples, seasonal campaigns, or brand strategies.")

if "agent" not in st.session_state:
    st.session_state.agent = build_agent()
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask about campaigns, BOGO, influencer marketing, or brand strategies..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analyzing market data..."):
            try:
                result = st.session_state.agent({"input": prompt})
                answer = getattr(result, "content", str(result))
            except Exception as e:
                error_msg = str(e)
                if "insufficient_quota" in error_msg.lower():
                    answer = (
                        "⚠️ **OpenAI API Quota Exceeded**\n\n"
                        "Your OpenAI account has no remaining credits. "
                        "Please:\n"
                        "1. Go to [OpenAI Dashboard](https://platform.openai.com/account/billing/overview)\n"
                        "2. Add a payment method or check your billing status\n"
                        "3. Wait ~5 minutes for quota to reset\n\n"
                        "In the meantime, use the data tables above to plan campaigns."
                    )
                else:
                    answer = f"❌ Error: {error_msg}\n\nTry again or check your OpenAI API key in Streamlit secrets."
            st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
