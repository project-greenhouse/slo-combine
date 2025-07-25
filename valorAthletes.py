import requests
import valorAuth

def get_athletes():
    """
    Makes a GET request to retrieve athletes data using JWT Bearer token authentication.
    """
    # Get the JWT token from valorAuth module
    jwt_token = valorAuth.get_jwt_token()
    
    if not jwt_token:
        print("Failed to obtain JWT token. Cannot make API request.")
        return None
    
    # Define the API endpoint
    url = "https://487q8d7goe.execute-api.us-east-1.amazonaws.com/production/athletes"
    
    # Set up headers with Bearer token
    headers = {
        'Authorization': f'Bearer {jwt_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        # Make the GET request
        response = requests.get(url, headers=headers)
        
        # Check if the request was successful
        if response.status_code == 200:
            print("Successfully retrieved athletes data:")
            return response.json()
        else:
            print(f"Error: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None

if __name__ == "__main__":
    # Call the function to get athletes data
    athletes_data = get_athletes()
    
    if athletes_data:
        print(athletes_data)
