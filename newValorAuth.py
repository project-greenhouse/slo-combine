import boto3
from botocore.exceptions import ClientError


def get_jwt_token(username: str, password: str, client_id: str) -> str:
    """
    Authenticate with AWS Cognito and return the JWT IdToken.

    Args:
        username (str): Cognito username.
        password (str): Cognito password.
        client_id (str): App client ID from Cognito User Pool.
        user_pool (str): User Pool ID for the Cognito User Pool.

    Returns:
        str: JWT IdToken on success.

    Raises:
        RuntimeError: If authentication fails.
    """
    try:
        cognito = boto3.client("cognito-idp", region_name="us-east-1")

        response = cognito.initiate_auth(
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": username,
                "PASSWORD": password,
            },
            ClientId=client_id
        )

        return response["AuthenticationResult"]["IdToken"]

    except ClientError as e:
        raise RuntimeError(f"Authentication failed: {e.response['Error']['Message']}")

