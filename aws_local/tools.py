"""
Externalizing some basic AWS methods.
"""
import boto3
from botocore.exceptions import ClientError, ConfigParseError


def send_email(
    aws_region: str, sender: str, receiver: list, subject: str, message: str
) -> None:
    """Sends an email using the AWS SES API.
    If not run in Lamba, requires AWS credentials in ~/.aws/credentials

    Args:
        aws_region (str): the AWS region to connect to
        sender (str): the sender's email formatted as: Pretty Name (email@address.com)
        receiver (list): A list containing recipient emails, without pretty names
        subject (str): The subject line of the email
        message (str): A plain-text formatted message body
    """
    # Create the email client.
    client = boto3.client("ses", region_name=aws_region)

    # Send the message.
    try:
        client.send_email(
            Destination={
                "ToAddresses": receiver,
            },
            Message={
                "Body": {
                    "Text": {
                        "Charset": "UTF-8",
                        "Data": message,
                    },
                },
                "Subject": {
                    "Charset": "UTF-8",
                    "Data": subject,
                },
            },
            Source=sender,
        )
    except ClientError as e:
        print(e.response["Error"]["Message"])


def get_secret(secret_name: str, region: str) -> str:
    """Retrieves a secret from AWS Secrets Manager.
    Not intended to retrieve binary or base64 secrets.

    Args:
        secret_name (str): the name of the secret, for example prod/MyApp/SomeSecret
        region (str): the AWS region that Secrets Manager is running in

    Returns:
        str: The contents of the secret, as a string.
    """

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=region)

    # Retrieve the secret
    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        print(e.__str__)
    else:
        secret = get_secret_value_response["SecretString"]
        return secret
