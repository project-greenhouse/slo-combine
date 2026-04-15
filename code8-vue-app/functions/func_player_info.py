import streamlit as st
from functions.utility import GetGsheet


## Athlete Sign Up CSV Data
@st.cache_data(ttl=3600)  # Cache for 1 hour
def AthleteSignUpData():
    """
    Fetches Athlete Sign Up data from Google Sheets.
    Returns:
        pd.DataFrame: DataFrame containing Athlete Sign Up data.
    """
    return GetGsheet(sheet_name="info")
