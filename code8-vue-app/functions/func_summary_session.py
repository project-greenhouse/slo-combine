"""
Alternative implementation using session state for summary storage
This is a fallback when Supabase is not available or not configured
"""

import streamlit as st
from datetime import datetime


def init_session_state():
    """Initialize session state for summary storage"""
    if 'athlete_summaries' not in st.session_state:
        st.session_state.athlete_summaries = {}

# Save athlete summary to session state
def save_athlete_summary_session(athlete_name: str, summary_html: str) -> bool:
    """
    Save athlete summary to session state
    
    Args:
        athlete_name: Name of the athlete
        summary_html: HTML content of the summary
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        init_session_state()
        st.session_state.athlete_summaries[athlete_name] = {
            'summary_html': summary_html,
            'updated_at': datetime.now().isoformat()
        }
        return True
    except Exception as e:
        st.error(f"Failed to save summary: {e}")
        return False

# Get athlete summary from session state
def get_athlete_summary_session(athlete_name: str) -> str:
    """
    Get athlete summary from session state
    
    Args:
        athlete_name: Name of the athlete
    
    Returns:
        str: HTML content of the summary, or empty string if not found
    """
    if not athlete_name:
        return ""
    
    try:
        init_session_state()
        if athlete_name in st.session_state.athlete_summaries:
            return st.session_state.athlete_summaries[athlete_name]['summary_html']
        else:
            return ""
    except Exception as e:
        st.error(f"Failed to load summary: {e}")
        return ""

# Delete athlete summary from session state
def delete_athlete_summary_session(athlete_name: str) -> bool:
    """
    Delete athlete summary from session state
    
    Args:
        athlete_name: Name of the athlete
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        init_session_state()
        if athlete_name in st.session_state.athlete_summaries:
            del st.session_state.athlete_summaries[athlete_name]
        return True
    except Exception as e:
        st.error(f"Failed to delete summary: {e}")
        return False
