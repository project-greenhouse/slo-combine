import streamlit as st
import functions.data as db
import pandas as pd
from functions.viz import radial_gauge as rad

import streamlit as st
import requests
import pandas as pd
import json

#---------------------------------------------------------------------------------------------------#
# ----- Valor API Configuration -----
#---------------------------------------------------------------------------------------------------#
valorEndpoint = st.secrets["VALOR_URL"]
tokenURL = st.secrets["VALOR_TOKEN_URL"]

#---------------------------------------------------------------------------------------------------#
# ----- Functions -----
#---------------------------------------------------------------------------------------------------#

#-----------------------------------------------------------------------------#
#----- Valor Extraction Utility -----#
# Valor Extraction Utility
def ValorExtraction(data: dict) -> pd.DataFrame:
    """
    Extract AvgMax and Score for all joints and sides from 'Ang' in a Hip Hinge test.

    Parameters:
    - data (dict): JSON structure with 'WorkoutMetrics'

    Returns:
    - pd.DataFrame with columns: Metric, Side, AvgMax, Score
    """
    ang_data = data.get("WorkoutMetrics", {}).get("Ang", {})
    results = []

    for metric, side_dict in ang_data.items():
        for side in side_dict:  # Handles 'L', 'R', 'F', 'B'
            values = side_dict.get(side, {})
            avgmax = values.get("AvgMax")
            score = values.get("Score")

            if avgmax is not None:
                results.append({
                    "Metric": metric,
                    "Side": side,
                    "AvgMax": avgmax,
                    "Score": score
                })

    return pd.DataFrame(results)

#-----------------------------------------------------------------------------#
#----- Valor Tokens -----#
@st.cache_data(ttl=3600)
def get_jwt_token():
    # Define user authentication details
    username = st.secrets["VALOR_USER"]
    password = st.secrets["VALOR_PASSWORD"]
    client_id = st.secrets["VALOR_CLIENT_ID"]

    payload = {
        "AuthFlow": "USER_PASSWORD_AUTH",
        "ClientId": client_id,
        "AuthParameters": {
            "USERNAME": username,
            "PASSWORD": password
        }
    }
    headers = {
        "Content-Type": "application/x-amz-json-1.1",
        "User-Agent": "insomnia/11.3.0",
        "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth"
    }

    response = requests.request("POST", tokenURL, json=payload, headers=headers)
    # Get Id Token from json response
    if response.status_code == 200:
        data = response.json()["AuthenticationResult"]

        id_token = data.get("IdToken", "")
        access_token = data.get("AccessToken", "")
        refresh_token = data.get("RefreshToken", "")
        expires_in = data.get("ExpiresIn", None)  # in seconds

        print(f"✅ ID Token starts with: {id_token[:20]}...")
        print(f"✅ Access Token starts with: {access_token[:20]}...")

        df = pd.DataFrame([{
            "id_token": id_token,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in_sec": expires_in
        }])

        return df
    else:
        print("\n❌ Authentication failed:")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        return None

#-----------------------------------------------------------------------------#
#----- Valor Athletes -----#
@st.cache_data(ttl=3600)
def ValorAthletes(token: str = None):
    """
    Fetches athletes from Valor API.
    Returns:
        list: List of athletes.
    """
    if not token:
        st.error("Failed to retrieve JWT token.")
        return []

    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(f"{valorEndpoint}athletes", headers=headers)

    if response.status_code == 200:
        raw = response.json()["body"]
        athletes = json.loads(raw)
        # json to dataframe
        df = pd.DataFrame(athletes)
        # Add full name column by combining first and last names
        df['Name'] = df['FirstName'] + ' ' + df['LastName']
        return df
    else:
        st.error(f"Failed to fetch athletes: {response.status_code}")
        return []
    
@st.cache_data(ttl=3600)
def ValorSessions(token: str = None):
    """
    Fetches Valor data from the API.
    Returns:
        pd.DataFrame: DataFrame containing Valor data.
    """
    if not token:
        st.error("No token provided")
        return pd.DataFrame()
        
    # Define the API endpoint
    api_url = f"{valorEndpoint}sessions"
    print(f"\nCalling {api_url}")

    # Initialize an empty list to store all items
    all_items = []

    # Default continuation token should be an empty string
    continuation_token = '""'

    # Debug: Print token info (remove in production)
    print(f"Using token: {token[:50]}..." if token else "No token")
    print(f"API URL: {api_url}")

    while True:
        # Create headers with the JWT token
        headers = {
            'Authorization': f'Bearer {token}',
            'X-Continuation-Token': continuation_token
        }

        # Debug: Print headers (remove sensitive info in production)
        print(f"Headers keys: {list(headers.keys())}")
        print(f"Auth header length: {len(headers.get('Authorization', ''))}")
        print(f"Token preview: Bearer {token[:20]}..." if token else "No token")
        print(f"Continuation token: {continuation_token}")

        # Make the API request with the headers and query parameters
        try:
            response = requests.get(api_url, headers=headers)
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            break

        print(f"Response status: {response.status_code} - {response.reason}")
        print(f"Response headers: {response.headers}")

        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text}")
            break

        try:
            data = response.json()
        except Exception as e:
            print(f"Failed to parse JSON: {e}")
            break
        
        # Get the body and check type
        body = data.get("body")
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except Exception as e:
                print(f"Could not decode body: {e}")
                break

        if not isinstance(body, list):
            print("Unexpected body format:", type(body))
            break

        all_items.extend(body)

        # Check if there's a next page
        continuation_token = data.get('X-Continuation-Token')

        # Handle pagination
        continuation_token = data.get("X-Continuation-Token")
        if not continuation_token or continuation_token == "null":
            break
    
    df = pd.DataFrame(all_items)

    # filter df for 'Date' column values that start with "2025-07-26"
    if 'Date' in df.columns:
        df = df[df['Date'].str.startswith("2025-07-26")]
    return df

#-----------------------------------------------------------------------------#
#----- Valor Left Shoulder Function -----
def ValorLeftShoulder(token: str = None, key: str= None):
    if not token:
        st.error("No token provided")
        return pd.DataFrame()
    
    api_url = f"{valorEndpoint}reportData"

    headers = {'Authorization': f'Bearer {token}',}

    params = {'s3Key': key,}

    response = requests.get(api_url, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()
        data = data['body']
        # convert to dict
        data = json.loads(data)
        # Use the helper function to flatten the JSON response
        data = ValorExtraction(data)
        # Return dataframe with rows filtered for "Side" == "L"
        data = data[data['Side'] == 'L']

        return data
    else:
        st.error(f"Failed to fetch session details: {response.status_code}")
        return pd.DataFrame()

#-----------------------------------------------------------------------------#
#----- Valor Right Shoulder Function -----   
def ValorRightShoulder(token: str = None, key: str= None):
    if not token:
        st.error("No token provided")
        return pd.DataFrame()
    
    api_url = f"{valorEndpoint}reportData"

    headers = {'Authorization': f'Bearer {token}',}

    params = {'s3Key': key,}

    response = requests.get(api_url, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()
        data = data['body']
        # convert to dict
        data = json.loads(data)
        # Use the helper function to flatten the JSON response
        data = ValorExtraction(data)
        # Return dataframe with rows filtered for "Side" == "R"
        data = data[data['Side'] == 'R']

        return data
    else:
        st.error(f"Failed to fetch session details: {response.status_code}")
        return pd.DataFrame()
    
#-----------------------------------------------------------------------------#
#----- Valor Hip Hinge Function -----
def ValorHipHinge(token: str = None, key: str = None):
    if not token:
        st.error("No token provided")
        return pd.DataFrame()
        
    print(f"Key for Hip Hinge: {key}")
    api_url = f"{valorEndpoint}reportData"
    print(f"API URL for Hip Hinge: {api_url}")

    headers = {'Authorization': f'Bearer {token}',}

    params = {'s3Key': key,}

    response = requests.get(api_url, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()
        data = data['body']
        # convert to dict
        data = json.loads(data)
        # Use the helper function to flatten the JSON response
        data = ValorExtraction(data)

        return data     
    else:
        st.error(f"Failed to fetch session details: {response.status_code}")
        return pd.DataFrame()
    
#-----------------------------------------------------------------------------#
#----- Valor Left Ankle Function -----
def ValorLeftAnkle(token: str = None, key: str = None):
    if not token:
        st.error("No token provided")
        return pd.DataFrame()

    api_url = f"{valorEndpoint}reportData"

    headers = {'Authorization': f'Bearer {token}',}

    params = {'s3Key': key,}

    response = requests.get(api_url, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()
        data = data['body']
        # convert to dict
        data = json.loads(data)
        # Use the helper function to flatten the JSON response
        data = ValorExtraction(data)
        # Return dataframe with rows filtered for "Side" == "L"
        data = data[data['Side'] == 'L']

        return data
    else:
        st.error(f"Failed to fetch session details: {response.status_code}")
        return pd.DataFrame()
    
#-----------------------------------------------------------------------------#
#----- Valor Right Ankle Function -----
def ValorRightAnkle(token: str = None, key: str = None):
    if not token:
        st.error("No token provided")
        return pd.DataFrame()

    api_url = f"{valorEndpoint}reportData"

    headers = {'Authorization': f'Bearer {token}',}

    params = {'s3Key': key,}

    response = requests.get(api_url, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()
        data = data['body']
        # convert to dict
        data = json.loads(data)
        # Use the helper function to flatten the JSON response
        data = ValorExtraction(data)
        # Return dataframe with rows filtered for "Side" == "R"
        data = data[data['Side'] == 'R']

        return data
    else:
        st.error(f"Failed to fetch session details: {response.status_code}")
        return pd.DataFrame()
    

#-----------------------------------------------------------------------------#
#----- Valor Display Tables -----
def valorDisplayTables(df: pd.DataFrame):
    """
    Display the Valor data tables in Streamlit.
    
    Parameters:
    - df (pd.DataFrame): DataFrame containing Valor data.
    
    Returns:
    - None
    """
    df = df
    if df.empty:
        st.warning("No Valor data available for this athlete.")
        return 
    
    # Pivot AvgMax and Score
    avgmax = df.pivot(index="Side", columns="Metric", values="AvgMax")
    score = df.pivot(index="Side", columns="Metric", values="Score")
    
    # Round AvgMax values to nearest whole number and convert to integers
    # Handle NaN values by keeping them as NaN, only convert non-NaN values to int
    avgmax = avgmax.round(0)
    # Use nullable integer type to handle NaN values
    avgmax = avgmax.astype('Int64')

    # Create per-cell color map
    def color_cells(val, score_val):
        if pd.isna(score_val):
            return ""
        if score_val == 0.0:
            return "background-color: #FF4B4B;"  # red
        elif score_val == 0.5:
            return "background-color: #FFC107;"  # amber
        return ""

    # Element-wise function that builds a DataFrame of same shape with CSS strings
    def style_dataframe(df, score_df):
        styled = pd.DataFrame("", index=df.index, columns=df.columns)
        for row in df.index:
            for col in df.columns:
                styled.loc[row, col] = color_cells(df.loc[row, col], score_df.loc[row, col])
        return styled

    # Apply style
    styled_df = avgmax.style.apply(style_dataframe, score_df=score, axis=None)

    # Import utility ranges for header mapping
    from functions.utility import HipHingeRanges, ShoulderRanges, AnkleRanges
    
    # Determine which range DataFrame to use based on the metrics present
    current_metrics = set(avgmax.columns)
    
    # Check which range DataFrame matches the current metrics
    hip_metrics = set(HipHingeRanges['Metric'].tolist())
    shoulder_metrics = set(ShoulderRanges['Metric'].tolist())
    ankle_metrics = set(AnkleRanges['Metric'].tolist())
    
    header_mapping = {}
    
    # Debug: print current metrics to understand what we're working with
    print(f"Current metrics: {current_metrics}")
    print(f"Hip metrics: {hip_metrics}")
    print(f"Shoulder metrics: {shoulder_metrics}")
    print(f"Ankle metrics: {ankle_metrics}")
    
    # More specific matching - check for unique identifiers first
    if "Ankle DF (°)" in current_metrics or "Ankle PF (°)" in current_metrics:
        # Use Ankle ranges
        print("Using Ankle ranges")
        for _, row in AnkleRanges.iterrows():
            if row['Metric'] in current_metrics:
                header_mapping[row['Metric']] = row['Header']
                print(f"Mapped: {row['Metric']} -> {row['Header']}")
    elif any(metric in current_metrics for metric in ["Shoulder ER (°)", "Shoulder IR (°)", "Shoulder Rotation Arc"]):
        # Use Shoulder ranges
        print("Using Shoulder ranges")
        for _, row in ShoulderRanges.iterrows():
            if row['Metric'] in current_metrics:
                header_mapping[row['Metric']] = row['Header']
                print(f"Mapped: {row['Metric']} -> {row['Header']}")
    elif any(metric in current_metrics for metric in ["Hip ER (°)", "Hip Flex. (°)", "Knee Flex. (°)", "Torso Ext. (°)"]):
        # Use Hip Hinge ranges
        print("Using Hip Hinge ranges")
        for _, row in HipHingeRanges.iterrows():
            if row['Metric'] in current_metrics:
                header_mapping[row['Metric']] = row['Header']
                print(f"Mapped: {row['Metric']} -> {row['Header']}")
    
    print(f"Final header mapping: {header_mapping}")
    
    # Apply header mapping if any mappings were found
    if header_mapping:
        # Rename columns using the header mapping
        avgmax_renamed = avgmax.rename(columns=header_mapping)
        score_renamed = score.rename(columns=header_mapping)
        
        # Re-apply styling with renamed columns
        def style_dataframe_renamed(df):
            styled = pd.DataFrame("", index=df.index, columns=df.columns)
            for row in df.index:
                for col in df.columns:
                    styled.loc[row, col] = color_cells(df.loc[row, col], score_renamed.loc[row, col])
            return styled
        
        styled_df = avgmax_renamed.style.apply(style_dataframe_renamed, axis=None)
    return styled_df
    

#---------------------------------------------------------------------------------------------------#
# ----- Core Variables -----
#---------------------------------------------------------------------------------------------------#

# --- Selected Athlete ---
selected_name = st.session_state.get("selected_name", None)

valorTokenDF = get_jwt_token()
# --- Retrieve Valor API token ---
token = valorTokenDF['id_token'].values[0]

#----- Retrieve Valor Athletes DataFrame -----
valorAthletes = ValorAthletes(token=token)

#----- Retrieve athlete ID from Valor Athletes DataFrame selected_name----- 
# Check if athlete exists in Valor data
if selected_name == "Blake St. Vincent":
    AthleteSelected = valorAthletes[valorAthletes['Name'] == "Blake St Vincent"]
else:
    AthleteSelected = valorAthletes[valorAthletes['Name'] == selected_name]


#--- Retrieve Valor Sessions DataFrame ---
valorSessions = ValorSessions(token=token)

#----- Get the session data if provided
def athlete_session_ids(AthleteId: str, valorSessions: pd.DataFrame) -> pd.DataFrame:
    # Filter the session IDs for the selected athlete

    athleteSession = valorSessions[valorSessions['Athlete ID'] == AthleteId]

    #----- Create a DataFrame for session IDs -----
    sessionIds = pd.DataFrame({
            "leftAnkle": [athleteSession[athleteSession['Session Name'] == "Left Regular Ankle Dorsiflexion - Weighted"]['s3Key'].values[0]],
            "rightAnkle": [athleteSession[athleteSession['Session Name'] == "Right Regular Ankle Dorsiflexion - Weighted"]['s3Key'].values[0]],
            "leftShoulder": [athleteSession[athleteSession['Session Name'] == "Left 90-90 Test Unilateral Shoulder IR/ER"]['s3Key'].values[0]],
            "rightShoulder": [athleteSession[athleteSession['Session Name'] == "Right 90-90 Test Unilateral Shoulder IR/ER"]['s3Key'].values[0]],
            "hipHinge": [athleteSession[athleteSession['Session Name'] == "Hip Hinge Test"]['s3Key'].values[0]],
        })

    return sessionIds


#-------------------------------------------------------------------------------------------------------------#
#----- Shoulder Data Table -----
# Extract the athlete ID as a string from the AthleteSelected DataFrame
if not AthleteSelected.empty:
    AthleteId = AthleteSelected.iloc[0]['ValorID']  # Get the first (and should be only) athlete ID
    sessionDF = athlete_session_ids(AthleteId=AthleteId, valorSessions=valorSessions)

    #---------------------------------------------------------------------------------------------------#
    # ----- TABLE SETUP -----
    #---------------------------------------------------------------------------------------------------#

    # ----- Hip Hinge Data -----
    HipHinge = ValorHipHinge(token=token, key=sessionDF['hipHinge'].values[0])
    # ----- Left Shoulder Data -----
    LeftShoulder = ValorLeftShoulder(token=token, key=sessionDF['leftShoulder'].values[0])
    # ----- Right Shoulder Data -----
    RightShoulder = ValorRightShoulder(token=token, key=sessionDF['rightShoulder'].values[0])
    # ----- Left Ankle Data -----
    LeftAnkle = ValorLeftAnkle(token=token, key=sessionDF['leftAnkle'].values[0])
    # ----- Right Ankle Data -----
    RightAnkle = ValorRightAnkle(token=token, key=sessionDF['rightAnkle'].values[0])
else:
    st.error("No athlete selected or athlete not found")
    sessionDF = pd.DataFrame()  # Create empty DataFrame to prevent further errors

# Only proceed if we have session data
if not sessionDF.empty:
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
else:
    # Set default values when no session data is available
    shoulder_score = 0
    ankle_score = 0
    hip_score = 0
    shoulder_data = pd.DataFrame()
    ankle_data = pd.DataFrame()
    hip_data = pd.DataFrame()

#---------------------------------------------------------------------------------------------------#
# ----- PAGE SETUP -----
#---------------------------------------------------------------------------------------------------#


# Only display tables if we have data
if not sessionDF.empty:
    st.dataframe(valorDisplayTables(HipHinge))  # Fixed typo: was 'hipHine'
    st.dataframe(valorDisplayTables(shoulder_data))
    st.dataframe(valorDisplayTables(ankle_data))


    