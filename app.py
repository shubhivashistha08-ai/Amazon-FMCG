import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from agent import build_agent, fetch_google_shopping_peanut_data

st.set_page_config(page_title="FMCG Campaign Intelligence", layout="wide")

st.markdown(
    "<h2 style='text-align:center;'>FMCG Campaign & Promotion Intelligence</h2>",
    unsafe_allow_html=True,
)

st.write(
    "Analyze live Google Shopping market data for peanut / nut butter products. "
    "See brand visibility, product ratings, and review volume to plan campaigns."
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
    # KPIs
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

    # --------- DUAL CHART: Brand Visibility (Line + Bar) ---------
    st.markdown("### Brand Market Presence")
    
    col_chart, col_tables = st.columns([1.2, 1])
    
    with col_chart:
        brand_stats = df.groupby("brand").agg({
            "product_id": "count",
            "rating": "mean"
        }).rename(columns={"product_id": "count", "rating": "avg_rating"}).sort_values("count", ascending=False).head(10)
        
        # Create figure with dual axis
        fig, ax1 = plt.subplots(figsize=(10, 6))
        fig.patch.set_facecolor('white')
        ax1.set_facecolor('white')
        
        # Bar chart for product count
        bars = ax1.bar(range(len(brand_stats)), brand_stats["count"], color="#1f77b4", alpha=0.7, label="Product Count")
        ax1.set_ylabel("Product Count", color="white", fontsize=10)
        ax1.tick_params(axis='y', labelcolor="white")
        ax1.set_xticks(range(len(brand_stats)))
        ax1.set_xticklabels(brand_stats.index, rotation=45, ha="right", color="white", fontsize=9)
        ax1.set_title("Brand Market Presence", color="white", fontsize=12, fontweight="bold")
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        ax1.spines['left'].set_color('white')
        ax1.spines['bottom'].set_color('white')
        
        # Line chart for avg rating (on secondary axis)
        ax2 = ax1.twinx()
        ax2.set_facecolor('white')
        line = ax2.plot(range(len(brand_stats)), brand_stats["avg_rating"], color="#ff7f0e", marker="o", linewidth=2, markersize=6, label="Avg Rating")
        ax2.set_ylabel("Avg Rating", color="white", fontsize=10)
        ax2.tick_params(axis='y', labelcolor="white")
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_color('white')
        
        plt.tight_layout()
        st.pyplot(fig)
    
    with col_tables:
        # Top-Rated Products
        st.markdown("#### ⭐ Top-Rated Products")
        top_rated = df.nlargest(5, "rating")[["title", "rating", "review_count"]].reset_index(drop=True)
        st.dataframe(top_rated, use_container_width=True, hide_index=True)
        
        st.markdown("")
        
        # Most-Reviewed Products
        st.markdown("#### 💬 Most-Reviewed Products")
        most_reviewed = df.nlargest(5, "review_count")[["title", "review_count", "rating"]].reset_index(drop=True)
        st.dataframe(most_reviewed, use_container_width=True, hide_index=True)

# ------------------------------------------------
# Chat agent section with product selector
# ------------------------------------------------
st.markdown("---")
st.markdown("### AI Campaign Advisor")

if "agent" not in st.session_state:
    st.session_state.agent = build_agent()
if "messages" not in st.session_state:
    st.session_state.messages = []

# Product selector dropdown
if not df.empty:
    product_options = df[["product_id", "title", "brand", "rating", "review_count"]].drop_duplicates()
    selected_product = st.selectbox(
        "Select a product for campaign analysis:",
        options=range(len(product_options)),
        format_func=lambda i: f"{product_options.iloc[i]['title']} ({product_options.iloc[i]['brand']}) - ⭐{product_options.iloc[i]['rating']}"
    )
    
    selected_prod_data = product_options.iloc[selected_product]
    st.caption(
        f"**Selected**: {selected_prod_data['title']} | "
        f"Brand: {selected_prod_data['brand']} | "
        f"Rating: {selected_prod_data['rating']} | "
        f"Reviews: {selected_prod_data['review_count']}"
    )
else:
    st.warning("Refresh data first to select a product.")
    selected_product = None

# Chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
if prompt := st.chat_input("Ask campaign strategies for the selected product..."):
    # Add product context to the prompt
    if not df.empty and selected_product is not None:
        prod = product_options.iloc[selected_product]
        context_prompt = (
            f"For the product '{prod['title']}' (brand: {prod['brand']}, rating: {prod['rating']}, reviews: {prod['review_count']}): {prompt}"
        )
    else:
        context_prompt = prompt
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analyzing campaign strategies..."):
            try:
                result = st.session_state.agent({"input": context_prompt})
                answer = getattr(result, "content", str(result))
            except Exception as e:
                error_msg = str(e)
                if "insufficient_quota" in error_msg.lower():
                    answer = (
                        "⚠️ **OpenAI API Quota Exceeded**\n\n"
                        "Your OpenAI account needs a payment method. "
                        "Please add credits at [OpenAI Billing](https://platform.openai.com/account/billing/overview)"
                    )
                else:
                    answer = f"❌ Error: {error_msg}"
            st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
