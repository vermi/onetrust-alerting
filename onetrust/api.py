"""
A library encapsulating some functions from the undocumented OneTrust API.

Probably not for general use. See function docstrings for more info.
"""

import json
from typing import Any
import urllib
from datetime import datetime

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class OnetrustSession:
    def __init__(
        self,
        instance_url: str,
        credentials: dict,
        chrome_path: str = "",
        driver_path: str = "chromedriver",
        timeout: int = 30,
    ) -> None:
        """Instantiates the OnetrustSession object.

        Args:
            instance_url (str): the URL of the OneTrust instance to log in to
            credentials (dict): Contains login credentials in the format
                {
                    ot_email (str): the email address of the OneTrust account,
                    okta_user (str): the Scholastic network account to log in to Okta,
                    okta_pw (str): password for Okta login,
                }
            chrome_path (str): (Optional) the absolute path to the chrome executable
            driver_path (str): (Optional) the absolutely path to the chromedriver executable
            timeout (int): (Optional) specifies the desired browser timeout in seconds. Default = 30
        """

        self.instance_url = instance_url
        self.__creds = credentials
        self.__chrome_path = chrome_path
        self.__driver_path = driver_path
        self.access_token, self.cookies = self.__fetch_auth_data(timeout)
        self.request_session = self.__build_session()

    def __fetch_auth_data(self, timeout: int) -> tuple:
        """Retrieves the OneTrust access_token and session cookies via chromedriver.

        Args:
            timeout (int)

        Returns:
            tuple[str, dict]: A tuple containing the access_token (str) and session cookies (dict)
        """

        # Instantiate a new chrome driver for the login.
        with self.__new_chrome_driver() as driver:
            # Create a waiter to pause execution while waiting for elements to load.
            driver_wait = WebDriverWait(driver, timeout)

            # Navigate to the specified URL.
            driver.get(self.instance_url)

            # Wait for page to fully load before attempting to log in.
            driver_wait.until(
                EC.presence_of_element_located((By.ID, "ot_form-element_0"))
            )
            username_element = driver.find_element_by_id("ot_form-element_0")
            username_element.send_keys(self.__creds["ot_email"])
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
            okta_username_element.send_keys(self.__creds["okta_user"])
            okta_password_element.send_keys(self.__creds["okta_pw"])
            okta_password_element.submit()

            # Wait for login to complete and OneTrust to fully load.
            driver_wait.until(EC.presence_of_element_located((By.ID, "MyApps")))

            # Snag session information
            local_storage = driver.execute_script("return window.localStorage;")
            access_token = local_storage["access_token"]

            return access_token, driver.get_cookies()

    def __new_chrome_driver(self):
        """Creates a new chrome driver instance.

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

        # use the specified version of chrome, if necessary
        if self.__chrome_path:
            options.binary_location = self.__chrome_path

        # Create the driver using the options above.
        # Use the downloaded version of chromedriver
        driver = webdriver.Chrome(
            self.__driver_path,
            options=options,
        )
        return driver

    def __build_session(self) -> requests.Session:
        headers = {
            "Authorization": "Bearer " + self.access_token,
        }

        s = requests.session()
        s.headers.update(headers)
        s.cookies.update({c["name"]: c["value"] for c in self.cookies})

        return s


class OnetrustService:
    def __init__(self, session: OnetrustSession) -> None:
        self.__session = session

    def __to_iso_time(self, timestamp: datetime) -> str:
        return timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")

    def get_overdue_subtasks(self, cutoff_date: datetime) -> Any:
        """
        Requests a list of subtasks that have a due date prior to the specified cutoff.

        Args:
            cuttof_date (str): The cutoff date in UNIX-style UTC time string.

        Returns:
            Any: a JSON representation of the response body
        """
        api = "/api/datasubject/v1/subtask/search/en-us?page=0&size=20&sort=deadline,asc&viewId=undefined"

        with self.__session.request_session as s:
            data = {
                "term": "",
                "filterCriteria": [
                    {
                        # Filter out completed subtasks
                        "attributeKey": "SubtaskStatus",    # status
                        "operator": "NE",                   # does not equal
                        "dataType": 30,                     # completed
                        "fromValue": ["30"],                # completed (poorly written filters)
                    },
                    {
                        "attributeKey": "DeadLineRange",
                        "operator": "LT",
                        "dataType": 60,
                        "fromValue": self.__to_iso_time(cutoff_date),
                    },
                ],
            }

            r = s.post(
                self.__session.instance_url + api,
                data=json.dumps(data),
                headers={"Content-type": "application/json"},
            )
            subtasks = r.json()

        return subtasks

    def get_group_id(self, group_name: str) -> str:
        """
        Retrieves the ID of the specified group.

        Args:
            group_name (str): The name of the group to retrieve.

        Returns:
            str: the group ID.
        """
        # TODO: Add error handling in case group does not exist.
        parsed_group = urllib.parse.quote_plus("%" + group_name + "%")
        api = "/api/access/v1/groups?filters=name=~={0}&page=0&size=20".format(
            parsed_group
        )

        with self.__session.request_session as s:
            r = s.get(self.__session.instance_url + api)

        return r.json()["content"][0]["id"]

    def get_group_email(self, group_id: str) -> list:
        """
        Retrieves the emails associated with the specified group ID.

        Args:
            group_id (str): The id of the group to retrieve.

        Returns:
            list: the group emails.
        """
        api = "/api/access/v1/groups/{0}/members?filters=&page=0&size=20".format(
            group_id
        )

        with self.__session.request_session as s:
            r = s.get(self.__session.instance_url + api)

        emails = []
        for user in r.json()["content"]:
            emails.append(user["email"])

        return emails
