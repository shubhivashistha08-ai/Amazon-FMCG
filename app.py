import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from agent import build_agent, fetch_google_shopping_peanut_data

st.set_page_config(page_title="FMCG Campaign Intelligence", layout="wide")

# Set dark theme
st.markdown("""
    <style>
        body { background-color: #0a0e27; }
        .stMetric { background-color: rgba(255,255,255,0.05); border-radius: 8px; padding: 15px; }
    </style>
""", unsafe_allow_html=True)

st.markdown(
    "<h2 style='text-align:center; color:white;'>FMCG Campaign & Promotion Intelligence</h2>",
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
    unique_brands = df["brand"].nunique()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🛍️ Products", total_products)
    col2.metric("⭐ Avg Rating", f"{avg_rating:.2f}" if pd.notna(avg_rating) else "N/A")
    col3.metric("💬 Avg Reviews", f"{avg_reviews:.0f}" if pd.notna(avg_reviews) else "N/A")
    col4.metric("🏢 Brands", unique_brands)

    # --------- CHARTS SECTION ---------
    st.markdown("### Market Analysis")
    
    col_brand_presence, col_market_share = st.columns(2)
    
    # LEFT: Brand Market Presence (Bar + Line)
    with col_brand_presence:
        st.markdown("#### Brand Market Presence")
        
        brand_stats = df.groupby("brand").agg({
            "product_id": "count",
            "rating": "mean"
        }).rename(columns={"product_id": "count", "rating": "avg_rating"}).sort_values("count", ascending=False).head(10)
        
        fig, ax1 = plt.subplots(figsize=(10, 5))
        fig.patch.set_facecolor('#0a0e27')
        ax1.set_facecolor('#0a0e27')
        
        # Bar chart for product count
        bars = ax1.bar(range(len(brand_stats)), brand_stats["count"], color="#1f77b4", alpha=0.8, label="Product Count")
        ax1.set_ylabel("Product Count", color="white", fontsize=10, fontweight="bold")
        ax1.tick_params(axis='y', labelcolor="white", labelsize=9)
        ax1.set_xticks(range(len(brand_stats)))
        ax1.set_xticklabels(brand_stats.index, rotation=45, ha="right", color="white", fontsize=9)
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        ax1.spines['left'].set_color('white')
        ax1.spines['bottom'].set_color('white')
        ax1.grid(axis='y', alpha=0.2, color='white')
        
        # Line chart for avg rating (secondary axis)
        ax2 = ax1.twinx()
        ax2.set_facecolor('#0a0e27')
        line = ax2.plot(range(len(brand_stats)), brand_stats["avg_rating"], color="#ff7f0e", marker="o", linewidth=2.5, markersize=7, label="Avg Rating")
        ax2.set_ylabel("Avg Rating", color="white", fontsize=10, fontweight="bold")
        ax2.tick_params(axis='y', labelcolor="white", labelsize=9)
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_color('white')
        ax2.set_ylim([0, 5.5])
        
        plt.tight_layout()
        st.pyplot(fig, use_container_width=True)
    
    # RIGHT: Brand Market Share (Pie Chart)
    with col_market_share:
        st.markdown("#### Brand Market Share")
        
        brand_share = df["brand"].value_counts().head(10)
        other_count = df["brand"].value_counts().iloc[10:].sum() if len(df["brand"].value_counts()) > 10 else 0
        
        if other_count > 0:
            brand_share = pd.concat([brand_share, pd.Series({"Other": other_count})])
        
        fig_pie, ax_pie = plt.subplots(figsize=(8, 5))
        fig_pie.patch.set_facecolor('#0a0e27')
        
        colors = plt.cm.Set3(range(len(brand_share)))
        wedges, texts, autotexts = ax_pie.pie(
            brand_share.values,
            labels=brand_share.index,
            autopct='%1.1f%%',
            colors=colors,
            startangle=90
        )
        
        # Format text colors
        for text in texts:
            text.set_color('white')
            text.set_fontsize(9)
        for autotext in autotexts:
            autotext.set_color('black')
            autotext.set_fontsize(8)
            autotext.set_fontweight('bold')
        
        st.pyplot(fig_pie, use_container_width=True)

    # --------- PRODUCT TABLES ---------
    st.markdown("### Top Products")
    
    col_top_rated, col_most_reviewed = st.columns(2)
    
    with col_top_rated:
        st.markdown("#### ⭐ Top-Rated Products")
        top_rated = df.nlargest(5, "rating")[["title", "rating"]].reset_index(drop=True)
        st.dataframe(top_rated, use_container_width=True, hide_index=True)
    
    with col_most_reviewed:
        st.markdown("#### 💬 Most-Reviewed Products")
        most_reviewed = df.nlargest(5, "review_count")[["title", "review_count"]].reset_index(drop=True)
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
        f"Rating: ⭐{selected_prod_data['rating']} | "
        f"Reviews: 💬{int(selected_prod_data['review_count'])}"
    )
else:
    st.warning("Refresh data first to select a product.")
    selected_product = None

# Chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
if prompt := st.chat_input("Ask campaign strategies (BOGO, influencer, samples, seasonal)..."):
    # Add product context to the prompt
    if not df.empty and selected_product is not None:
        prod = product_options.iloc[selected_product]
        context_prompt = (
            f"For the product '{prod['title']}' (brand: {prod['brand']}, rating: {prod['rating']}, reviews: {int(prod['review_count'])}), "
            f"suggest campaign strategies. User asks: {prompt}"
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
                        "Add credits at [OpenAI Billing](https://platform.openai.com/account/billing/overview)"
                    )
                else:
                    answer = f"❌ Error: {error_msg}"
            st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
