import streamlit as st
from functions.utility import GetGsheet


## Pro Agility CSV Data
@st.cache_data(ttl=3600)  # Cache for 1 hour
def ProAgilityData():
    """
    Fetches Pro Agility data from Google Sheets.
    Returns:
        pd.DataFrame: DataFrame containing Pro Agility data.
    """
    return GetGsheet(sheet_name="pro-agility")

#--------------------------------------------------

## Sprint CSV Data
@st.cache_data(ttl=3600)  # Cache for 1 hour
def Sprint40Data():
    """
    Fetches Sprint data from Google Sheets.
    Returns:
        pd.DataFrame: DataFrame containing Sprint data.
    """
    return GetGsheet(sheet_name="sprint40")

#--------------------------------------------------

## Vertical Jump -----
@st.cache_data(ttl=3600)  # Cache for 1 hour
def VertJumpData():
    """
    Fetches Vertical Jump data from Google Sheets.
    Returns:
        pd.DataFrame: DataFrame containing Vertical Jump data.
    """
    return GetGsheet(sheet_name="standing-vert")

#--------------------------------------------------

## Broad Jump -----
@st.cache_data(ttl=3600)  # Cache for 1 hour
def BroadJumpData():
    """
    Fetches Broad Jump data from Google Sheets.
    Returns:
        pd.DataFrame: DataFrame containing Broad Jump data.
    """
    return GetGsheet(sheet_name="broad-jump")
