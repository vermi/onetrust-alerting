#!/usr/bin/env python3
'''
A script to download specific reports from OneTrust.

Requires selenium.
Chromedriver executable must be in the PATH.
'''
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
    '''
    Initiates a new chrome driver with the specified download path for saving files.
    '''
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

    print("** searching for + filling in the auth login field")
    driver_wait.until(EC.presence_of_element_located((By.ID, "ot_form-element_0")))
    username_element = driver.find_element_by_id("ot_form-element_0")
    username_element.send_keys(email_address)
    username_element.submit()

    print("** waiting for okta login form, then submitting okta username/password")
    driver_wait.until(EC.presence_of_element_located((By.ID, "okta-signin-username")))
    driver_wait.until(EC.presence_of_element_located((By.ID, "okta-signin-password")))

    okta_username_element = driver.find_element_by_id("okta-signin-username")
    okta_password_element = driver.find_element_by_id("okta-signin-password")
    okta_username_element.send_keys(okta_username)
    okta_password_element.send_keys(okta_password)
    okta_password_element.submit()

    print("** waiting for main OneTrust app portal to load")
    driver_wait.until(EC.presence_of_element_located((By.ID, "MyApps")))

    driver.get(rpt_url)
    print("** waiting for report to load")
    driver_wait.until(
        EC.presence_of_element_located((By.XPATH, "//a[contains(., 'DSAR Subtask')]"))
    )
    driver.find_element_by_xpath("//a[contains(., 'DSAR Subtask')]").click()

    driver_wait.until(
        EC.presence_of_element_located((By.XPATH, "//button[contains(., 'Export')]"))
    )
    driver.find_element_by_xpath("//button[contains(., 'Export')]").click()

    driver_wait.until(
        EC.presence_of_element_located((By.XPATH, "//button[contains(., 'Close')]"))
    )
    driver.find_element_by_xpath("//button[contains(., 'Close')]").click()
    print("** waiting for export to be ready")
    sleep(15)

    print("** downloading")
    driver.find_element_by_xpath(
        "//button[contains(@class, 'gh-notification-action')]"
    ).click()
    driver.find_element_by_xpath(
        "//button[contains(@class, 'nf-notification-card__item')]"
    ).click()
