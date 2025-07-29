import streamlit as st
import pandas as pd
import altair as alt
from functions.data import dfSprint, dfProAgility

# --- Retrieve selected athlete from session state ---
selected_name = st.session_state.get("selected_name", None)

# Sprint Data Section
def SprintTable(data=dfSprint, selected_name=selected_name):
    """
    Creates a DataFrame for sprint data filtered by the selected athlete.
    Args:
        data (DataFrame): The sprint data DataFrame.
        selected_name (str): The name of the athlete to filter by.
    Returns:
        DataFrame: Filtered sprint data.
    """
    if selected_name:
        data = data[data["Name"] == selected_name].copy()
    
    return pd.DataFrame({
        "Name": data["Name"],
        "Activity Id": data["ActivityIdentifier"],
        "Timestamp": data["ActivityTimestamp"],
        "Sequence": data["Sequence"],
        "Total Time (s)": data["Total"],
        "Split (s)": data["Split"],
        "Distance (yd)": data["Distance"],
        "Velocity (yd/s)": data["Velocity"]
    }   )

# Pro Agility Data Section
def ProAgilityTable(data=dfProAgility, selected_name=selected_name):
    """
    Creates a DataFrame for Pro Agility data filtered by the selected athlete.
    Args:
        data (DataFrame): The Pro Agility data DataFrame.
        selected_name (str): The name of the athlete to filter by.
    Returns:
        DataFrame: Filtered Pro Agility data.
    """
    if selected_name:
        data = data[data["Name"] == selected_name].copy()
    
    return pd.DataFrame({
        "Name": data["Name"],
        "Activity Id": data["ActivityIdentifier"],
        "Timestamp": data["ActivityTimestamp"],
        "Sequence": data["Sequence"],
        "Total Time (s)": data["Total"],
        "Split (s)": data["Split"],
        "Distance (yd)": data["Distance"],
        "Velocity (yd/s)": data["Velocity"]
    })

with st.spinner("Loading Swift data..."):
    sprint_data = SprintTable()
    agility_data = ProAgilityTable()

st.subheader("40-Yard Dash Data", anchor=False, divider="red")
st.dataframe(sprint_data)

st.subheader("5-10-5 Pro Agility Shuttle Data", anchor=False, divider="red")
st.dataframe(agility_data)