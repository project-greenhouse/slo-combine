import streamlit as st
import pandas as pd
import functions.data as db
from functions.viz import plot_power_ranks
# --- Retrieve selected athlete from session state ---
selected_name = st.session_state.get("selected_name", None)

forcePlateData = db.AthleteCMJ(athlete=selected_name)
VerticalData = db.verticalJump(player_name=selected_name)
BroadJumpData = db.broadJump(player_name=selected_name)

def verticalJumpSection():
    """
    Displays the vertical jump data section with metrics and a dataframe.
    """
    if forcePlateData.empty:
        st.warning("No vertical jump data available for this athlete.")
        return

    #----- Row 1: Power Ranks -----
    fdData = pd.DataFrame({
        "Comp": ['SLO Combine', 'SLO Combine', 'Elite', 'Elite'],
        "Metric": ['Reactive Strength','Relative Power', 'Reactive Strength', 'Relative Power'],
        "Value": [forcePlateData['mRSI SLO Rank'].max().round(0), forcePlateData['Peak Rel Power SLO Rank'].max().round(0), forcePlateData['mRSI Elite Rank'].max().round(0), forcePlateData['Peak Rel Power Elite Rank'].max().round(0)]
    })

    plot_power_ranks(fdData)

    #----- Row 2: Jump Range
    vertCol, broadCol = st.columns([1, 1], gap="small", border=True)
    with vertCol:
        st.markdown(
        # Underlined and centered header
        "<h6 style='text-align: center; text-decoration: underline;'>Standing Vert</h6>" ,
        unsafe_allow_html=True
        )
        vCol1, vCol2, vCol3 = st.columns([1, 1, 1], gap="small", border=False)
        with vCol1:
            # Display the vertical jump height
            st.metric("Vertical Jump (in)", VerticalData['VerticalJump'].max(), delta=None)
        with vCol2:
            # Display the horizontal jump distance
            st.metric("Combine % Rank", VerticalData['perc_vert'].max(), delta=None)
        with vCol3:
            # Display the broad jump distance
            st.metric("Elite % Rank", VerticalData['ext_perc_vert'].max(), delta=None)

    with broadCol:
        st.markdown(
        # Underlined and centered header
        "<h6 style='text-align: center; text-decoration: underline;'>Broad Jump</h6>" ,
        unsafe_allow_html=True
        )
        bCol1, bCol2, bCol3= st.columns([1, 1, 1], gap="small", border=False)
        with bCol1:
            st.metric("Broad Jump (in)", BroadJumpData['BestBroadJump'].max(), delta=None)
        with bCol2:
            st.metric("Combine % Rank", BroadJumpData['perc_broad'].max(), delta=None)
        with bCol3:
            st.metric("Elite % Rank", BroadJumpData['ext_perc_broad'].max(), delta=None)


