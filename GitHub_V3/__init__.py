import datetime
import json
import logging
import os
import requests
import time

from pg import DB


class GitHub_v3:
    github_v3_url = "https://api.github.com"
    github_v3_normal_headers = {"Authorization": None}
    db = None

    sleep_time = 16  # number of seconds to sleep
    max_retry_count = 5

    # functions
    def __init__(self, token, db_handle):
        """
      Contains the graphql query structure for getting CVE information for an org.
    """
        self.github_v3_normal_headers["Authorization"] = f"token {token}"
        self.db = db_handle

    def write_structured_json(self, file_name, json_obj):
        os.makedirs("output/traffic", exist_ok=True)
        with open(f"output/traffic/{file_name}", "wt") as f:
            json.dump(json_obj, f, sort_keys=True, indent=2)

    def github_v3_get_query(self, query, headers):
        """
      Making raw calls because python doesn't have a very good octokit client
    """
        for count in range(1, self.max_retry_count + 1):
            request = requests.get(self.github_v3_url + query, headers=headers)
            if request.status_code == 200:
                return request.json()
            elif (
                request.status_code == 202 or request.status_code == 204
            ):  # repo exists but doesn't have any traffic info
                return {"error": "No content returned."}
            else:
                logging.warn(
                    f"Request failed, retrying in {self.sleep_time} seconds. Number of recounts left: {self.max_retry_count - count}"
                )
                time.sleep(self.sleep_time)
        # retry failed, log in DLQ
        self.db.insert(
            "dead_letter_queue",
            source="github_v3",
            query=query,
            request_time=datetime.datetime.now(),
            response={
                "body": request.text,
                "headers": headers,
                "status_code": request.status_code,
            },
        )

    def get_api_rate_limit(self):
        """
      Get rate limit from v3 API
    """
        return self.github_v3_get_query("/rate_limit", self.github_v3_normal_headers)

    def get_repo_traffic(self, org, repo):
        """
      Get the traffic info (referrers, paths, views, clones) for a repo and write to file

      Note: These sometimes fail the first request but there is no pagination.
            That being said, the retry takes care of getting the data since it
            seems that the API just needs a kick on that first request sionce
            the second is almost always successful.
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
        logging.info(f"Getting traffic and stats for {org}/{repo}")
        # traffic info found https://developer.github.com/v3/repos/traffic/
        repo_info = {}
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

        currDate = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        self.write_structured_json(f"{org}-{repo}-traffic-{currDate}.json", repo_info)
        logging.info(f"Traffic and stats for {org}/{repo} written to file")

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
