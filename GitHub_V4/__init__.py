# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License").
# You may not use this file except in compliance with the License.
# A copy of the License is located at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# or in the "license" file accompanying this file. This file is distributed
# on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied. See the License for the specific language governing
# permissions and limitations under the License.

import datetime
import json
import logging
import os
import requests
import time

from .Repo import Repo


class GitHubV4Error(RuntimeError):
    def __init__(self, arg):
        self.args = arg


class GitHub_v4:
    # functions
    def __init__(self, token):
        """
        Contains the graphql query structure for getting information for an org.
        """
        # initialize dependencies
        self.github_v4_url = "https://api.github.com/graphql"
        self.github_v4_cve_headers = {
            "Accept": "application/vnd.github.vixen-preview+json",
            "Authorization": f"token {token}",
        }
        self.github_v4_normal_headers = {"Authorization": f"token {token}"}
        self.sleep_time = 16  # number of seconds to sleep
        self.max_retry_count = 5
        self.repo = Repo()

    def write_structured_json(self, file_name, json_obj):
        file_path = None
        curr_date = datetime.datetime.now().strftime("%Y-%m-%d")
        os.makedirs(f"output/{curr_date}/repo", exist_ok=True)
        file_path = f"output/{curr_date}/repo/{file_name}"
        with open(f"{file_path}", "wt") as f:
            json.dump(json_obj, f, sort_keys=True, indent=2)

    def make_graphql_query(self, query, variables, headers):
        """
        Makes queries to the graphql API and handles pagination
        """
        # ensure you have enough tokens before proceeding
        rate_query = """
          query {
            rateLimit {
              limit
              cost
              remaining
              resetAt
            }
          }
        """
        response = requests.post(
            self.github_v4_url, json={"query": rate_query}, headers=headers
        )
        rate_limit = response.json()
        if rate_limit["data"]["rateLimit"]["remaining"] < 100:
            logging.warn(
                "Not enough tokens to complete request. Waiting until token refresh to proceed."
            )
            # sleep until you have new tokens
            d1 = datetime.datetime.now()
            d2 = datetime.datetime.strptime(
                rate_limit["data"]["rateLimit"]["resetAt"], "%Y-%m-%dT%H-%M-%SZ"
            )
            time.sleep((d2 - d1).seconds + self.sleep_time)

        for count in range(1, self.max_retry_count + 1):
            response = requests.post(
                self.github_v4_url,
                json={"query": query, "variables": variables},
                headers=headers,
            )
            if response.status_code == 200:
                return response.json()
            elif 400 <= response.status_code < 500:
                # client error
                # raise exception
                msg = f"Client error when requesting: {query} {variables} {headers}  and got response: {response}"
                raise GitHubV4Error(msg)
            elif 500 <= response.status_code < 600:
                # server error
                if count == self.max_retry_count + 1:
                    # raise exception as there are no more retries
                    msg = f"Server error when requesting: {query} {variables} {headers}  and got response: {response}"
                    raise GitHubV4Error(msg)
                else:
                    logging.warn(
                        f"Request failed, retrying in {self.sleep_time} seconds. Number of recounts left: {self.max_retry_count - count}"
                    )
                    time.sleep(self.sleep_time)
            else:
                # some other error
                msg = f"Error when requesting: {query} {variables} {headers} and got response: {response}"
                raise GitHubV4Error(msg)

    def write_data_for_org(self, org):
        """
        Get the CVE information for the current org and write them to file
        Returns: Array of file names created
        """
        try:
            repo_list = self.get_org_repo_list(org)
        except GitHubV4Error:
            # log critical error
            msg = f"Failed to get list of repos for org {org}."
            logging.critical(msg)
            return []
        file_list = []
        for repo_info in repo_list:
            logging.info(f"Getting data for {org}/{repo_info['name']}")
            try:
                repo_cve = self.get_data_for_repo(org, repo_info["name"])
            except GitHubV4Error:
                msg = f"Failed to get data for {org}/{repo_info['name']}"
                logging.critical(msg)
                # don't raise, continue to try the next repo
                continue
            currDate = datetime.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
            file_name = f"{org}-{repo_info['name']}-data-{currDate}.json"
            self.write_structured_json(file_name, repo_cve)
            msg = f"Data for {org}/{repo_info['name']} written to {file_name}"
            logging.info(msg)
            file_list.append(file_name)
        return file_list

    def get_data_for_repo(
        self, org, repo, page_info={"endCursor": None, "hasNextPage": False}
    ):
        """
        Get paginated data for a repo
        Returns: 
        """
        query = self.repo.get_repo_info_query()
        variables = {"org_name": org, "repo_name": repo, "first": 100}
        try:
            response = self.make_graphql_query(
                query, variables, self.github_v4_cve_headers
            )
            page_info = response["data"]["organization"]["repository"][
                "vulnerabilityAlerts"
            ]["pageInfo"]
            # handle pagination for graphql
            while page_info["hasNextPage"]:
                # setuip query to get desired data with current cursor
                query = self.repo.get_repo_info_query()
                variables = {
                    "org_name": org,
                    "repo_name": repo,
                    "first": 100,
                    "after": page_info["endCursor"],
                }
                # make a request to the GitHub API
                pages = self.make_graphql_query(
                    query, variables, self.github_v4_cve_headers
                )
                # merge new data with the previous data
                edges = (
                    response["data"]["organization"]["repository"][
                        "vulnerabilityAlerts"
                    ]["edges"]
                    + pages["data"]["organization"]["repository"][
                        "vulnerabilityAlerts"
                    ]["edges"]
                )
                # replace previous data with newer and more complete data
                response["data"]["organization"]["repository"]["vulnerabilityAlerts"][
                    "edges"
                ] = edges
                # update page_info for tracking in the loop
                page_info = pages["data"]["organization"]["repository"][
                    "vulnerabilityAlerts"
                ]["pageInfo"]
            # store final page_info in the request for storage
            response["data"]["organization"]["repository"]["vulnerabilityAlerts"][
                "pageInfo"
            ] = page_info
            # return all paginated data
            return response
        except GitHubV4Error as e:
            # log critical error
            logging.critical(e.args)
            raise

    def get_org_repo_list(self, org_name):
        """
        get list of repos in an org
        Returns: array of repo data in an org and the id for the v4 API
        """
        query = self.repo.get_full_org_repos()
        variables = {"login": org_name, "first": 100}
        try:
            response = self.make_graphql_query(
                query, variables, self.github_v4_normal_headers
            )
            repo_data = response["data"]["organization"]["repositories"]["edges"]
            repo_page_info = response["data"]["organization"]["repositories"][
                "pageInfo"
            ]
            while repo_page_info["hasNextPage"]:
                query = self.repo.get_full_org_repos()
                variables = {
                    "login": org_name,
                    "first": 100,
                    "after": repo_page_info["endCursor"],
                }
                response = self.make_graphql_query(
                    query, variables, self.github_v4_normal_headers
                )
                repo_data += response["data"]["organization"]["repositories"]["edges"]
                repo_page_info = response["data"]["organization"]["repositories"][
                    "pageInfo"
                ]
            repo_list = []
            for repo_info in repo_data:
                repo_list.append(repo_info["node"])
            return repo_list
        except GitHubV4Error as e:
            # log critical error
            logging.critical(e.args)
            # this is critical so raise it up
            raise
