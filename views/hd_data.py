import streamlit as st
import pandas as pd
from functions.data import AthleteCMJ, AthleteMR

# --- Retrieve selected athlete from session state ---
selected_name = st.session_state.get("selected_name", None)

with st.spinner("Loading CMJ and MR data..."):
    cmj = AthleteCMJ(athlete=selected_name)
    mr = AthleteMR(athlete=selected_name)

st.subheader("Hawking Dynamic Data", anchor=False, divider="red")

st.subheader("CMJ Data", anchor=False, divider="red")
st.dataframe(cmj, hide_index=True)
    
st.subheader("MR Data", anchor=False, divider="red")
st.dataframe(mr, hide_index=True)
