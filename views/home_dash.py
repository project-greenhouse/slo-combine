import streamlit as st

# Report Header
headerLogo, headerTitle = st.columns((1,3))
headerLogo.image("assets/code8perf_logo.png", use_container_width=True)
headerTitle.markdown("<h1 style='text-align: center;'>SLO County Combine 2025</h1>", unsafe_allow_html=True)

# --- Home Page Content ---

# Athlete Info Section
st.subheader("Athlete Information")

# Row 1: Name and Age
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.write("**Name:** John Smith")
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

# Visual separator
st.divider()

# Movement Data Section

# Speed Data Section

# Power Data Section