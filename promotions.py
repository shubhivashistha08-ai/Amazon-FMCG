# Functions for handling promotion data from RapidAPI

import requests
import streamlit as st

def get_price_history(asin, api_key, api_host="amazon-price1.p.rapidapi.com"):
    """Fetch price history from RapidAPI"""
    if not api_key:
        return None
    
    url = f"https://{api_host}/gethistory"
    querystring = {"asin": asin, "country": "US"}
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": api_host
    }
    
    try:
        response = requests.get(url, headers=headers, params=querystring, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Failed to fetch data: {str(e)}")
        return None


def detect_promotions(price_history):
    """Auto-detect promotions from price history"""
    if not price_history:
        return []
    
    promotions = []
    prices = price_history.get('price_history', [])
    
    for i in range(1, len(prices)):
        prev_price = float(prices[i-1]['price'])
        curr_price = float(prices[i]['price'])
        
        if curr_price < prev_price:
            discount_percent = ((prev_price - curr_price) / prev_price) * 100
            
            if discount_percent > 30:
                tactic = "FLASH_SALE"
            elif discount_percent > 15:
                tactic = "DISCOUNT"
            else:
                tactic = "MINOR_DISCOUNT"
            
            promotions.append({
                'date': prices[i]['date'],
                'price_before': prev_price,
                'price_during': curr_price,
                'discount_%': round(discount_percent, 1),
                'tactic': tactic
            })
    
    return promotions


def get_promotion_statistics(promotions_df):
    """Calculate promotion statistics"""
    if promotions_df.empty:
        return None
    
    stats = {
        'total': len(promotions_df),
        'avg_discount': promotions_df['discount_%'].mean(),
        'max_discount': promotions_df['discount_%'].max(),
        'min_discount': promotions_df['discount_%'].min()
    }
    return stats
