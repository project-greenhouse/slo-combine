import streamlit as st
import functions.data as db
import pandas as pd
from functions.func_valor import ValorSessions

token = db.valorToken
url = st.secrets["VALOR_URL"]

with st.spinner("Loading Valor Data..."):
    try:
        valor_df = ValorSessions(token=token, url=url)
        if valor_df.empty:
            st.warning("No data available from Valor API.")
        else:
            st.dataframe(valor_df)
    except Exception as e:
        st.error(f"Error fetching Valor data: {e}")

# --- PAGE SETUP ---
st.subheader("Valor Data",anchor=False, divider="orange")
st.dataframe(valor_df)
