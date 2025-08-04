import streamlit as st
import requests
import pandas as pd
import json

valorEndpoint = st.secrets["VALOR_URL"]
tokenURL = st.secrets["VALOR_TOKEN_URL"]

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
    elif any(metric in current_metrics for metric in ["Hip ER (°)", "Hip Ext. (°)", "Hip Flex. (°)", "Hip IR (°)", "Knee Flex. (°)", "Torso Ext. (°)"]):
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

    # Show in Streamlit with real per-cell coloring
    st.dataframe(styled_df, use_container_width=True)