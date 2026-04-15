"""
Functions for handling athlete summary data with Supabase integration
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from functions.db_client import GetSupaTable, InsertSupaTable, UpdateSupaTable, DeleteSupaTable
from functions.func_summary_session import (
    save_athlete_summary_session, 
    get_athlete_summary_session, 
    delete_athlete_summary_session
)

# Try to import supabase, fall back to session state if not available
try:
    SUPABASE_AVAILABLE = True
except Exception:
    SUPABASE_AVAILABLE = False
    st.warning("Supabase not available. Using session state for summary storage. Data will be lost when the session ends.")


def create_summary_table():
    """Create the athlete_summaries table if it doesn't exist"""
    if not SUPABASE_AVAILABLE:
        return True
        
    try:
        # Check if table exists by trying to select from it
        result = GetSupaTable('athlete_summaries') 
        
    except Exception:
        # Table doesn't exist, create it
        try:
            # Note: In a real app, you'd want to create this table through Supabase dashboard
            # This is a placeholder - you'll need to create the table manually
            st.error("Please create the 'athlete_summaries' table in Supabase with columns: id, athlete_name, summary_html, created_at, updated_at")
            return False
        except Exception as e:
            st.error(f"Failed to create summary table: {e}")
            return False
    return True


def save_athlete_summary(athlete_name: str, summary_html: str) -> bool:
    """
    Save or update athlete summary to Supabase or session state
    
    Args:
        athlete_name: Name of the athlete
        summary_html: HTML content of the summary
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not SUPABASE_AVAILABLE:
        return save_athlete_summary_session(athlete_name, summary_html)
    
    try:
        # Check if summary already exists for this athlete
        existing = GetSupaTable('athlete_summaries', eq=('athlete_name', athlete_name))
        current_time = datetime.now().isoformat()
        
        if existing:  # Check if data exists
            # Update existing summary
            result = UpdateSupaTable('athlete_summaries', {
                'summary_html': summary_html,
                'updated_at': current_time
            }, eq=('athlete_name', athlete_name))
        else:
            # Insert new summary
            result = InsertSupaTable('athlete_summaries', {
                'athlete_name': athlete_name,
                'summary_html': summary_html,
                'created_at': current_time,
                'updated_at': current_time
            })
        
        return len(result) > 0 if result else False
    except Exception as e:
        st.error(f"Failed to save summary: {e}")
        # Fallback to session state
        return save_athlete_summary_session(athlete_name, summary_html)


def get_athlete_summary(athlete_name: str) -> str:
    """
    Get athlete summary from Supabase or session state
    
    Args:
        athlete_name: Name of the athlete
    
    Returns:
        str: HTML content of the summary, or empty string if not found
    """
    if not athlete_name:
        return ""
    
    if not SUPABASE_AVAILABLE:
        return get_athlete_summary_session(athlete_name)
    
    try:
        result = GetSupaTable('athlete_summaries', select="summary_html", eq=('athlete_name', athlete_name))
        
        if result and len(result) > 0:
            return result[0]['summary_html']
        else:
            return ""
    except Exception as e:
        st.error(f"Failed to load summary from Supabase: {e}")
        # Fallback to session state
        return get_athlete_summary_session(athlete_name)


def delete_athlete_summary(athlete_name: str) -> bool:
    """
    Delete athlete summary from Supabase or session state
    
    Args:
        athlete_name: Name of the athlete
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not SUPABASE_AVAILABLE:
        return delete_athlete_summary_session(athlete_name)
    
    try:
        result = DeleteSupaTable('athlete_summaries', eq=('athlete_name', athlete_name))
        return len(result) > 0 if result else True  # Return True even if no rows deleted (already gone)
    except Exception as e:
        st.error(f"Failed to delete summary from Supabase: {e}")
        # Fallback to session state
        return delete_athlete_summary_session(athlete_name)
