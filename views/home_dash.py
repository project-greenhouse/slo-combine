import streamlit as st
import pandas as pd

# --- App Modules ---
import functions.data as db
import functions.viz as viz
import functions.utility as utility
import functions.func_valor as val
from functions.func_summary import get_athlete_summary

# --- View Modules ---
import views.valor_data as valor

# --- Retrieve selected athlete from session state ---
selected_name = st.session_state.get("selected_name", None)

# Report Header
logo_url = st.secrets["SUPABASE_LOGO_URL"]
_,headerLogo, headerTitle = st.columns((0.5,2, 3))
headerLogo.image(logo_url, width=125, use_container_width=False)
headerTitle.title(f"Code 8 Athlete Report")

# --- Home Page Content ---

# Athlete Info Section
st.subheader(
    "Athlete Information",
    anchor=False,
    #help="This section provides basic information about the athlete including name, age, school, and more.",
    divider="orange"
)

# Get Athlete Sign Up Data
athlete_info = db.AthleteInfoData(athlete=selected_name)

# Condensed athlete info layout - 2 rows instead of 3
# Row 1: Name, Age, Gender, Height
col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
with col1:
    if athlete_info.empty:
        st.markdown("<b>Name: </b>N/A", unsafe_allow_html=True)
    else:
        st.markdown("<b>Name: </b>" + athlete_info['Name'].values[0], unsafe_allow_html=True)
with col2:
    if athlete_info.empty:
        st.markdown("<b>Age: </b>N/A", unsafe_allow_html=True)
    else:
        st.markdown("<b>Age: </b>" + str(athlete_info['Age'].values[0]), unsafe_allow_html=True)
with col3:
    if athlete_info.empty:
        st.markdown("<b>Gender: </b>N/A", unsafe_allow_html=True)
    else:
        st.markdown("<b>Gender: </b>" + athlete_info['Gender'].values[0], unsafe_allow_html=True)
with col4:
    if athlete_info.empty:
        st.markdown("<b>Height: </b>N/A", unsafe_allow_html=True)
    else:
        st.markdown("<b>Height: </b>" + str(athlete_info['Height_in'].values[0]) + '"', unsafe_allow_html=True)

# Row 2: School, Sports, Position, Limb Dominance
col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
with col1:
    if athlete_info.empty:
        st.markdown("<b>School - Grad Year: </b>N/A", unsafe_allow_html=True)
    else:
        st.markdown("<b>School - Grad Year: </b>" + athlete_info['School-GradYear'].values[0], unsafe_allow_html=True)
with col2:
    if athlete_info.empty:
        st.markdown("<b>Sport: </b>N/A", unsafe_allow_html=True)
    else:
        st.markdown("<b>Sport: </b>" + athlete_info['Sport'].values[0], unsafe_allow_html=True)
with col3:
    if athlete_info.empty:
        st.markdown("<b>Position: </b>N/A", unsafe_allow_html=True)
    else:
        st.markdown("<b>Position: </b>" + athlete_info['Position'].values[0], unsafe_allow_html=True)
with col4:
    if athlete_info.empty:
        st.markdown("<b>Dominance: </b>N/A", unsafe_allow_html=True)
    else:
        st.markdown("<b>Dominance: </b>" + athlete_info['LimbDominance'].values[0], unsafe_allow_html=True)

# Movement Data Section
st.subheader(
    "Movement Data",
    anchor=False,
    #help="This section includes data from various movement tests such as vertical jump, broad jump, and more.",
    divider="orange"
)

# Get dynamic movement data based on selected athlete
if selected_name:
    try:
        # Get Valor data for the selected athlete
        token = db.valorToken
        valorAthletes = val.ValorAthletes(token=token)
        
        # Check if athlete exists in Valor data
        athlete_match = valorAthletes[valorAthletes['Name'] == selected_name]
        if not athlete_match.empty:
            athlete_id = athlete_match['ValorID'].values[0]
            valorSessions = val.ValorSessions(token=token)
            athleteSession = valorSessions[valorSessions['Athlete ID'] == athlete_id]
            
            # Get session IDs for different tests
            hip_sessions = athleteSession[athleteSession['Session Name'] == "Hip Hinge Test"]
            left_shoulder_sessions = athleteSession[athleteSession['Session Name'] == "Left 90-90 Test Unilateral Shoulder IR/ER"]
            right_shoulder_sessions = athleteSession[athleteSession['Session Name'] == "Right 90-90 Test Unilateral Shoulder IR/ER"]
            left_ankle_sessions = athleteSession[athleteSession['Session Name'] == "Left Regular Ankle Dorsiflexion - Weighted"]
            right_ankle_sessions = athleteSession[athleteSession['Session Name'] == "Right Regular Ankle Dorsiflexion - Weighted"]
            
            # Calculate scores if data exists
            shoulder_score = 0
            ankle_score = 0
            hip_score = 0
            
            # Hip score
            if not hip_sessions.empty:
                hip_data = val.ValorHipHinge(token=token, key=hip_sessions['s3Key'].values[0])
                hip_score = hip_data["Score"].mean(skipna=True) * 100 if not hip_data.empty else 0
            
            # Shoulder score (average of left and right)
            shoulder_scores = []
            if not left_shoulder_sessions.empty:
                left_shoulder_data = val.ValorLeftShoulder(token=token, key=left_shoulder_sessions['s3Key'].values[0])
                if not left_shoulder_data.empty:
                    shoulder_scores.append(left_shoulder_data["Score"].mean(skipna=True))
            
            if not right_shoulder_sessions.empty:
                right_shoulder_data = val.ValorRightShoulder(token=token, key=right_shoulder_sessions['s3Key'].values[0])
                if not right_shoulder_data.empty:
                    shoulder_scores.append(right_shoulder_data["Score"].mean(skipna=True))
            
            if shoulder_scores:
                shoulder_score = sum(shoulder_scores) / len(shoulder_scores) * 100
            
            # Ankle score (average of left and right)
            ankle_scores = []
            if not left_ankle_sessions.empty:
                left_ankle_data = val.ValorLeftAnkle(token=token, key=left_ankle_sessions['s3Key'].values[0])
                if not left_ankle_data.empty:
                    ankle_scores.append(left_ankle_data["Score"].mean(skipna=True))
            
            if not right_ankle_sessions.empty:
                right_ankle_data = val.ValorRightAnkle(token=token, key=right_ankle_sessions['s3Key'].values[0])
                if not right_ankle_data.empty:
                    ankle_scores.append(right_ankle_data["Score"].mean(skipna=True))
            
            if ankle_scores:
                ankle_score = sum(ankle_scores) / len(ankle_scores) * 100
                
        else:
            # Athlete not found in Valor data
            shoulder_score = ankle_score = hip_score = 0
            
    except Exception as e:
        # Handle any errors gracefully
        st.error(f"Error loading movement data: {str(e)}")
        shoulder_score = ankle_score = hip_score = 0
else:
    # No athlete selected
    shoulder_score = ankle_score = hip_score = 0

with st.container(height=225, border=False):
    shoulCol, anklCol, hipCol = st.columns([1,1,1], vertical_alignment="center", gap="small", border=False)
    with shoulCol:
        st.markdown(
            # Underlined and centered header
            "<h6 style='text-align: center; text-decoration: underline; margin-bottom: 0px;'>Shoulder</h6>" ,
            unsafe_allow_html=True
        )
        # Center the plot using columns
        _, plot_col, _ = st.columns([0.2, 1, 0.2])
        with plot_col:
            #viz.radial_gauge(value=shoulder_score, title="Shoulder Score", figsize=(1, 1))
            utility.ScoreChart(round(shoulder_score, 0), show=True, key="shoulder_score_chart")
            
    with anklCol:
        st.markdown(
            # Underlined and centered header
            "<h6 style='text-align: center; text-decoration: underline; margin-bottom: 0px;'>Ankle</h6>" ,
            unsafe_allow_html=True
        )
        # Center the plot using columns
        _, plot_col, _ = st.columns([0.2, 1, 0.2])
        with plot_col:
            #viz.radial_gauge(value=ankle_score, title="Ankle Score", figsize=(1, 1))
            utility.ScoreChart(round(ankle_score, 0), show=False, key="ankle_score_chart")
            
    with hipCol:
        st.markdown(
            # Underlined and centered header
            "<h6 style='text-align: center; text-decoration: underline; margin-bottom: 0px;'>Hip Hinge</h6>" ,
            unsafe_allow_html=True
        )
        # Center the plot using columns
        _, plot_col, _ = st.columns([0.2, 1, 0.2])
        with plot_col:
            #viz.radial_gauge(value=hip_score, title="Hip Score", figsize=(1, 1))
            utility.ScoreChart(round(hip_score, 0), show=False, key="hip_score_chart")

           
# ----- Shoulder 90-90 ROM Results Table -----
st.markdown(
            # Centered header without streamlit anchor
            "<h5 style='text-align: center; margin-bottom: 0px;'>Shoulder 90-90 Range of Motion Results</h5>" ,
            unsafe_allow_html=True
        )
_, shldrTab, _ = st.columns([0.2, 1, 0.2], gap="small", border=False)
with shldrTab:
    if selected_name:
        try:
            val.valorDisplayTables(valor.shoulder_data)
        except:
            st.info("Detailed movement data tables not available for this athlete.")

# ----- Ankle Dorsiflexion Results Table -----
st.markdown(
            # Centered header without streamlit anchor
            "<h5 style='text-align: center; margin-bottom: 0px;'>Ankle Dorsiflexion Range of Motion Results</h5>" ,
            unsafe_allow_html=True
        )
_, anklTab, _ = st.columns([0.2, 1, 0.2], gap="small", border=False)
with anklTab:
    if selected_name:
        try:
            val.valorDisplayTables(valor.ankle_data)
        except:
            st.info("Detailed movement data tables not available for this athlete.")

# ----- Hip Hinge Results Table -----
st.markdown(
            # Centered header without streamlit anchor
            "<h5 style='text-align: center; margin-bottom: 0px;'>Hip Hinge Range of Motion Results</h5>" ,
            unsafe_allow_html=True
        )
_, hipTab, _ = st.columns([0.2, 1, 0.2], gap="small", border=False)
with hipTab:
    if selected_name:
        try:
            # Filter rows from Metric column ="Hip ER (°)",  "Hip Flex. (°)", "Knee Flex. (°)", "Shin Angle (°)", "Torso Ext. (°)"
            hingeData = valor.HipHinge[valor.HipHinge['Metric'].isin(["Hip ER (°)", "Hip Flex. (°)", "Knee Flex. (°)", "Shin Angle (°)", "Torso Ext. (°)"])]
            val.valorDisplayTables(hingeData)
        except:
            st.info("Detailed movement data tables not available for this athlete.")

#-----------------------------------------------------#
#----- Speed Data Section -----#
#-----------------------------------------------------#

st.subheader(
    ":material/sprint: Speed Data",
    anchor=False,
    #help="This section includes data from various speed tests such as 40-yard dash, shuttle run, and more.",
    divider="orange"
)

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
    
    # Only show the plot if we have data for both tests
    if not sprintData.empty and not agilityData.empty:
        fig = viz.plot_reactive_performance(sprintData, agilityData)
        st.plotly_chart(fig, use_container_width=True)
        
        # Streamlit horizontal bar chart for sprint and agility data
        # Prepare data for horizontal bar chart similar to the plotly chart
        sprint_trial = sprintData[sprintData['total_time_40yd'] == sprintData['total_time_40yd'].min()]
        agility_trial = agilityData[agilityData['total_time'] == agilityData['total_time'].min()]
        
        # Create DataFrame for the horizontal bar chart with split times
        chart_data = pd.DataFrame({
            'Test': ['40 Yard Sprint', '40 Yard Sprint', 'Pro Agility', 'Pro Agility', 'Pro Agility', 'Pro Agility'],
            'Split': ['1', '2', '1', '2', '3', '4'],
            "Time": [float(sprint_trial["split_time_10yd"].iloc[0]) if not sprint_trial.empty and "split_time_10yd" in sprint_trial.columns else 0,
                    float(sprint_trial["split_time_40yd"].iloc[0]) if not sprint_trial.empty and "split_time_40yd" in sprint_trial.columns else 0,
                    float(agility_trial["split_time_5yd"].iloc[0]) if not agility_trial.empty and "split_time_5yd" in agility_trial.columns else 0,
                    float(agility_trial["split_time_10yd"].iloc[0]) if not agility_trial.empty and "split_time_10yd" in agility_trial.columns else 0,
                    float(agility_trial["split_time_15yd"].iloc[0]) if not agility_trial.empty and "split_time_15yd" in agility_trial.columns else 0,
                    float(agility_trial["split_time_20yd"].iloc[0]) if not agility_trial.empty and "split_time_20yd" in agility_trial.columns else 0]
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

#-----------------------------------------------------#
#----- Power Data Section -----#
#-----------------------------------------------------#
VerticalData = db.verticalJump(player_name=selected_name)
BroadJumpData = db.broadJump(player_name=selected_name)
ForcePlateCMJData = db.AthleteCMJ(athlete=selected_name)
ForcePlateMRData = db.AthleteMR(athlete=selected_name)

st.subheader(
    ":material/sports_handball: Power Data",
    anchor=False,
    #help="This section includes data from various power tests such as vertical jump, broad jump, and more.",
    divider="orange"
)

#----- Row 1: Power Ranks -----
fdData = pd.DataFrame({
    "Comp": ['SLO Combine', 'SLO Combine', 'Elite', 'Elite'],
    "Metric": ['Reactive Strength','Relative Power', 'Reactive Strength', 'Relative Power'],
    "Value": [ForcePlateCMJData['mRSI SLO Rank'].max().round(0), ForcePlateCMJData['Peak Rel Power SLO Rank'].max().round(0), ForcePlateCMJData['mRSI Elite Rank'].max().round(0), ForcePlateCMJData['Peak Rel Power Elite Rank'].max().round(0)]
})

viz.plot_power_ranks(fdData, key="power_ranks_chart")

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
        st.metric("Vertical Jump (in)", int(VerticalData['VerticalJump'].max().round(0)), delta=None)
    with vCol2:
        # Display the horizontal jump distance
        st.metric("Combine % Rank", int(VerticalData['perc_vert'].max().round(0)), delta=None)
    with vCol3:
        # Display the broad jump distance
        st.metric("Elite % Rank", int(VerticalData['ext_perc_vert'].max().round(0)), delta=None)

with broadCol:
    st.markdown(
    # Underlined and centered header
    "<h6 style='text-align: center; text-decoration: underline;'>Broad Jump</h6>" ,
    unsafe_allow_html=True
    )
    bCol1, bCol2, bCol3= st.columns([1, 1, 1], gap="small", border=False)
    with bCol1:
        st.metric("Broad Jump (in)", int(BroadJumpData['BestBroadJump'].max().round(0)), delta=None)
    with bCol2:
        st.metric("Combine % Rank", int(BroadJumpData['perc_broad'].max().round(0)), delta=None)
    with bCol3:
        st.metric("Elite % Rank", int(BroadJumpData['ext_perc_broad'].max().round(0)), delta=None)

#-----------------------------------------------------#
_,fpTab, mrTab,_ = st.columns([0.5,1,1, 0.5], gap="medium", border=False)
#----- Force Plate Tables -----#
with fpTab:
    # Force Plate Tables
    st.markdown(
    # Underlined and centered header
    "<h6 style='text-align: center; margin-bottom: 0px;'>Force Plate Countermovement Jump</h6>" ,
    unsafe_allow_html=True
    )
    if selected_name:
        try:
            # Get Force Plate data for the selected athlete and summarize it with max values for 'Jump Height (in)', 'mRSI', 'Peak Rel Prop Power (W/kg)'
            dfPlatesCMJ = ForcePlateCMJData.copy()
            dfPlatesCMJ = dfPlatesCMJ[['Jump Height (in)', 'mRSI', 'Peak Rel Prop Power (W/kg)', 'Braking Asymmetry']].max().reset_index().round(2)
            dfPlatesCMJ.columns = ['Metric', 'Value']
            # rename columns for clarity (mRSI -> Reactive Strength Index, Peak Rel Prop Power -> Peak Relative Power)
            dfPlatesCMJ.loc[dfPlatesCMJ['Metric'] == 'mRSI', 'Metric'] = 'Reactive Strength Index'
            dfPlatesCMJ.loc[dfPlatesCMJ['Metric'] == 'Peak Rel Prop Power (W/kg)', 'Metric'] = 'Peak Relative Power'
            # If value 'Braking Asymmetry' value is negative append the absolute value of 'Braking Asymmetry' to '% Left', else append the absolute value to '% Right'
            dfPlatesCMJ.loc[dfPlatesCMJ['Metric'] == 'Braking Asymmetry', 'Value'] = str(dfPlatesCMJ['Value'].apply(lambda x: f"{int(abs(x))}% Left" if x > 0 else f"{int(abs(x))}% Right"))
            dfPlatesCMJ["value"] = dfPlatesCMJ["Value"].astype(str)  # Ensure Value is string for display
            st.dataframe(dfPlatesCMJ, hide_index=True, use_container_width=True)
        except:
            st.info("Force Plate data tables not available for this athlete.")
#----- Multi-Rebound Tables -----#
with mrTab:
    # Force Plate Tables
    st.markdown(
    # Underlined and centered header
    "<h6 style='text-align: center; margin-bottom: 0px;'>Force Plate Multi-Rebound Jump</h6>" ,
    unsafe_allow_html=True
    )
    if selected_name:
        try:
            # Get Force Plate data for the selected athlete and summarize it with max values for 'Jump Height (in)', 'mRSI', 'Peak Rel Prop Power (W/kg)'
            dfPlatesMR = ForcePlateMRData.copy()
            dfPlatesMR = dfPlatesMR[['Avg Jump Height (in)', 'Peak Jump Height (in)', 'Avg RSI', 'Peak RSI']].max().reset_index().round(2)
            dfPlatesMR.columns = ['Metric', 'Value']
            # rename columns for clarity
            dfPlatesMR.loc[dfPlatesMR['Metric'] == 'Avg RSI', 'Metric'] = 'Average Reactive Strength Index'
            dfPlatesMR.loc[dfPlatesMR['Metric'] == 'Peak RSI', 'Metric'] = 'Peak Reactive Strength Index'

            st.dataframe(dfPlatesMR, hide_index=True, use_container_width=True)
        except:
            st.info("Force Plate data tables not available for this athlete.")


#-----------------------------------------------------#
#----- Commentary Section -----#
# Summary Section
if selected_name:
    summary_content = get_athlete_summary(selected_name)
    if summary_content and summary_content.strip():
    
        # Create a styled container for the summary
        st.markdown(
            """
            <div style="
                background-color: #f0f2f6;
                padding: 20px;
                border-radius: 10px;
                border-left: 2px solid #e1c173;
                border-right: 2px solid #e1c173;
                border-top: 2px solid #e1c173;
                border-bottom: 2px solid #e1c173;
                margin: 5px 0;
            ">
            """ "Summary: " + summary_content + """
            </div>
            """,
            unsafe_allow_html=True
        )

#-----------------------------------------------------#
# --- PDF/Image Export Functionality ---

# Check if export was requested
if st.session_state.get("export_pdf", False):
    # Reset the export flag
    st.session_state.export_pdf = False
    
    st.markdown("### 📄 Export Options")
    st.info("Choose your preferred export method:")
    
    # Method 1: Browser Print (most reliable)
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🖨️ Browser Print to PDF")
        st.markdown("**Recommended Method**")
        
        if st.button("Open Print Dialog", type="primary", use_container_width=True):
            # JavaScript to open print dialog
            st.markdown("""
            <script>
            setTimeout(function() {
                window.print();
            }, 500);
            </script>
            """, unsafe_allow_html=True)
            
        st.markdown("""
        **Instructions:**
        1. Click 'Open Print Dialog' above
        2. In the print dialog, select 'Save as PDF' as destination
        3. Choose 'More settings' and uncheck 'Headers and footers'
        4. Click 'Save' to download your PDF
        """)
    
    with col2:
        st.markdown("#### 📱 Screenshot Method")
        st.markdown("**Alternative Method**")
        
        # Add CSS to hide sidebar and buttons for clean screenshot
        st.markdown("""
        <style>
        .screenshot-mode .stApp > div[data-testid="stSidebar"] {
            display: none !important;
        }
        .screenshot-mode button {
            display: none !important;
        }
        .screenshot-mode .export-buttons {
            display: none !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        screenshot_mode = st.button("Enable Screenshot Mode", use_container_width=True)
        if screenshot_mode:
            st.session_state.screenshot_mode = True
            st.rerun()
            
        st.markdown("""
        **Instructions:**
        1. Click 'Enable Screenshot Mode'
        2. Use your browser's screenshot tool or snipping tool
        3. Capture the main content area
        4. Save as image or convert to PDF
        """)
    
    # Add print-specific CSS
    st.markdown("""
    <style>
    @media print {
        .stApp > header[data-testid="stHeader"] {
            display: none !important;
        }
        .stApp > div[data-testid="stSidebar"] {
            display: none !important;
        }
        .main .block-container {
            padding-top: 0.5rem !important;
            padding-bottom: 0.5rem !important;
            max-width: none !important;
            margin: 0 !important;
        }
        .stApp {
            background-color: white !important;
        }
        button, .stButton {
            display: none !important;
        }
        .export-section {
            display: none !important;
        }
    }
    
    /* Hide export buttons when in screenshot mode */
    .screenshot-mode .export-buttons {
        display: none !important;
    }
    .screenshot-mode button {
        display: none !important;
    }
    .screenshot-mode .stButton {
        display: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Check if screenshot mode is enabled
if st.session_state.get("screenshot_mode", False):
    st.markdown('<div class="screenshot-mode">', unsafe_allow_html=True)
    st.success("📸 Screenshot mode enabled! The page is now optimized for capturing. Use your screenshot tool to capture the content below.")
    if st.button("Exit Screenshot Mode"):
        st.session_state.screenshot_mode = False
        st.rerun()
