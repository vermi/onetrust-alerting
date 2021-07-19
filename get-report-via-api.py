#!/usr/bin/env python
"""
Basic script to fetch information from OneTrust via undocumented API.

Requires selenium and chromedriver.
"""

import base64
import getpass
import json
import os
from time import sleep
from datetime import datetime

import jwt
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

BROWSER_WAIT_TIMEOUT_IN_S = 30
now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

print(now)

email_address = input("Enter email: ")
okta_username = input("Enter okta username: ")
okta_password = getpass.getpass("Enter okta password: ")

ot_url = "https://uat.onetrust.com/"
api = "https://uat.onetrust.com/api/datasubject/v1/subtask/search/en-us"
api_params = "?page=0&size=20&sort=deadline,asc&viewId=undefined"


def newChromeDriver(downloadPath=None) -> webdriver.Chrome:
    """
    Initiates a new chrome driver with the specified download path for saving files.
    """
    options = webdriver.ChromeOptions()
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--incognito")

    if downloadPath is not None:
        prefs = {}
        os.makedirs(downloadPath, exist_ok=True)
        prefs["profile.default_content_settings.popups"] = 0
        prefs["download.default_directory"] = downloadPath
        options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(options=options)
    return driver


with newChromeDriver() as driver:
    driver_wait = WebDriverWait(driver, BROWSER_WAIT_TIMEOUT_IN_S)

    # Navigate to the specified URL.
    driver.get(ot_url)

    # Wait for page to full load before attempting to login.
    driver_wait.until(EC.presence_of_element_located((By.ID, "ot_form-element_0")))
    username_element = driver.find_element_by_id("ot_form-element_0")
    username_element.send_keys(email_address)
    username_element.submit()

    # Process Okta login flow.
    driver_wait.until(EC.presence_of_element_located((By.ID, "okta-signin-username")))
    driver_wait.until(EC.presence_of_element_located((By.ID, "okta-signin-password")))

    okta_username_element = driver.find_element_by_id("okta-signin-username")
    okta_password_element = driver.find_element_by_id("okta-signin-password")
    okta_username_element.send_keys(okta_username)
    okta_password_element.send_keys(okta_password)
    okta_password_element.submit()

    # Wait for login to complete and OneTrust to fully load.
    driver_wait.until(EC.presence_of_element_located((By.ID, "MyApps")))

    local_storage = driver.execute_script("return window.localStorage;")
    access_token = local_storage["access_token"]

    headers = {
        "Authorization": "Bearer " + access_token,
        "Content-Type": "application/json",
    }
    s = requests.session()
    s.headers.update(headers)
    s.cookies.update({c["name"]: c["value"] for c in driver.get_cookies()})
    data = {
        "term": "",
        "filterCriteria": [
            {
                "attributeKey": "SubtaskStatus",
                "operator": "NE",
                "dataType": 30,
                "fromValue": ["30"],
            },
            {
                "attributeKey": "DeadLineRange",
                "operator": "LT",
                "dataType": 60,
                "fromValue": "2021-07-19T06:00:00.000Z",
            },
        ],
    }

    r = s.post(api + api_params, data=json.dumps(data))

    # TODO: Adding email alerting here.
    print(json.dumps(r.json(), indent=2))
