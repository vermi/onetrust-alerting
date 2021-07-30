#!/usr/bin/env python
"""
Basic script to fetch information from OneTrust via undocumented API.

Requires selenium and chromedriver.
"""

import configparser
import json
import os
import traceback
from datetime import datetime

import arrow
import boto3
from botocore.exceptions import ClientError, ConfigParseError
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from onetrust.api import OneTrustSession

BROWSER_WAIT_TIMEOUT_IN_S = 30
now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

GROUP_TEMPLATE = """Hello--
You are receiving this email because you are assigned to the following subtask, which is overdue:

Subtask Name: {}
Subtask ID: {}
Due Date: {} ({})

Please take action on this subtask as soon as possible to avoid potential SLA violations and regulatory fines.

If you have any questions, contact the ISM Team.
"""

NO_GROUP_TEMPLATE = """Hello--
The following subtask was due {}, but it is not assigned to a group.

Subtask Name: {}
Subtask ID: {}
Due Date: {}

Please investigate this subtask status and ensure that action is taken as soon as possible.
"""


def readable_time(time: str) -> str:
    """Converts an ISO-formatted time string into a human readable format.
    Example: 12 hours ago"""
    a = arrow.get(time)
    a.to("America/New_York")
    a = a.humanize()
    return a


def utc_to_local(time: str) -> str:
    """Converts an ISO-formatted time string from UTC to local time."""
    a = arrow.get(time)
    a.to("America/New_York")
    return a.datetime.strftime("%Y-%m-%d")


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


def newChromeDriver(downloadPath: str = None) -> webdriver.Chrome:
    """Instantiates a new chrome driver.

    Args:
        downloadPath (str): (Optional) the path to save downloads.

    Returns:
        webdriver.Chrome: the configured chrome driver instance
    """

    # These options are REQUIRED for running Chrome under Lambda
    # DO NOT CHANGE
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280x1696")
    options.add_argument("--single-process")
    options.add_argument("--disable-dev-tools")
    options.add_argument("--no-zygote")
    options.add_argument("--user-data-dir=/tmp/chrome-user-data")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/87.0.4280.88 Safari/537.36"
    )

    # use the downloaded version of chrome
    options.binary_location = "/opt/chrome/chrome"

    # Set the download path if necessary
    if downloadPath is not None:
        prefs = {}
        os.makedirs(downloadPath, exist_ok=True)
        prefs["profile.default_content_settings.popups"] = 0
        prefs["download.default_directory"] = downloadPath
        options.add_experimental_option("prefs", prefs)

    # Create the driver using the options above.
    # If running in docker, use the installed version of chromedriver
    driver = webdriver.Chrome(
        "/opt/chromedriver/chromedriver",
        options=options,
    )
    return driver


def get_session(url: str, email: str, okta_user: str, okta_pass: str) -> tuple:
    """Retrieves the OneTrust access_token and session cookies via chromedriver.

    Args:
        url (str): the URL of the OneTrust instance to log in to
        email (str): the email address of the OneTrust account
        okta_user (str): the Scholastic network account to log in to Okta
        okta_pass (str): password for Okta login

    Returns:
        tuple[str, dict]: A tuple containing the access_token (str) and session cookies (dict)
    """

    # Instantiate a new chrome driver for the login.
    with newChromeDriver() as driver:
        # Create a waiter to pause execution while waiting for elements to load.
        driver_wait = WebDriverWait(driver, BROWSER_WAIT_TIMEOUT_IN_S)

        # Navigate to the specified URL.
        driver.get(url)

        # Wait for page to fully load before attempting to log in.
        driver_wait.until(EC.presence_of_element_located((By.ID, "ot_form-element_0")))
        username_element = driver.find_element_by_id("ot_form-element_0")
        username_element.send_keys(email)
        username_element.submit()

        # Process Okta login flow.
        driver_wait.until(
            EC.presence_of_element_located((By.ID, "okta-signin-username"))
        )
        driver_wait.until(
            EC.presence_of_element_located((By.ID, "okta-signin-password"))
        )

        okta_username_element = driver.find_element_by_id("okta-signin-username")
        okta_password_element = driver.find_element_by_id("okta-signin-password")
        okta_username_element.send_keys(okta_user)
        okta_password_element.send_keys(okta_pass)
        okta_password_element.submit()

        # Wait for login to complete and OneTrust to fully load.
        driver_wait.until(EC.presence_of_element_located((By.ID, "MyApps")))

        # Snag session information
        local_storage = driver.execute_script("return window.localStorage;")
        access_token = local_storage["access_token"]

        return access_token, driver.get_cookies()


def main(event, context) -> str:
    """The entry point for the script.

    Args:
        event, context: required for Lambda functionality, but unused.

    Returns:
        str: a status message, will be logged in CloudWatch.
    """

    # Load configuration from file
    try:
        config = configparser.ConfigParser()
        config.read("onetrust.cfg")

        ot_url = config["onetrust"]["url"]
        ot_email = config["onetrust"]["email"]
        aws_secret = config["aws"]["secret_name"]
        aws_region = config["aws"]["region"]
        okta_user = config["okta"]["user"]
        admin_email = config["onetrust"]["admin_email"]
    except OSError as e:
        return f"OS error: {e}"
    except ConfigParseError as e:
        return f"Config parsing error: {e}"

    # Retrieve Okta password from AWS
    okta_pw = json.loads(get_secret(aws_secret, aws_region))["okta_pw"]

    # Get access_token and cookies from OneTrust session
    access_token, cookies = get_session(ot_url, ot_email, okta_user, okta_pw)

    # get overdue subtask info
    ot = OneTrustSession(access_token, cookies, ot_url)
    r = ot.get_overdue_subtasks(now)
    subtasks = r.json()

    # Notify on each overdue subtask
    for s in subtasks["content"]:
        subtask_name = s["subTaskName"]
        subtask_id = s["subTaskId"]
        due_date = s["subTaskDeadline"]

        if s["subTaskAssignee"] is None:
            emails = [
                admin_email,
            ]
            send_email(
                aws_region,
                f"OneTrust Admin <{admin_email}>",
                emails,
                "Overdue OneTrust Subtask",
                NO_GROUP_TEMPLATE.format(
                    readable_time(due_date),
                    subtask_name,
                    subtask_id,
                    utc_to_local(due_date),
                ),
            )
        else:
            emails = ot.get_group_email(ot.get_group_id(s["subTaskAssignee"]))
            emails.append(admin_email)
            send_email(
                aws_region,
                f"OneTrust Admin <{admin_email}>",
                emails,
                "Overdue OneTrust Subtask",
                GROUP_TEMPLATE.format(
                    subtask_name,
                    subtask_id,
                    readable_time(due_date),
                    utc_to_local(due_date),
                ),
            )

    return "done"


if __name__ == "__main__":
    main(None, None)
