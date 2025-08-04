import streamlit as st
import functions.data as db
import pandas as pd
import functions.func_valor as valFunc
from functions.viz import radial_gauge as rad
#---------------------------------------------------------------------------------------------------#
# ----- DATA COMPONENTS -----
#---------------------------------------------------------------------------------------------------#

# --- Selected Athlete ---
selected_name = st.session_state.get("selected_name", None)
# --- Retrieve Valor API token ---
token = db.valorToken
#--- Retrieve Valor Athletes DataFrame ---
valorAthletes = valFunc.ValorAthletes(token=token)
#--- Retrieve athlete ID from Valor Athletes DataFrame selected_name---
AthleteSelected = valorAthletes[valorAthletes['Name'] == selected_name]['ValorID'].values[0]
#--- Retrieve Valor Sessions DataFrame ---
valorSessions = valFunc.ValorSessions(token=token)

#----- Get the session data if provided
athleteSession = valorSessions[valorSessions['Athlete ID'] == AthleteSelected]

#----- Create a DataFrame for session IDs -----
sessionIds = pd.DataFrame(
    {
        "leftAnkle": [athleteSession[athleteSession['Session Name'] == "Left Regular Ankle Dorsiflexion - Weighted"]['s3Key'].values[0]],
        "rightAnkle": [athleteSession[athleteSession['Session Name'] == "Right Regular Ankle Dorsiflexion - Weighted"]['s3Key'].values[0]],
        "leftShoulder": [athleteSession[athleteSession['Session Name'] == "Left 90-90 Test Unilateral Shoulder IR/ER"]['s3Key'].values[0]],
        "rightShoulder": [athleteSession[athleteSession['Session Name'] == "Right 90-90 Test Unilateral Shoulder IR/ER"]['s3Key'].values[0]],
        "hipHinge": [athleteSession[athleteSession['Session Name'] == "Hip Hinge Test"]['s3Key'].values[0]],
    }
)
print(sessionIds)

#---------------------------------------------------------------------------------------------------#
# ----- TABLE SETUP -----
#---------------------------------------------------------------------------------------------------#

# ----- Hip Hinge Data -----
HipHinge = valFunc.ValorHipHinge(token=token, key=sessionIds['hipHinge'].values[0])
# ----- Left Shoulder Data -----
LeftShoulder = valFunc.ValorLeftShoulder(token=token, key=sessionIds['leftShoulder'].values[0])
# ----- Right Shoulder Data -----
RightShoulder = valFunc.ValorRightShoulder(token=token, key=sessionIds['rightShoulder'].values[0])
# ----- Left Ankle Data -----
LeftAnkle = valFunc.ValorLeftAnkle(token=token, key=sessionIds['leftAnkle'].values[0])
# ----- Right Ankle Data -----
RightAnkle = valFunc.ValorRightAnkle(token=token, key=sessionIds['rightAnkle'].values[0])


#-------------------------------------------------------------------------------------------------------------#
#----- Shoulder Data Table -----

shoulder_data = pd.concat([LeftShoulder, RightShoulder], axis=0)
shoulder_data.reset_index(drop=True, inplace=True)

# Mean score as percentage
shoulder_score = shoulder_data["Score"].mean(skipna=True) * 100

# Filter for specific metrics
shoulder_ir = shoulder_data[shoulder_data['Metric'] == 'Shoulder IR (°)']
shoulder_er = shoulder_data[shoulder_data['Metric'] == 'Shoulder ER (°)']

# Safe helper to extract scalar AvgMax
def get_avgmax(df, metric_name):
    match = df[df["Metric"] == metric_name]
    if not match.empty:
        return match["AvgMax"].values[0]
    return None  # or use np.nan if you prefer

# Get scalar values
r_shoulder_er = get_avgmax(RightShoulder, "Shoulder ER (°)")
l_shoulder_er = get_avgmax(LeftShoulder, "Shoulder ER (°)")
r_shoulder_ir = get_avgmax(RightShoulder, "Shoulder IR (°)")
l_shoulder_ir = get_avgmax(LeftShoulder, "Shoulder IR (°)")

# Handle IR asymmetry
if r_shoulder_ir is not None and l_shoulder_ir is not None:
    if r_shoulder_ir > l_shoulder_ir:
        ir_asymm = f"{round(r_shoulder_ir - l_shoulder_ir, )} R"
    else:
        ir_asymm = f"{round(l_shoulder_ir - r_shoulder_ir,0)} L"
else:
    ir_asymm = "N/A"

# Handle ER asymmetry
if r_shoulder_er is not None and l_shoulder_er is not None:
    if r_shoulder_er > l_shoulder_er:
        er_asymm = f"{round(r_shoulder_er - l_shoulder_er, 0)} R"
    else:
        er_asymm = f"{round(l_shoulder_er - r_shoulder_er, 0)} L"
else:
    er_asymm = "N/A"

# Assemble summary table
shoulder_asymm = pd.DataFrame({
    "Metric": ["Shoulder ER", "Shoulder IR"],
    "Left": [l_shoulder_er.round(0), l_shoulder_ir.round(0)],
    "Right": [r_shoulder_er.round(0), r_shoulder_ir.round(0)],
    "Asymmetry": [er_asymm, ir_asymm]
})

#---------------------------------------------------------------------------------------------------#
#----- Ankle Data Table -----

ankle_data = pd.concat([LeftAnkle, RightAnkle], axis=0)
ankle_data.reset_index(drop=True, inplace=True)
# Mean score as percentage
ankle_score = ankle_data["Score"].mean(skipna=True) * 100

# Filter for specific metrics
ankleDF = ankle_data[ankle_data['Metric'] == 'Ankle DF (°)']
ankleSA = ankle_data[ankle_data['Metric'] == 'Shin Angle (°)']

# Safe helper to extract scalar AvgMax
def get_avgmax(df, metric_name):
    match = df[df["Metric"] == metric_name]
    if not match.empty:
        return match["AvgMax"].values[0]
    return None  # or use np.nan if you prefer

# Get scalar values
r_ankle_df = get_avgmax(RightAnkle, "Ankle DF (°)")
l_ankle_df = get_avgmax(LeftAnkle, "Ankle DF (°)")
r_ankle_sa = get_avgmax(RightAnkle, "Shin Angle (°)")
l_ankle_sa = get_avgmax(LeftAnkle, "Shin Angle (°)")

# Dorsiflexion asymmetry
if r_ankle_df is not None and l_ankle_df is not None:
    if r_ankle_df > l_ankle_df:
        dorsiflexion_asymm = f"{round(r_ankle_df - l_ankle_df, )} R"
    else:
        dorsiflexion_asymm = f"{round(l_ankle_df - r_ankle_df,0)} L"
else:
    dorsiflexion_asymm = "N/A"

# Shin Angle asymmetry
if r_ankle_sa is not None and l_ankle_sa is not None:
    if r_ankle_sa > l_ankle_sa:
        shin_angle_asymm = f"{round(r_ankle_sa - l_ankle_sa, 0)} R"
    else:
        shin_angle_asymm = f"{round(l_ankle_sa - r_ankle_sa, 0)} L"
else:
    shin_angle_asymm = "N/A"

# Assemble summary table
ankle_asymm = pd.DataFrame({
    "Metric": ["Ankle DF", "Shin Angle"],
    "Left": [l_ankle_df.round(0), l_ankle_sa.round(0)],
    "Right": [r_ankle_df.round(0), r_ankle_sa.round(0)],
    "Asymmetry": [dorsiflexion_asymm, shin_angle_asymm]
})


#---------------------------------------------------------------------------------------------------#
#----- Hip Hinge Data Table -----

hip_data = HipHinge.copy()
hip_data.reset_index(drop=True, inplace=True)
# Mean score as percentage
hip_score = hip_data["Score"].mean(skipna=True) * 100

#---------------------------------------------------------------------------------------------------#
# ----- PAGE SETUP -----
#---------------------------------------------------------------------------------------------------#

def ValorPage():
    with st.container(height=250, border=False):
        shoulCol, anklCol, hipCol = st.columns([1,1,1], vertical_alignment="bottom", gap="small", border=False)
        with shoulCol:
            st.markdown(
                    # Underlined and centered header
                    "<h6 style='text-align: center; text-decoration: underline;'>Shoulder</h6>" ,
                    unsafe_allow_html=True
                )
            rad(value=shoulder_score, title= "Shoulder Score")
        with anklCol:
            st.markdown(
                    # Underlined and centered header
                    "<h6 style='text-align: center; text-decoration: underline;'>Ankle</h6>" ,
                    unsafe_allow_html=True
                )
            rad(value=ankle_score, title= "Ankle Score")
        with hipCol:
            st.markdown(
                    # Underlined and centered header
                    "<h6 style='text-align: center; text-decoration: underline;'>Hip Hinge</h6>" ,
                    unsafe_allow_html=True
                )
            rad(value=hip_score, title= "Hip Score")

    valFunc.valorDisplayTables(HipHinge)
    valFunc.valorDisplayTables(shoulder_data)
    valFunc.valorDisplayTables(ankle_data)

    print(shoulder_data)
