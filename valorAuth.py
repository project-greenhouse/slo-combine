import boto3
from botocore.exceptions import ClientError

hostURL = "https://487q8d7goe.execute-api.us-east-1.amazonaws.com/production"

# Define user authentication details
username = 'your_username'
password = 'your_password'
client_id = 'your_client_id'
user_pool_id = 'your_user_pool_id'

# Global variable to store the JWT token
jwt_token = None

def authenticate():
    """
    Authenticate the user and obtain a JWT token.
    Returns the JWT token if successful, None otherwise.
    """
    global jwt_token
    
    try:
        # Initialize a Cognito Identity Provider client
        cognito = boto3.client('cognito-idp', region_name='us-east-1')
        
        # Authenticate the user and obtain a JWT token
        response = cognito.initiate_auth(
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password,
            },
            ClientId=client_id
        )
        
        # Extract the JWT token from the response
        jwt_token = response['AuthenticationResult']['IdToken']
        return jwt_token
        
    except ClientError as e:
        print(f"Authentication failed: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error during authentication: {e}")
        return None

def get_jwt_token():
    """
    Get the current JWT token. If not authenticated yet, attempt authentication.
    Returns the JWT token if available, None otherwise.
    """
    global jwt_token
    
    if jwt_token is None:
        jwt_token = authenticate()
    
    return jwt_token

# Only run authentication when this module is executed directly
if __name__ == "__main__":
    token = authenticate()
    if token:
        print("Authentication successful!")
        print(f"JWT Token: {token}")
    else:
        print("Authentication failed!")
