#!/usr/bin/env python
"""
Basic script to fetch information from OneTrust via undocumented API.

Requires selenium and chromedriver.
"""

import configparser
import json
import os
from datetime import datetime

import arrow
import boto3
from botocore.exceptions import ClientError, ConfigParseError
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from onetrust.api import OneTrustSession

OT_INSTANCE_URL = "https://uat.onetrust.com"
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

NO_GROUP_TEMPLATE = """
"""

def readable_time(time) -> str:
    a = arrow.get(time)
    a.to("America/New_York")
    a = a.humanize()
    return a

def utc_to_local(time) -> str:
    a = arrow.get(time)
    a.to("America/New_York")
    return a.datetime.strftime("%Y-%m-%d")

def send_email(aws_region, sender, receiver, subject, message) -> None:
    client = boto3.client("ses", region_name=aws_region)
    try:
        client.send_email(
            Destination={
                "ToAddresses": [
                    receiver,
                ],
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
        print(e.response['Error']['Message'])

def get_secret(secret_name, region) -> str:
    """Retrieves a secret from AWS Secrets Manager."""

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=region)

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        print(e.__str__)
    else:
        secret = get_secret_value_response["SecretString"]
        return secret


def newChromeDriver(downloadPath=None) -> webdriver.Chrome:
    """
    Initiates a new chrome driver with the specified download path for saving files.
    """
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

    options.binary_location = '/opt/chrome/chrome'

    if downloadPath is not None:
        prefs = {}
        os.makedirs(downloadPath, exist_ok=True)
        prefs["profile.default_content_settings.popups"] = 0
        prefs["download.default_directory"] = downloadPath
        options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome("/opt/chromedriver/chromedriver", options=options)
    return driver


def get_token(url, email, okta_user, okta_pass) -> tuple:
    with newChromeDriver() as driver:
        driver_wait = WebDriverWait(driver, BROWSER_WAIT_TIMEOUT_IN_S)

        # Navigate to the specified URL.
        driver.get(url)

        # Wait for page to full load before attempting to login.
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

        local_storage = driver.execute_script("return window.localStorage;")
        access_token = local_storage["access_token"]

        return access_token, driver.get_cookies()


def main(event, context):
    # Gather config information.
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
        print("OS error: {0}".format(e))
    except ConfigParseError as e:
        print("Config parsing error: {0}".format(e))

    # Retrieve Okta password from AWS
    okta_pw = json.loads(get_secret(aws_secret, aws_region))["okta_pw"]

    # Get access_token from OneTrust session
    access_token, cookies = get_token(ot_url, ot_email, okta_user, okta_pw)

    # get overdue subtask info
    ot = OneTrustSession(access_token, cookies, OT_INSTANCE_URL)
    r = ot.get_overdue_subtasks(now)
    subtasks = r.json()

    # Notify on each overdue subtask
    for s in subtasks["content"]:
        if s["subTaskAssignee"] is None:
            # TODO: Send alert email to Admins only
            pass
        else:
            # TODO: Send alert to Admins and assignees
            emails = ot.get_group_email(ot.get_group_id(s["subTaskAssignee"]))
            emails.append(admin_email)
            subtask_name = s["subTaskName"]
            subtask_id = s["subTaskId"]
            due_date = s["subTaskDeadline"]
            send_email(
                aws_region,
                f"OneTrust Admin <{admin_email}>",
                "justin@afakecompany.com",
                "Overdue OneTrust Subtask",
                GROUP_TEMPLATE.format(subtask_name, subtask_id, readable_time(due_date), utc_to_local(due_date)),
            )


if __name__ == "__main__":
    main(None, None)
