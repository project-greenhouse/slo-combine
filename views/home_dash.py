import streamlit as st
import functions.data as db

# --- Retrieve selected athlete from session state ---
selected_name = st.session_state.get("selected_name", None)

# Report Header
headerLogo, headerTitle = st.columns((1, 3))
headerLogo.image("assets/SLO CC ONLY.png", use_container_width=True)
headerTitle.markdown(
    "<h1 style='text-align: center;'>Code 8 San Luis Obispo County Combine 2025</h1>",
    unsafe_allow_html=True
)

# --- Home Page Content ---

# Athlete Info Section
st.subheader(
    "Athlete Information",
    anchor=False,
    help="This section provides basic information about the athlete including name, age, school, and more.",
    divider="orange"
)

# Row 1: Name and Age
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.write(f"**Name:** {selected_name if selected_name else 'N/A'}")
with col2:
    st.write("**Age:** 17")
with col3:
    st.write("**Gender:** Male")

# Row 2: School and Height
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.write("**School - Grad Year:** San Luis Obispo High - 2026")
with col2:
    st.write("**Height:** 6'2\"")
with col3:
    st.write("**Limb Dominance:** Right")

# Row 3: Sports and Position
col1, col2 = st.columns([1, 1])
with col1:
    st.write("**Sports:** Basketball, Football")
with col2:
    st.write("**Position:** Point Guard, Quarterback")

# Movement Data Section
st.subheader(
    "Movement Data",
    anchor=False,
    help="This section includes data from various movement tests such as vertical jump, broad jump, and more.",
    divider="orange"
)
st.dataframe(db.dfValorAthletes)

# Speed Data Section
st.subheader(
    "Speed Data",
    anchor=False,
    help="This section includes data from various speed tests such as 40-yard dash, shuttle run, and more.",
    divider="orange"
)

if selected_name:
    st.dataframe(db.swiftSprint(player_name=selected_name))
    st.divider()
    st.dataframe(db.proAgility(player_name=selected_name))
else:
    st.info("Select an athlete from the sidebar to view test results.")

# Power Data Section
st.subheader(
    "Power Data",
    anchor=False,
    help="This section includes data from various power tests such as vertical jump, broad jump, and more.",
    divider="orange"
)

#st.dataframe(db.HawkinCMJ(athlete=selected_name))
st.subheader("CMJ Data", anchor=False)
st.dataframe(db.AthleteCMJ(athlete=selected_name))

st.subheader("MR Data", anchor=False)
st.dataframe(db.AthleteMR(athlete=selected_name))

st.divider()
st.dataframe(db.rosterCheck())