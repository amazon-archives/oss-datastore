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

import boto3
import datetime
import json
import logging
import os
import requests
import time


class GitHubV3Error(RuntimeError):
    def __init__(self, arg):
        self.args = arg


class GitHub_v3:
    # functions
    def __init__(self, token):
        """
        Uses the v3 GitHub API to get traffic and repo files.
        """
        self.github_v3_url = "https://api.github.com"
        self.github_v3_normal_headers = {"Authorization": None}
        self.github_v3_normal_headers["Authorization"] = f"token {token}"
        self.sleep_time = 16  # number of seconds to sleep
        self.max_retry_count = 5

    def write_structured_json(self, file_name, json_obj):
        """
        Writes json blob (json_obj) to a file at file_name
        """
        curr_date = datetime.datetime.now().strftime("%Y-%m-%d")
        os.makedirs(f"output/{curr_date}/traffic", exist_ok=True)
        with open(f"output/{curr_date}/traffic/{file_name}", "wt") as f:
            json.dump(json_obj, f, sort_keys=True, indent=2)

    def github_v3_run_query(self, query, headers=None):
        """
        Make a query to the v3 GitHub API.
        Returns: Paginated responses or an empty array.
        """
        for count in range(1, self.max_retry_count + 1):
            if headers is None:
                headers = self.github_v3_normal_headers
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
                # these status codes return no content so return empty array
                return []
            elif "link" not in response.headers:
                # nothing to paginate and not empty body, return body json data
                return response.json()
            elif 400 <= response.status_code < 500:
                # client error
                # raise exception
                msg = f"Client error when requesting: {query} and got response: {response}"
                raise GitHubV3Error(msg)
            elif 500 <= response.status_code < 600:
                # server error
                if count == self.max_retry_count + 1:
                    # retry hit max count and failed so except
                    msg = f"Server error when requesting: {query} and got response: {response}"
                    raise GitHubV3Error(msg)
                else:
                    # sleep and retry again as it might just be a transient issue
                    logging.warn(
                        f"Request failed due to API issues, retrying in {self.sleep_time} seconds. Number of recounts left: {self.max_retry_count - count}"
                    )
                    time.sleep(self.sleep_time)

    def github_pagination_setup(self, link_header):
        """
        Gathers pagination information
        Returns: Tuple of total number of pages (page_count) and URL to use
                 for pagination (clean_link)
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
        Returns: JSON object of the rate limits.
                 See https://developer.github.com/v3/rate_limit/
        """
        return self.github_v3_run_query("/rate_limit")

    def write_org_traffic(self, org, run_lambda=False):
        """
        Get the orgs repo traffic and write them to their respective locations.
        Returns: array of file names created
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
        repo_list = self.get_repos(org)
        repo_files = []
        for repo_info in repo_list:
            repo_name = repo_info["name"]
            if run_lambda is False:
                file_name = self.write_repo_traffic_to_disk(org, repo_name)
                repo_files.append(file_name)
            else:
                self.write_repo_traffic_to_s3(org, repo_name)
        return repo_files

    def write_repo_traffic_to_disk(self, org, repo):
        """
        Write repo traffic to disk
        Returns: file name of json written to disk
        """
        repo_info = self.get_repo_traffic(org, repo)
        curr_date = datetime.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        file_name = f"{org}-{repo}-traffic-{curr_date}.json"
        self.write_structured_json(file_name, repo_info)
        logging.info(f"Traffic and stats for {org}/{repo} written to file {file_name}")
        return file_name

    def write_repo_traffic_to_s3(self, org, repo):
        """
        Write repo traffic to S3

        Note: Use print here as logging doesn't appear in CloudWatch output
        """
        print(f"Starting processing of {org}/{repo}")
        # setup for storing in S3
        s3 = boto3.resource("s3")
        bucket_name = (
            "oss-datastore-staging"
        )  # TODO: convert to config file linked to .env
        bucket = s3.Bucket(bucket_name)
        try:
            # now get repo info
            repo_traffic = self.get_repo_traffic(org, repo, lambda_active=True)
        except GitHubV3Error:
            raise
        curr_date_full = datetime.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        curr_date = datetime.datetime.now().strftime("%Y-%m-%d")
        file_path_and_name = (
            f"{curr_date}/traffic/{org}-{repo}-traffic-{curr_date_full}.json"
        )
        # write directly to S3
        bucket.put_object(
            Body=json.dumps(repo_traffic), Bucket=bucket_name, Key=file_path_and_name
        )
        print(f"Processing of {org}/{repo} complete.")

    def get_repo_traffic(self, org, repo, lambda_active=False):
        """
        Get repo traffic info (referrers, paths, views, clones) for a repo.
        Returns: JSON object of traffic data

        Note: These sometimes fail the first request but there is no pagination.
              That being said, the retry takes care of getting the data since it
              seems that the API just needs a kick on that first request as
              the second request is almost always successful.
        """
        logging.info(f"Getting traffic and stats for {org}/{repo}")
        # traffic info found https://developer.github.com/v3/repos/traffic/
        repo_info = {}
        try:
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
            repo_info["stats"]["code_frequency"] = self.get_stats_code_frequency(
                org, repo
            )
            repo_info["stats"]["participation"] = self.get_stats_participation(
                org, repo
            )
            repo_info["stats"]["punch_card"] = self.get_stats_punch_card(org, repo)

            return repo_info
        except GitHubV3Error as e:
            # log critical error
            logging.critical(e.args)
            if lambda_active is True:
                raise
            # not going to raise we need it to move onto the next repo

    def get_repos(self, org):
        return self.github_v3_run_query(f"/orgs/{org}/repos")

    def get_files(self, org, repo):
        return self.github_v3_run_query(f"/repos/{org}/{repo}/contents")

    def get_referrers(self, org, repo):
        return self.github_v3_run_query(
            f"/repos/{org}/{repo}/traffic/popular/referrers"
        )

    def get_paths(self, org, repo):
        return self.github_v3_run_query(f"/repos/{org}/{repo}/traffic/popular/paths")

    def get_views(self, org, repo):
        return self.github_v3_run_query(f"/repos/{org}/{repo}/traffic/views")

    def get_clones(self, org, repo):
        return self.github_v3_run_query(f"/repos/{org}/{repo}/traffic/clones")

    def get_stats_contributors(self, org, repo):
        return self.github_v3_run_query(f"/repos/{org}/{repo}/stats/contributors")

    def get_stats_common_activity(self, org, repo):
        return self.github_v3_run_query(f"/repos/{org}/{repo}/stats/commit_activity")

    def get_stats_code_frequency(self, org, repo):
        return self.github_v3_run_query(f"/repos/{org}/{repo}/stats/code_frequency")

    def get_stats_participation(self, org, repo):
        return self.github_v3_run_query(f"/repos/{org}/{repo}/stats/participation")

    def get_stats_punch_card(self, org, repo):
        return self.github_v3_run_query(f"/repos/{org}/{repo}/stats/punch_card")
