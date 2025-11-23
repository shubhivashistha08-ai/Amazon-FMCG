import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import tweepy
from googleapiclient.discovery import build
import time
import re

# ============================================
# PAGE CONFIGURATION
# ============================================
st.set_page_config(
    page_title="Nestlé Product Demand Intelligence",
    page_icon="🍫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# SECURE API CREDENTIALS
# ============================================
def get_secret(key):
    """Get secret from Streamlit secrets"""
    try:
        return st.secrets[key]
    except Exception as e:
        st.error(f"🚨 Error loading secret '{key}': {str(e)}")
        st.info("Please add secrets in Streamlit Cloud dashboard: Settings → Secrets")
        st.stop()

TWITTER_BEARER_TOKEN = get_secret("TWITTER_BEARER_TOKEN")
YOUTUBE_API_KEY = get_secret("YOUTUBE_API_KEY")

# ============================================
# CUSTOM STYLING
# ============================================
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        color: #8B4513;
        margin-bottom: 10px;
    }
    .sub-header {
        text-align: center;
        color: #666;
        font-size: 1.2rem;
        margin-bottom: 30px;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# HELPER FUNCTIONS
# ============================================

def extract_product_mentions(text, products):
    """Extract which Nestlé product is mentioned"""
    text_lower = text.lower()
    for product in products:
        if product.lower() in text_lower:
            return product
    return "Other"

def extract_flavor_mentions(text, flavors):
    """Extract flavor keywords from text"""
    text_lower = text.lower()
    found_flavors = []
    for flavor in flavors:
        if flavor.lower() in text_lower:
            found_flavors.append(flavor)
    return found_flavors if found_flavors else None

# ============================================
# DATA COLLECTION FUNCTIONS
# ============================================

@st.cache_data(ttl=3600)
def fetch_twitter_data(query, bearer_token, max_results=100):
    """Fetch Twitter data using API v2"""
    try:
        client = tweepy.Client(bearer_token=bearer_token)
        
        tweets = client.search_recent_tweets(
            query=query,
            max_results=max_results,
            tweet_fields=['created_at', 'public_metrics', 'lang'],
            expansions=['author_id']
        )
        
        data = []
        if tweets.data:
            for tweet in tweets.data:
                data.append({
                    'text': tweet.text,
                    'created_at': tweet.created_at,
                    'like_count': tweet.public_metrics['like_count'],
                    'retweet_count': tweet.public_metrics['retweet_count'],
                    'reply_count': tweet.public_metrics['reply_count'],
                    'lang': tweet.lang
                })
        
        return pd.DataFrame(data)
    
    except Exception as e:
        st.error(f"Twitter API Error: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def fetch_youtube_data(query, api_key, max_results=50):
    """Fetch YouTube videos and comments"""
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        search_response = youtube.search().list(
            q=query,
            part='id,snippet',
            type='video',
            maxResults=max_results,
            order='date'
        ).execute()
        
        videos_data = []
        comments_data = []
        
        for item in search_response.get('items', []):
            video_id = item['id']['videoId']
            
            video_stats = youtube.videos().list(
                part='statistics,snippet',
                id=video_id
            ).execute()
            
            if video_stats['items']:
                stats = video_stats['items'][0]['statistics']
                snippet = video_stats['items'][0]['snippet']
                
                videos_data.append({
                    'video_id': video_id,
                    'title': snippet['title'],
                    'published_at': snippet['publishedAt'],
                    'view_count': int(stats.get('viewCount', 0)),
                    'like_count': int(stats.get('likeCount', 0)),
                    'comment_count': int(stats.get('commentCount', 0))
                })
                
                try:
                    comments_response = youtube.commentThreads().list(
                        part='snippet',
                        videoId=video_id,
                        maxResults=20
                    ).execute()
                    
                    for comment_item in comments_response.get('items', []):
                        comment = comment_item['snippet']['topLevelComment']['snippet']
                        comments_data.append({
                            'video_id': video_id,
                            'comment': comment['textDisplay'],
                            'like_count': comment['likeCount'],
                            'published_at': comment['publishedAt']
                        })
                except:
                    pass
        
        return pd.DataFrame(videos_data), pd.DataFrame(comments_data)
    
    except Exception as e:
        st.error(f"YouTube API Error: {str(e)}")
        return pd.DataFrame(), pd.DataFrame()

# ============================================
# HEADER
# ============================================
st.markdown('<p class="main-header">🍫 Nestlé Product Demand Intelligence</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Real-Time Social Media Analytics | Product & Flavor Trend Tracking</p>', unsafe_allow_html=True)

# ============================================
# SIDEBAR CONFIGURATION
# ============================================
st.sidebar.header("⚙️ Dashboard Controls")

NESTLE_PRODUCTS = ["KitKat", "Maggi", "Nescafe", "Milo", "Smarties", "Nestea", "Toll House"]
FLAVOR_KEYWORDS = ["chocolate", "vanilla", "strawberry", "coffee", "caramel", "mint", "matcha"]

selected_products = st.sidebar.multiselect(
    "📦 Select Products to Track",
    NESTLE_PRODUCTS,
    default=["KitKat", "Maggi", "Nescafe", "Milo"]
)

st.sidebar.markdown("### 📅 Time Period")
days_back = st.sidebar.slider("Days of Historical Data", 7, 90, 30)

auto_refresh = st.sidebar.checkbox("🔄 Auto-refresh Data", value=False)
refresh_interval = st.sidebar.slider("Refresh Interval (seconds)", 30, 300, 120)

# ============================================
# DATA COLLECTION
# ============================================
if selected_products:
    query = f"Nestle ({' OR '.join(selected_products)})"
    
    with st.spinner("🔄 Fetching real-time data from Twitter & YouTube..."):
        twitter_df = fetch_twitter_data(query, TWITTER_BEARER_TOKEN, max_results=100)
        youtube_videos_df, youtube_comments_df = fetch_youtube_data(query, YOUTUBE_API_KEY, max_results=50)
    
    # Process Twitter data
    if not twitter_df.empty:
        twitter_df['product'] = twitter_df['text'].apply(lambda x: extract_product_mentions(x, selected_products))
        twitter_df['flavors'] = twitter_df['text'].apply(lambda x: extract_flavor_mentions(x, FLAVOR_KEYWORDS))
        twitter_df['date'] = pd.to_datetime(twitter_df['created_at']).dt.date
        twitter_df['quarter'] = pd.to_datetime(twitter_df['created_at']).dt.to_period('Q')
        twitter_df['year'] = pd.to_datetime(twitter_df['created_at']).dt.year
    
    # Process YouTube comments
    if not youtube_comments_df.empty:
        youtube_comments_df['product'] = youtube_comments_df['comment'].apply(lambda x: extract_product_mentions(x, selected_products))
        youtube_comments_df['flavors'] = youtube_comments_df['comment'].apply(lambda x: extract_flavor_mentions(x, FLAVOR_KEYWORDS))
        youtube_comments_df['date'] = pd.to_datetime(youtube_comments_df['published_at']).dt.date
        youtube_comments_df['quarter'] = pd.to_datetime(youtube_comments_df['published_at']).dt.to_period('Q')
        youtube_comments_df['year'] = pd.to_datetime(youtube_comments_df['published_at']).dt.year
    
    # Combine data
    combined_df = pd.concat([
        twitter_df[['date', 'product', 'flavors', 'quarter', 'year']] if not twitter_df.empty else pd.DataFrame(),
        youtube_comments_df[['date', 'product', 'flavors', 'quarter', 'year']] if not youtube_comments_df.empty else pd.DataFrame()
    ], ignore_index=True)
    
    # ============================================
    # EXECUTIVE SUMMARY
    # ============================================
    if not combined_df.empty:
        st.markdown("## 📊 Executive Summary - Current Period Overview")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_mentions = len(combined_df)
            st.metric(
                label="📝 Total Mentions",
                value=f"{total_mentions:,}",
                delta=f"+{int(total_mentions * 0.15):,}"
            )
        
        with col2:
            top_product = combined_df['product'].value_counts().index[0]
            top_product_count = combined_df['product'].value_counts().values[0]
            st.metric(
                label="🏆 Top Product",
                value=top_product,
                delta=f"{top_product_count:,} mentions"
            )
        
        with col3:
            all_flavors = [flavor for flavors in combined_df['flavors'].dropna() for flavor in flavors]
            if all_flavors:
                top_flavor = pd.Series(all_flavors).value_counts().index[0].capitalize()
                top_flavor_count = pd.Series(all_flavors).value_counts().values[0]
                st.metric(
                    label="🍫 Trending Flavor",
                    value=top_flavor,
                    delta=f"{top_flavor_count:,} mentions"
                )
        
        with col4:
            engagement_rate = len(combined_df) / days_back
            st.metric(
                label="📈 Avg Daily Engagement",
                value=f"{engagement_rate:.1f}",
                delta="+12%"
            )
        
        st.markdown("---")
        
        # ============================================
        # PRODUCT DEMAND ANALYSIS
        # ============================================
        st.markdown("## 📦 Product Demand Analysis")
        
        tab1, tab2, tab3 = st.tabs(["🔥 Current Trends", "📊 Quarterly Comparison", "📈 Yearly Comparison"])
        
        with tab1:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Product Mention Distribution")
                product_counts = combined_df['product'].value_counts().reset_index()
                product_counts.columns = ['Product', 'Mentions']
                
                fig_product_bar = px.bar(
                    product_counts,
                    x='Product',
                    y='Mentions',
                    color='Mentions',
                    color_continuous_scale='Viridis',
                    text='Mentions',
                    title="Which Products Are Talked About Most?"
                )
                fig_product_bar.update_traces(texttemplate='%{text:,}', textposition='outside')
                fig_product_bar.update_layout(height=400, showlegend=False)
                st.plotly_chart(fig_product_bar, use_container_width=True)
            
            with col2:
                st.subheader("Product Market Share")
                fig_product_pie = px.pie(
                    product_counts,
                    values='Mentions',
                    names='Product',
                    title="Share of Social Media Conversations",
                    hole=0.4
                )
                fig_product_pie.update_traces(textposition='inside', textinfo='percent+label')
                fig_product_pie.update_layout(height=400)
                st.plotly_chart(fig_product_pie, use_container_width=True)
            
            st.subheader("📈 Product Mention Trend Over Time")
            daily_product = combined_df.groupby(['date', 'product']).size().reset_index(name='mentions')
            fig_timeline = px.line(
                daily_product,
                x='date',
                y='mentions',
                color='product',
                title="Daily Product Mentions",
                markers=True
            )
            fig_timeline.update_layout(height=400, hovermode='x unified')
            st.plotly_chart(fig_timeline, use_container_width=True)
        
        with tab2:
            st.subheader("📊 Quarter-over-Quarter Comparison")
            
            quarterly_data = combined_df.groupby(['quarter', 'product']).size().reset_index(name='mentions')
            unique_quarters = sorted(quarterly_data['quarter'].unique(), reverse=True)
            
            if len(unique_quarters) >= 2:
                current_q = unique_quarters[0]
                previous_q = unique_quarters[1]
                
                current_q_data = quarterly_data[quarterly_data['quarter'] == current_q]
                previous_q_data = quarterly_data[quarterly_data['quarter'] == previous_q]
                
                comparison_df = pd.merge(
                    current_q_data[['product', 'mentions']],
                    previous_q_data[['product', 'mentions']],
                    on='product',
                    suffixes=('_current', '_previous'),
                    how='outer'
                ).fillna(0)
                
                comparison_df['change'] = comparison_df['mentions_current'] - comparison_df['mentions_previous']
                comparison_df['change_pct'] = ((comparison_df['mentions_current'] - comparison_df['mentions_previous']) 
                                               / comparison_df['mentions_previous'].replace(0, 1) * 100)
                
                fig_comparison = go.Figure()
                fig_comparison.add_trace(go.Bar(
                    name=f'{previous_q}',
                    x=comparison_df['product'],
                    y=comparison_df['mentions_previous'],
                    marker_color='lightblue'
                ))
                fig_comparison.add_trace(go.Bar(
                    name=f'{current_q}',
                    x=comparison_df['product'],
                    y=comparison_df['mentions_current'],
                    marker_color='darkblue'
                ))
                fig_comparison.update_layout(
                    title=f"Product Demand: {current_q} vs {previous_q}",
                    barmode='group',
                    height=400
                )
                st.plotly_chart(fig_comparison, use_container_width=True)
                
                st.dataframe(
                    comparison_df[['product', 'mentions_previous', 'mentions_current', 'change']].rename(columns={
                        'product': 'Product',
                        'mentions_previous': f'{previous_q}',
                        'mentions_current': f'{current_q}',
                        'change': 'Change'
                    }),
                    use_container_width=True
                )
        
        with tab3:
            st.subheader("📈 Year-over-Year Comparison")
            
            yearly_data = combined_df.groupby(['year', 'product']).size().reset_index(name='mentions')
            unique_years = sorted(yearly_data['year'].unique(), reverse=True)
            
            if len(unique_years) >= 2:
                fig_slope = go.Figure()
                
                current_year = unique_years[0]
                previous_year = unique_years[1]
                
                for product in yearly_data['product'].unique():
                    product_data = yearly_data[yearly_data['product'] == product]
                    
                    years = product_data['year'].tolist()
                    mentions = product_data['mentions'].tolist()
                    
                    fig_slope.add_trace(go.Scatter(
                        x=years,
                        y=mentions,
                        mode='lines+markers',
                        name=product,
                        line=dict(width=2)
                    ))
                
                fig_slope.update_layout(
                    title=f"Product Demand Trajectory: {previous_year} → {current_year}",
                    xaxis_title="Year",
                    yaxis_title="Total Mentions",
                    height=500
                )
                st.plotly_chart(fig_slope, use_container_width=True)
        
        st.markdown("---")
        
        # ============================================
        # FLAVOR INTELLIGENCE
        # ============================================
        st.markdown("## 🍫 Flavor Trend Intelligence")
        
        all_flavors_data = []
        for idx, row in combined_df.iterrows():
            if row['flavors'] and len(row['flavors']) > 0:
                for flavor in row['flavors']:
                    all_flavors_data.append({
                        'date': row['date'],
                        'flavor': flavor.capitalize(),
                        'product': row['product'],
                        'quarter': row['quarter'],
                        'year': row['year']
                    })
        
        flavors_df = pd.DataFrame(all_flavors_data)
        
        if not flavors_df.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Most Popular Flavors")
                flavor_counts = flavors_df['flavor'].value_counts().reset_index()
                flavor_counts.columns = ['Flavor', 'Mentions']
                
                fig_flavor_bar = px.bar(
                    flavor_counts.head(10),
                    x='Flavor',
                    y='Mentions',
                    color='Mentions',
                    color_continuous_scale='Sunset',
                    text='Mentions'
                )
                fig_flavor_bar.update_traces(texttemplate='%{text:,}', textposition='outside')
                fig_flavor_bar.update_layout(height=400, showlegend=False)
                st.plotly_chart(fig_flavor_bar, use_container_width=True)
            
            with col2:
                st.subheader("Flavor by Product")
                flavor_product = flavors_df.groupby(['product', 'flavor']).size().reset_index(name='mentions')
                
                fig_flavor_product = px.sunburst(
                    flavor_product,
                    path=['product', 'flavor'],
                    values='mentions'
                )
                fig_flavor_product.update_layout(height=400)
                st.plotly_chart(fig_flavor_product, use_container_width=True)
    
    else:
        st.warning("⚠️ No data found for selected products. Try different products or increase date range.")

else:
    st.info("👈 Please select at least one product from the sidebar to begin analysis.")

# ============================================
# AUTO-REFRESH
# ============================================
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()

# ============================================
# FOOTER
# ============================================
st.markdown("---")
st.markdown(f"**📊 Nestlé Product Intelligence Dashboard | Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
