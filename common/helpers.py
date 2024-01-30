import boto3
import os
import json

SECRET_NAME = os.getenv("SECRET_NAME")
REGION_NAME = os.getenv("REGION_NAME")
BUCKET_NAME = os.getenv("BUCKET_NAME")


def get_secret():
    print("Fetching secrets...")

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=REGION_NAME)

    # Retrieve the secret
    try:
        get_secret_value_response = client.get_secret_value(SecretId=SECRET_NAME)
    except Exception as e:
        raise e

    # Your secret's value
    if "SecretString" in get_secret_value_response:
        secret = get_secret_value_response["SecretString"]
        return json.loads(secret)
