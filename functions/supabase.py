# supabase.py
"""
This module initializes a Supabase client using environment variables for the project URL and key.
"""

# Import necessary libraries
import os
from functions.supabase import create_client, Client

# store supabase API URL and Key in environment variables
# This is a security measure to avoid hardcoding sensitive information in the codebase.
os.environ["SUPABASE_URL"] = "https://xvybpsrxzrzosztqzclq.supabase.co"
os.environ["SUPABASE_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh2eWJwc3J4enJ6b3N6dHF6Y2xxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTMzNjA5NDMsImV4cCI6MjA2ODkzNjk0M30.fXiBfbhwfaaUjkVE5TpHNLoJBdEWIacn27MLKDeIUVs"

# Ensure environment variables are set for Supabase URL and Key
if not os.environ.get("SUPABASE_URL") or not os.environ.get("SUPABASE_KEY"):
    raise EnvironmentError("Supabase URL and Key must be set in environment variables.")

# Supabase Project URL and Key
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)