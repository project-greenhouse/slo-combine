import streamlit as st
import pandas as pd
import functions.data as db
from functions.data import CombinePercentiles as CombinePrcnt
from functions.viz import plot_reactive_performance as speed_plot
from functions.data import dfSprint, dfProAgility

# --- Retrieve selected athlete from session state ---
selected_name = st.session_state.get("selected_name", None)

def speedSection():
    # Combine Percentile Data
    combineData = pd.DataFrame(db.CombinePercentiles)

    if selected_name:
        # 40 Yard Dash Data 
        sprintData = db.swiftSprint(data= db.dfSprint,player_name=selected_name)
        agilityData = db.proAgility(data= db.dfProAgility, player_name=selected_name)
        # Strip plot for 40 Yard Dash
        if not sprintData.empty and 'total_time_40yd' in sprintData.columns:
            average_40yd = round(sprintData['total_time_40yd'].mean(), 2)
        else:
            average_40yd = None

        # Strip plot for Pro Agility
        if not agilityData.empty and 'total_time' in agilityData.columns:
            average_pro_agility = round(agilityData['total_time'].mean(), 2)
        else:
            average_pro_agility = None
        
        # Sprint Strip Plot
        #strip_plot(title= "40 Yard Dash", value = average_40yd, table = combineData, metric= "Sprint40", metric_label = "Average Time (s)")
        
        # Only show the plot if we have data for both tests
        if not sprintData.empty and not agilityData.empty:
            fig = speed_plot(sprintData, agilityData)
            st.plotly_chart(fig, use_container_width=True)
            
            # Streamlit horizontal bar chart for sprint and agility data
            # Prepare data for horizontal bar chart similar to the plotly chart
            sprint_trial = sprintData[sprintData['total_time_40yd'] == sprintData['total_time_40yd'].min()]
            agility_trial = agilityData[agilityData['total_time'] == agilityData['total_time'].min()]
            
            # Create DataFrame for the horizontal bar chart with split times
            chart_data = pd.DataFrame({
                'Test': ['40 Yard Sprint', '40 Yard Sprint', 'Pro Agility', 'Pro Agility', 'Pro Agility', 'Pro Agility'],
                'Split': ['1', '2', '1', '2', '3', '4'],
                "Time": [float(sprint_trial.get("split_time_10yd", 0)), float(sprint_trial.get("split_time_40yd", 0)),
                        float(agility_trial.get("split_time_5yd", 0)), float(agility_trial.get("split_time_10yd", 0)),
                        float(agility_trial.get("split_time_15yd", 0)), float(agility_trial.get("split_time_20yd", 0))]
            })

        # Row 3: Sports and Position
        R1L, R1R = st.columns([1, 1], gap="small", border=True)
        # Sprint Table
        with R1L: 
            if not sprintData.empty and 'perc_40yd' in sprintData.columns:
                st.markdown(
                    # Underlined and centered header
                    "<h6 style='text-align: center; text-decoration: underline;'>40 Yard Dash</h6>" ,
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    "<h6 style='text-align: center;'>40 Yard Dash</h6>" +
                    "<div style='text-align: center;'>No data available</div>",
                    unsafe_allow_html=True
                )
            R1LA, R1LB, R1LC = st.columns([1, 1, 1], gap="small", border=False)
            with R1LA:
                # Display the strip plot for 40 Yard Dash
                if not sprintData.empty and 'total_time_40yd' in sprintData.columns:
                    st.metric(
                        label="Average Time (s)",
                        value=f"{average_40yd} s",
                        border=False
                    )
                else:
                    st.write("NA")
            with R1LB:
                # Display the strip plot for 40 Yard Dash
                if not sprintData.empty and 'perc_40yd' in sprintData.columns:
                    st.metric(
                        label="Combine % Rank",
                        value=f"{int(sprintData['perc_40yd'].max().round(0))}",
                        delta_color="off",
                        border=False
                    )
                else:
                    st.write("NA")
            with R1LC:
                # Display the strip plot for 40 Yard Dash
                if not sprintData.empty and 'ext_perc_40yd' in sprintData.columns:
                    st.metric(
                        label="Elite % Rank",
                        value=f"{int(sprintData['ext_perc_40yd'].max().round(0))}",
                        delta_color="off",
                        border=False
                    )
                else:
                    st.write("NA")

        # Pro Agility Table
        with R1R:
            if not agilityData.empty and 'perc_proAgility' in agilityData.columns:
                st.markdown(
                    # Underlined and centered header
                    "<h6 style='text-align: center; text-decoration: underline;'>Pro Agility Shuttle</h6>" ,
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    "<h6 style='text-align: center;'>Pro Agility Shuttle</h6>" +
                    "<div style='text-align: center;'>No data available</div>",
                    unsafe_allow_html=True
                )
            R1RA, R1RB, R1RC = st.columns([1, 1, 1], gap="small", border=False)
            with R1RA:
                # Display the strip plot for Pro Agility Shuttle
                if not agilityData.empty and 'total_time' in agilityData.columns:
                    st.metric(
                        label="Average Time (s)",
                        value=f"{average_pro_agility} s",
                        delta_color="off",
                        border=False
                    )
                else:
                    st.write("NA")
            with R1RB:
                # Display the strip plot for Pro Agility Shuttle
                if not agilityData.empty and 'perc_proAgility' in agilityData.columns:
                    st.metric(
                        label="Combine % Rank",
                        value=f"{int(agilityData['perc_proAgility'].max().round(0))}",
                        delta_color="off",
                        border=False
                    )
                else:
                    st.write("NA")
            with R1RC:
                # Display the strip plot for Pro Agility Shuttle
                if not agilityData.empty and 'ext_perc_proAgility' in agilityData.columns:
                    st.metric(
                        label="Elite % Rank",
                        value=f"{int(agilityData['ext_perc_proAgility'].max().round(0))}",
                        delta_color="off",
                        border=False
                    )
                else:
                    st.write("NA")
        
    else:
        st.info("Select an athlete from the sidebar to view test results.")