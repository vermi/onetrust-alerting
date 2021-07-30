"""
A library encapsulating some functions from the undocumented OneTrust API.

Probably not for general use. See function docstrings for more info.
"""

import json
import urllib

import requests


class OneTrustSession:
    def __init__(self, access_token, cookies, instance_url) -> None:
        self.access_token = access_token
        self.cookies = cookies
        self.instance_url = instance_url

    def get_overdue_subtasks(self, cutoff_date) -> requests.models.Response:
        """
        Requests a list of subtasks that have a due date prior to the specified cutoff.

        Args:
            cuttof_date (str): The cutoff date in UNIX-style UTC time string.

        Returns:
            Response: An HTTP Response object from python requests.
        """
        api = "/api/datasubject/v1/subtask/search/en-us?page=0&size=20&sort=deadline,asc&viewId=undefined"

        headers = {
            "Authorization": "Bearer " + self.access_token,
            "Content-Type": "application/json",
        }
        s = requests.session()
        s.headers.update(headers)
        s.cookies.update({c["name"]: c["value"] for c in self.cookies})
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
                    "fromValue": cutoff_date,
                },
            ],
        }

        return s.post(self.instance_url + api, data=json.dumps(data))

    def get_group_id(self, group_name) -> str:
        """
        Retrieves the ID of the specified group.

        Args:
            group_name (str): The name of the group to retrieve.

        Returns:
            str: the group ID.
        """
        parsed_group = urllib.parse.quote_plus("%" + group_name + "%")
        api = "/api/access/v1/groups?filters=name=~={0}&page=0&size=20".format(
            parsed_group
        )

        headers = {
            "Authorization": "Bearer " + self.access_token,
        }
        s = requests.session()
        s.headers.update(headers)
        s.cookies.update({c["name"]: c["value"] for c in self.cookies})

        r = s.get(self.instance_url + api)

        return r.json()["content"][0]["id"]

    def get_group_email(self, group_id) -> list:
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

        headers = {
            "Authorization": "Bearer " + self.access_token,
        }
        s = requests.session()
        s.headers.update(headers)
        s.cookies.update({c["name"]: c["value"] for c in self.cookies})

        r = s.get(self.instance_url + api)

        emails = []
        for user in r.json()["content"]:
            emails.append(user["email"])

        return emails
