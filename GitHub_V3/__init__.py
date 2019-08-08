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


class GitHub_v3:
    # functions
    def __init__(self, token, db_handle):
        """
        Uses the v3 GitHub API to get traffic and repo files.
        """
        self.github_v3_url = "https://api.github.com"
        self.github_v3_normal_headers = {"Authorization": None}
        self.github_v3_normal_headers["Authorization"] = f"token {token}"
        self.db = db_handle
        self.sleep_time = 16  # number of seconds to sleep
        self.max_retry_count = 5

    def write_structured_json(self, file_name, json_obj):
        curr_date = datetime.datetime.now().strftime("%Y-%m-%d")
        os.makedirs(f"output/{curr_date}/traffic", exist_ok=True)
        with open(f"output/{curr_date}/traffic/{file_name}", "wt") as f:
            json.dump(json_obj, f, sort_keys=True, indent=2)

    def github_v3_get_query(self, query, headers):
        """
        Making raw calls because python doesn't have a very good octokit client
        """
        for count in range(1, self.max_retry_count + 1):
            response = requests.get(self.github_v3_url + query, headers=headers)
            if "link" in response.headers:
                # handle pagination
                page_count, clean_link = self.github_pagination_setup(
                    response.headers["link"]
                )
                new_body = response.json()
                for step in range(2, page_count + 1):
                    response = requests.get(clean_link + str(step), headers=headers)
                    if 200 <= response.status_code < 300:
                        new_body = new_body + response.json()
                    else:
                        logging.warn(
                            f"Request failed, retrying in {self.sleep_time} seconds. Number of recounts left: {self.max_retry_count - count}"
                        )
                        time.sleep(self.sleep_time)
                return new_body
            elif response.status_code == 202 or response.status_code == 204:
                # these two status codes return no content so return empty array
                return []
            else:
                return response.json()

        # retry failed, log in DLQ
        self.db.insert(
            "dead_letter_queue",
            source="github_v3",
            query=query,
            request_time=datetime.datetime.now(),
            response={
                "body": response.text,
                "headers": headers,
                "status_code": response.status_code,
            },
        )

    def github_pagination_setup(self, link_header):
        """
        Gathers pagination information
        """
        links = link_header.split(",")
        start = links[1].index("<")
        end = links[1].index(">")
        last_link = links[1][start + 1 : end]
        clean_link, page_count = last_link.split("=")
        # re-add '=' to link
        clean_link = clean_link + "="
        # convert page_count to int
        page_count = int(page_count)
        return page_count, clean_link

    def get_api_rate_limit(self):
        """
        Get rate limit from v3 API
        """
        return self.github_v3_get_query("/rate_limit", self.github_v3_normal_headers)

    def get_org_traffic(self, org):
        """
        Get the orgs repo traffic.
        """
        rate_limit = self.get_api_rate_limit()
        if rate_limit["rate"]["remaining"] < 100:
            logging.warn(
                "Not enough tokens to complete request. Waiting until token refresh to proceed."
            )
            # sleep until you have new tokens
            d1 = datetime.datetime.now()
            d2 = datetime.datetime.fromtimestamp(rate_limit["rate"]["reset"])
            time.sleep((d2 - d1).seconds + self.sleep_time)
        repo_list = self.get_repo(org)
        for repo_info in repo_list:
            self.get_repo_traffic(org, repo_info["name"])

    def get_repo_traffic(self, org, repo):
        """
        Get the traffic info (referrers, paths, views, clones) for a repo and write to file

        Note: These sometimes fail the first request but there is no pagination.
              That being said, the retry takes care of getting the data since it
              seems that the API just needs a kick on that first request sionce
              the second is almost always successful.
        """
        logging.info(f"Getting traffic and stats for {org}/{repo}")
        # traffic info found https://developer.github.com/v3/repos/traffic/
        repo_info = {}
        repo_info["repo_file_names"] = self.get_files(org, repo)
        repo_info["referrers"] = self.get_referrers(org, repo)
        repo_info["paths"] = self.get_paths(org, repo)
        repo_info["views"] = self.get_views(org, repo)
        repo_info["clones"] = self.get_clones(org, repo)
        # stats info found https://developer.github.com/v3/repos/statistics/
        repo_info["stats"] = {}
        repo_info["stats"]["contributors"] = self.get_stats_contributors(org, repo)
        repo_info["stats"]["comment_activity"] = self.get_stats_common_activity(
            org, repo
        )
        repo_info["stats"]["code_frequency"] = self.get_stats_code_frequency(org, repo)
        repo_info["stats"]["participation"] = self.get_stats_participation(org, repo)
        repo_info["stats"]["punch_card"] = self.get_stats_punch_card(org, repo)

        currDate = datetime.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        file_name = f"{org}-{repo}-traffic-{currDate}.json"
        self.write_structured_json(file_name, repo_info)
        logging.info(f"Traffic and stats for {org}/{repo} written to file {file_name}")

    def get_repo(self, org):
        return self.github_v3_get_query(
            f"/orgs/{org}/repos", self.github_v3_normal_headers
        )

    def get_files(self, org, repo):
        return self.github_v3_get_query(
            f"/repos/{org}/{repo}/contents", self.github_v3_normal_headers
        )

    def get_referrers(self, org, repo):
        return self.github_v3_get_query(
            f"/repos/{org}/{repo}/traffic/popular/referrers",
            self.github_v3_normal_headers,
        )

    def get_paths(self, org, repo):
        return self.github_v3_get_query(
            f"/repos/{org}/{repo}/traffic/popular/paths", self.github_v3_normal_headers
        )

    def get_views(self, org, repo):
        return self.github_v3_get_query(
            f"/repos/{org}/{repo}/traffic/views", self.github_v3_normal_headers
        )

    def get_clones(self, org, repo):
        return self.github_v3_get_query(
            f"/repos/{org}/{repo}/traffic/clones", self.github_v3_normal_headers
        )

    def get_stats_contributors(self, org, repo):
        return self.github_v3_get_query(
            f"/repos/{org}/{repo}/stats/contributors", self.github_v3_normal_headers
        )

    def get_stats_common_activity(self, org, repo):
        return self.github_v3_get_query(
            f"/repos/{org}/{repo}/stats/commit_activity", self.github_v3_normal_headers
        )

    def get_stats_code_frequency(self, org, repo):
        return self.github_v3_get_query(
            f"/repos/{org}/{repo}/stats/code_frequency", self.github_v3_normal_headers
        )

    def get_stats_participation(self, org, repo):
        return self.github_v3_get_query(
            f"/repos/{org}/{repo}/stats/participation", self.github_v3_normal_headers
        )

    def get_stats_punch_card(self, org, repo):
        return self.github_v3_get_query(
            f"/repos/{org}/{repo}/stats/punch_card", self.github_v3_normal_headers
        )
