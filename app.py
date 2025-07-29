import streamlit as st
import streamlit.components.v1 as components
import functions.data as db
import pandas as pd

# --- PAGE SETUP ---
st.set_page_config(
    page_title="SLO Combine App",
    layout="wide",  # ✅ Default to wide mode
)

# --- Shared Assets ---
st.logo("assets/code8perf_logo.png")

# --- SIDEBAR: Athlete Selector ---
roster_df = db.clean_roster()

if roster_df is not None and isinstance(roster_df, pd.DataFrame) and "Name" in roster_df.columns:
    selected_name = st.sidebar.selectbox("Select Athlete", options=roster_df["Name"].tolist())
    st.session_state["selected_name"] = selected_name
else:
    st.sidebar.warning("No valid athlete roster available.")

# --- SIDEBAR FOOTER ---

st.sidebar.text(
    "Powered by Greenhouse Performance"
)

# --- PAGE DEFINITIONS ---
home_page = st.Page(
    page="views/home_dash.py",
    title="Report Home",
    icon=":material/widgets:",
    default=True
)

hd_page = st.Page(
    page="views/hd_data.py",
    title="Force Plate Data",
    icon=":material/cruelty_free:",
)

swift_page = st.Page(
    page="views/swift_data.py",
    title="Swift Data",
    icon=":material/sprint:",
)

valor_page = st.Page(
    page="views/valor_data.py",
    title="Valor Data",
    icon=":material/sports_gymnastics:",
)

vert_jump_page = st.Page(
    page="views/vert_jump_data.py",
    title="Vertical Jump Data",
    icon=":material/sports_handball:",
)

broad_jump_page = st.Page(
    page="views/broad_jump_data.py",
    title="Broad Jump Data",
    icon=":material/linear_scale:",
)

# --- NAVIGATION ---
pg = st.navigation(
    {
        "Report": [home_page], 
        "Data": [hd_page, swift_page, valor_page, vert_jump_page, broad_jump_page],
    }
)

# --- RUN PAGE ---
pg.run()
