#!/usr/bin/env python3
"""
A script to download specific reports from OneTrust.

Requires selenium.
Chromedriver executable must be in the PATH.
"""
import getpass
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from time import sleep

BROWSER_WAIT_TIMEOUT_IN_S = 30

email_address = ""  # input("Enter email: ")
okta_username = ""  # input("Enter okta username: ")
okta_password = ""  # getpass.getpass("Enter okta password: ")

ot_url = "https://uat.onetrust.com/"
rpt_url = "https://uat.onetrust.com/reporting/column/60d900aa99845310d8a94078"


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


with newChromeDriver("/Users/justin/Desktop/onetrust") as driver:
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

    # Navigate to report URL
    driver.get(rpt_url)

    # Select report organized by Subtask
    driver_wait.until(
        EC.presence_of_element_located((By.XPATH, "//a[contains(., 'DSAR Subtask')]"))
    )
    driver.find_element_by_xpath("//a[contains(., 'DSAR Subtask')]").click()

    # Wait for export button to be available, then click it.
    driver_wait.until(
        EC.presence_of_element_located((By.XPATH, "//button[contains(., 'Export')]"))
    )
    driver.find_element_by_xpath("//button[contains(., 'Export')]").click()

    # Close modal dialog.
    driver_wait.until(
        EC.presence_of_element_located((By.XPATH, "//button[contains(., 'Close')]"))
    )
    driver.find_element_by_xpath("//button[contains(., 'Close')]").click()

    # This is currently a race condition, assuming the report will be ready in 15s or less.
    sleep(15)

    # Click the notification icon to expand the list.
    driver.find_element_by_xpath(
        "//button[contains(@class, 'gh-notification-action')]"
    ).click()

    # FIXME: Find and click the top Report Export button.
    driver.find_element_by_xpath("//p[contains(., 'Report Export')]").click()
