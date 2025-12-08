import requests
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, timedelta

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# -------------------------------
# Load API Keys from Streamlit Secrets
# -------------------------------
SERPAPI_API_KEY = st.secrets.get("SERPAPI_API_KEY")
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY")

if not SERPAPI_API_KEY:
    raise RuntimeError("❌ SERPAPI_API_KEY missing in Streamlit secrets.")

if not OPENAI_API_KEY:
    raise RuntimeError("❌ OPENAI_API_KEY missing in Streamlit secrets.")

# ===============================
# ENHANCED: Sales & Campaign Data (FIXED)
# ===============================

def generate_synthetic_campaign_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enhance dataframe with synthetic metrics.
    FIXED: Properly handle data types to avoid TypeError
    """
    
    # 1. Convert price to numeric (handle string prices)
    if "price" in df.columns:
        df["price"] = pd.to_numeric(df["price"], errors='coerce')
    
    # 2. Sales estimate (proxy: search position + rating + reviews)
    df["sales_proxy"] = 1000.0 / df["search_position"].clip(lower=1)
    
    # 3. Competitor count & avg price
    df["competitor_count"] = df.groupby("category")["product_id"].transform("count") - 1
    df["competitor_count"] = df["competitor_count"].clip(lower=0)
    
    # Average price in same category
    avg_cat_price = df.groupby("category")["price"].transform("mean")
    df["avg_competitor_price"] = avg_cat_price.fillna(df["price"].mean())
    
    # 4. Price positioning (FIXED: ensure numeric before calculation)
    df["price_vs_market"] = 0.0
    mask = (df["price"].notna()) & (df["avg_competitor_price"] > 0)
    df.loc[mask, "price_vs_market"] = (
        ((df.loc[mask, "price"] - df.loc[mask, "avg_competitor_price"]) / 
         df.loc[mask, "avg_competitor_price"] * 100).round(2)
    )
    
    return df


# -------------------------------
# Google Shopping Fetch Function
# -------------------------------
def fetch_google_shopping_peanut_data(
    keyword: str = "high protein peanut butter",
    max_items: int = 20
) -> pd.DataFrame:

    params = {
        "engine": "google_shopping",
        "q": keyword,
        "hl": "en",
        "gl": "us",
        "api_key": SERPAPI_API_KEY,
        "num": max_items,
    }

    try:
        resp = requests.get(
            "https://serpapi.com/search.json",
            params=params,
            timeout=30
        )

        if resp.status_code != 200:
            st.error(f"❌ SerpAPI Error {resp.status_code}")
            return pd.DataFrame()

        data = resp.json()

    except Exception as e:
        st.error(f"❌ SerpAPI Request Failed: {e}")
        return pd.DataFrame()

    results = data.get("shopping_results", [])

    if not results:
        st.warning("⚠️ No Google Shopping results returned.")
        return pd.DataFrame()

    products = []

    for p in results:
        product_id = p.get("product_id")
        title = p.get("title")

        if not product_id or not title:
            continue

        # Extract price - handle different formats
        price = None
        if isinstance(p.get("price"), dict):
            price = p["price"].get("value")
        elif isinstance(p.get("price"), (int, float)):
            price = p.get("price")
        elif isinstance(p.get("price"), str):
            try:
                price = float(p.get("price"))
            except:
                price = None

        rating = p.get("rating")
        reviews = p.get("reviews")
        position = p.get("position", 1000)

        products.append(
            {
                "product_id": product_id,
                "title": title,
                "brand": p.get("source", "Unknown"),
                "category": "Peanut / Nut Butter",
                "price": price,
                "list_price": None,
                "rating": rating,
                "review_count": reviews if reviews else 0,
                "search_position": position if position else 1000,
                "is_sponsored": int(p.get("sponsored", False)),
            }
        )

    df = pd.DataFrame(products)

    if df.empty:
        return df

    # Add base metrics
    df["discount_pct"] = 0.0
    df["search_position"] = df["search_position"].fillna(1000).astype(int)
    df["sales_proxy"] = 1000.0 / df["search_position"].clip(lower=1)
    
    # Ensure numeric types
    df["rating"] = pd.to_numeric(df["rating"], errors='coerce')
    df["review_count"] = pd.to_numeric(df["review_count"], errors='coerce').fillna(0).astype(int)
    df["price"] = pd.to_numeric(df["price"], errors='coerce')

    # ✅ ADD ENHANCED DATA (with fixed data types)
    df = generate_synthetic_campaign_data(df)

    return df


# ===============================
# LangChain Tools
# ===============================

@tool
def get_top_products(n: int = 5) -> str:
    """Return the top N products by sales proxy."""
    df = fetch_google_shopping_peanut_data()

    if df.empty:
        return "No products found from Google Shopping."

    df = df.sort_values("sales_proxy", ascending=False).head(int(n))

    rows = []
    for _, r in df.iterrows():
        price_str = f"${r['price']:.2f}" if pd.notna(r['price']) else 'N/A'
        rating_str = f"{r['rating']:.1f}" if pd.notna(r['rating']) else 'N/A'
        rows.append(
            f"ID {r['product_id']} | {r['title']} | "
            f"brand={r['brand']} | price={price_str} | "
            f"rating={rating_str} | "
            f"reviews={int(r['review_count'])}"
        )

    return "\n".join(rows)


@tool
def get_brand_analysis(n: int = 5) -> str:
    """Analyze top brands by product count and average rating."""
    df = fetch_google_shopping_peanut_data()

    if df.empty:
        return "No data available."

    brand_stats = df.groupby("brand").agg({
        "product_id": "count",
        "rating": "mean",
        "review_count": "sum"
    }).rename(columns={
        "product_id": "product_count",
        "rating": "avg_rating"
    }).sort_values("product_count", ascending=False).head(int(n))

    rows = ["Top Brands Analysis:"]
    for brand, row in brand_stats.iterrows():
        rows.append(
            f"{brand}: {int(row['product_count'])} products, "
            f"avg rating {row['avg_rating']:.2f}, "
            f"total reviews {int(row['review_count'])}"
        )

    return "\n".join(rows)


@tool
def product_recommendation(category: str = "peanut butter") -> str:
    """Get product recommendations based on reviews and ratings."""
    df = fetch_google_shopping_peanut_data()

    if df.empty:
        return "No products available."

    # Filter by category
    category_df = df[df["category"].str.contains(category, case=False, na=False)]
    
    if category_df.empty:
        category_df = df

    # Top 5 by rating and review count combination
    category_df = category_df[category_df["review_count"] >= 5]  # At least 5 reviews
    
    if category_df.empty:
        top_products = df.nlargest(5, "rating")
    else:
        # Score: 70% rating + 30% review popularity
        category_df["score"] = (
            (category_df["rating"].fillna(0) / 5.0 * 70) +
            (category_df["review_count"].fillna(0) / category_df["review_count"].max() * 30)
        )
        top_products = category_df.nlargest(5, "score")

    rows = [f"Top Recommendations in {category}:"]
    for _, r in top_products.iterrows():
        price_str = f"${r['price']:.2f}" if pd.notna(r['price']) else 'N/A'
        rating_str = f"{r['rating']:.1f}" if pd.notna(r['rating']) else 'N/A'
        rows.append(
            f"• {r['title']} ({r['brand']}) - "
            f"Rating: {rating_str} "
            f"({int(r['review_count'])} reviews) - "
            f"{price_str}"
        )

    return "\n".join(rows)


# ===============================
# Build the Agent
# ===============================

def build_agent():
    """Return Google Shopping FMCG Analysis Agent."""

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.1,
        api_key=OPENAI_API_KEY
    )

    tools = [
        get_top_products,
        get_brand_analysis,
        product_recommendation
    ]

    llm_with_tools = llm.bind_tools(tools)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a retail and marketing analytics assistant focused on FMCG food products. "
                "You analyze Google Shopping market data to provide insights on brands, products, and market trends. "
                "Provide specific, actionable recommendations based on data."
            ),
            MessagesPlaceholder("agent_scratchpad"),
            ("human", "{input}"),
        ]
    )

    def chain(inputs: dict):
        messages = prompt.format_messages(
            input=inputs["input"],
            agent_scratchpad=[]
        )
        return llm_with_tools.invoke(messages)

    return chain
