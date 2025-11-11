#!/usr/bin/env python3
"""
Test script to verify freshness information is properly returned by the API.
"""
import requests
import json
from datetime import datetime

def test_api_freshness():
    """Test that API endpoints return freshness information."""
    
    # Test news endpoint
    try:
        news_response = requests.get("http://localhost:8050/api/news/feed")
        if news_response.status_code == 200:
            news_data = news_response.json()
            print("✅ News API call successful")
            
            # Check if freshness info is present
            if 'data' in news_data and 'freshness' in news_data['data']:
                print(f"✅ News: Freshness info present - {news_data['data']['freshness']}")
            elif 'freshness' in news_data:
                print(f"✅ News: Freshness info present at root - {news_data['freshness']}")
            else:
                print("⚠️  News: Freshness info missing")
                
            # Check last_update if available
            if 'data' in news_data and 'last_update' in news_data['data']:
                print(f"✅ News: Last update info present - {news_data['data']['last_update']}")
            elif 'last_update' in news_data:
                print(f"✅ News: Last update info present at root - {news_data['last_update']}")
        else:
            print(f"❌ News API call failed with status {news_response.status_code}")
    except Exception as e:
        print(f"❌ Error testing news API: {str(e)}")
    
    # Test forecasts endpoint
    try:
        forecasts_response = requests.get("http://localhost:8050/api/forecasts")
        if forecasts_response.status_code == 200:
            forecasts_data = forecasts_response.json()
            print("✅ Forecasts API call successful")
            
            # Check if freshness info is present
            if 'data' in forecasts_data and 'freshness' in forecasts_data['data']:
                print(f"✅ Forecasts: Freshness info present - {forecasts_data['data']['freshness']}")
            elif 'freshness' in forecasts_data:
                print(f"✅ Forecasts: Freshness info present at root - {forecasts_data['freshness']}")
            else:
                print("⚠️  Forecasts: Freshness info missing")
                
            # Check last_update if available
            if 'data' in forecasts_data and 'last_update' in forecasts_data['data']:
                print(f"✅ Forecasts: Last update info present - {forecasts_data['data']['last_update']}")
            elif 'last_update' in forecasts_data:
                print(f"✅ Forecasts: Last update info present at root - {forecasts_data['last_update']}")
        else:
            print(f"❌ Forecasts API call failed with status {forecasts_response.status_code}")
    except Exception as e:
        print(f"❌ Error testing forecasts API: {str(e)}")

if __name__ == "__main__":
    print("Testing freshness implementation...")
    test_api_freshness()