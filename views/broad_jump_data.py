import streamlit as st
import pandas as pd
from functions.data import broadJump
# --- Retrieve selected athlete from session state ---
selected_name = st.session_state.get("selected_name", None)

with st.spinner("Loading Broad Jump data..."):
    # Fetch broad jump data for the selected athlete
    if selected_name:
        df = broadJump(player_name=selected_name)
    else:
        st.error("No athlete selected. Please select an athlete from the sidebar.")

st.subheader("Broad Jump Data", anchor=False, divider="red")
st.dataframe(df)