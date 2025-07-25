import streamlit as st

# --- SLO Combine App ---
# This is the main file for the SLO Combine application.

# --- PAGE SETUP ---
#st.title("SLO Combine App")

#--- Shared Assets ---
st.logo("assets/code8perf_logo.png")

# --- SIDEBAR FOOTER ---
st.sidebar.text("Powered by Greenhouse Performance")

# Home Page
home_page = st.Page(
    page="views/home_dash.py",
    title="Report Home",
    icon=":material/widgets:",
    default=True
)

# Force Plate Data
hd_page = st.Page(
    page="views/hd_data.py",
    title="Force Plate Data",
    icon=":material/cruelty_free:",
)

# Swift Data
swift_page = st.Page(
    page="views/swift_data.py",
    title="Swift Data",
    icon=":material/sprint:",
)
# Valor Data
valor_page = st.Page(
    page="views/valor_data.py",
    title="Valor Data",
    icon=":material/sports_gymnastics:",
)

# Vertical Jump Data
vert_jump_page = st.Page(
    page="views/vert_jump_data.py",
    title="Vertical Jump Data",
    icon=":material/sports_handball:",
)

# Broad Jump Data
broad_jump_page = st.Page(
    page="views/broad_jump_data.py",
    title="Broad Jump Data",
    icon=":material/linear_scale:",
)

# --- NAVIGATION SETUP w/o SECTIONS ---
#pg = st.navigation(pages=[home_page, hd_page, swift_page, valor_page, vert_jump_page, broad_jump_page])

# --- NAVIGATION SETUP w/ SECTIONS ---
pg = st.navigation(
    {
        "Report":[home_page], 
        "Data": [hd_page, swift_page, valor_page, vert_jump_page, broad_jump_page],
    }
)

# --- RUN NAVIGATION ---
pg.run()
