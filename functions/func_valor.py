import streamlit as st
import requests
import pandas as pd
import json

valorEndpoint = st.secrets["VALOR_URL"]
tokenURL = st.secrets["VALOR_TOKEN_URL"]

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
        data = response.json()
        id_token = data['AuthenticationResult']['IdToken']
        print("\n✅ JWT IdToken:\n")
        print(id_token)
        return id_token
    else:
        print("\n❌ Authentication failed:")
        print(f"Status Code: {response.status_code}")

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
def ValorSessions(token: str = None, url: str = None):
    """
    Fetches Valor data from the API.
    Returns:
        pd.DataFrame: DataFrame containing Valor data.
    """
    # Define the API endpoint
    api_url = url

    # Initialize an empty list to store all items
    all_items = []

    # Default continuation token should be an emptry string wrapped in a json
    continuation_token = json.dumps("")

    # Replace 'your_jwt_token' with your actual JWT token
    jwt_token = token

    while True:
        # Create headers with the X-Continuation-Token and JWT token
        headers = {
            'X-Continuation-Token': continuation_token,  # Include the continuation token
            'Authorization': f'Bearer {jwt_token}'
        }

        # Define query parameters
        params = {
            'limit': '', # Replace with the limit you need (Default = '')
            'athleteID': 'E23A0C23-8AAB-41FC-BE3E-0C6F16EA4D4D'  # Replace with the athlete ID you need (Default = '')
        }

        # Make the API request with the headers and query parameters
        response = requests.get(api_url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            items = json.loads(data.get('body'))

            # Append the items from the current page to the list
            all_items.extend(items)

            # Check if there's a next page
            continuation_token = data.get('X-Continuation-Token')

            if continuation_token != "null":
                continuation_token = json.dumps(continuation_token)

            if continuation_token == "null":
                # No more pages to fetch, exit the loop
                break
        else:
            print(f"Error: {response.status_code}")
            break