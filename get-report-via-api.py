#!/usr/bin/env python
"""
Basic script to fetch information from OneTrust via undocumented API.

Requires selenium and chromedriver.
"""

import configparser
import json
from datetime import datetime

import arrow

from aws_local.tools import ConfigParseError, get_secret, send_email
from onetrust.api import OnetrustService, OnetrustSession

BROWSER_WAIT_TIMEOUT_IN_S = 30


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


def main(event, context) -> str:
    """The entry point for the script.

    Args:
        event, context: required for Lambda functionality, but unused.

    Returns:
        str: a status message, will be logged in CloudWatch.
    """

    # Load configuration
    try:
        config = configparser.ConfigParser()
        config.read("onetrust.cfg")

        aws_secret = config["aws"]["secret_name"]
        aws_region = config["aws"]["region"]
        ot_url = config["onetrust"]["url"]
        ot_credentials = {
            "ot_email": config["onetrust"]["email"],
            "okta_user": config["okta"]["user"],
            "okta_pw": json.loads(get_secret(aws_secret, aws_region))["okta_pw"],
        }
        admin_email = config["onetrust"]["admin_email"]

        with open(config["templates"]["group"]) as f:
            group_template = f.read()
        with open(config["templates"]["orphan"]) as f:
            orphan_template = f.read()

    except OSError as e:
        return f"OS error: {e}"
    except ConfigParseError as e:
        return f"Config parsing error: {e}"

    # get overdue subtask info
    # Be sure to use the downloaded versions of chrome and chromedriver
    sess = OnetrustSession(
        ot_url,
        ot_credentials,
        chrome_path="/opt/chrome/chrome",
        driver_path="/opt/chromedriver/chromedriver",
        timeout=BROWSER_WAIT_TIMEOUT_IN_S,
    )
    ot = OnetrustService(sess)
    subtasks = ot.get_overdue_subtasks(datetime.utcnow())

    # Notify on each overdue subtask
    # TODO: add a try-except wrapper for more graceful exits in case of weird errors
    # TODO: make the templates more "template-y" to avoid issues with .format()
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
                orphan_template.format(
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
                group_template.format(
                    subtask_name,
                    subtask_id,
                    readable_time(due_date),
                    utc_to_local(due_date),
                ),
            )

    return "done"


if __name__ == "__main__":
    main(None, None)
