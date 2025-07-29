import streamlit as st
import pandas as pd
from functions.data import verticalJump
# --- Retrieve selected athlete from session state ---
selected_name = st.session_state.get("selected_name", None)

with st.spinner("Loading Vertical Jump data..."):
    # Fetch vertical jump data for the selected athlete
    if selected_name:
        df = verticalJump(player_name=selected_name)
    else:
        st.error("No athlete selected. Please select an athlete from the sidebar.")

st.subheader("Vertical Jump Data", anchor=False, divider="red")

st.dataframe(df)
