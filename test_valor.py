#!/usr/bin/env python3
"""
Test script for Valor API debugging
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from functions.func_valor import get_jwt_token, ValorSessions
import streamlit as st

# Mock the secrets for testing - you'll need to set these
# st.secrets = {
#     "VALOR_URL": "your_valor_url",
#     "VALOR_TOKEN_URL": "your_token_url",
#     "VALOR_USER": "your_username",
#     "VALOR_PASSWORD": "your_password",
#     "VALOR_CLIENT_ID": "your_client_id"
# }

def test_valor_auth():
    print("Testing Valor Authentication...")
    token = get_jwt_token()
    
    if token:
        print(f"\n✅ Token received successfully")
        print(f"Token type: {type(token)}")
        print(f"Token length: {len(token)}")
        return token
    else:
        print("\n❌ Failed to get token")
        return None

def test_valor_sessions(token, url):
    print("\nTesting Valor Sessions API...")
    try:
        df = ValorSessions(token=token, url=url)
        print(f"✅ Sessions data retrieved: {len(df)} rows")
        return df
    except Exception as e:
        print(f"❌ Error retrieving sessions: {e}")
        return None

if __name__ == "__main__":
    # Test authentication
    token = test_valor_auth()
    
    if token:
        # Test sessions API
        # You'll need to provide the correct URL
        url = st.secrets.get("VALOR_URL", "") + "sessions"  # Adjust endpoint as needed
        df = test_valor_sessions(token, url)
        
        if df is not None and not df.empty:
            print(f"\n📊 Sample data:")
            print(df.head())
        else:
            print("\n⚠️ No data returned or error occurred")
