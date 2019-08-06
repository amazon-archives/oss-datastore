import boto3
import datetime
import json
import logging
import os
import requests
import time

from pg import DB

from .CVE import CVE
from .Repo import Repo
from .User import User


class GitHub_v4:
    cve = None
    repo = None
    user = None
    db = None
    github_v4_url = "https://api.github.com/graphql"
    github_v4_cve_headers = {
        "Accept": "application/vnd.github.vixen-preview+json",
        "Authorization": None,
    }
    github_v4_normal_headers = {"Authorization": None}
    sleep_time = 16  # number of seconds to sleep
    max_retry_count = 5

    # functions
    def __init__(self, token, db_handle):
        """
        Contains the graphql query structure for getting CVE information for an org.
        """
        # initialize headers
        self.github_v4_cve_headers["Authorization"] = f"token {token}"
        self.github_v4_normal_headers["Authorization"] = f"token {token}"
        # initialize dependencies
        self.cve = CVE()
        self.repo = Repo()
        self.user = User()
        self.db = db_handle

    def write_structured_json(self, file_name, json_obj, file_type):
        file_path = None
        if file_type == "repo":
            os.makedirs("output/repo", exist_ok=True)
            file_path = "output/repo/{}"
        elif file_type == "cve":
            if not os.path.exists("output/cve"):
                os.makedirs("output/cve")
        with open(f"output/cve/{file_name}", "wt") as f:
            json.dump(json_obj, f, sort_keys=True, indent=2)

    def make_graphql_query(self, query, headers):
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
                rate_limit["data"]["rateLimit"]["resetAt"], "%Y-%m-%dT%H:%M:%SZ"
            )
            time.sleep((d2 - d1).seconds + self.sleep_time)

        for count in range(1, self.max_retry_count + 1):
            response = requests.post(
                self.github_v4_url, json={"query": query}, headers=headers
            )
            if response.status_code == 200:
                return response.json()
            else:
                logging.warn(
                    f"Request failed, retrying in {self.sleep_time} seconds. Number of recounts left: {self.max_retry_count - count}"
                )
                time.sleep(self.sleep_time)
        # retry failed, log in DLQ
        self.db.insert(
            "dead_letter_queue",
            source="github_v4",
            query=query,
            request_time=datetime.datetime.now(),
            response={
                "body": response.text,
                "headers": headers,
                "status_code": response.status_code,
            },
        )

    def get_cves_for_org(self, org):
        """
        Get the CVE information for the current org
        """
        query = self.cve.get_full_org_cve_info_query(org)
        request = self.make_graphql_query(query, self.github_v4_cve_headers)
        repo_page_info = request["data"]["organization"]["repositories"]["pageInfo"]
        while repo_page_info["hasNextPage"]:
            query = self.cve.get_full_org_cve_info_query(
                org, repo_page_info["endCursor"]
            )
            pages = self.make_graphql_query(query, self.github_v4_cve_headers)
            edges = (
                request["data"]["organization"]["repositories"]["edges"]
                + pages["data"]["organization"]["repositories"]["edges"]
            )
            request["data"]["organization"]["repositories"]["edges"] = edges
            repo_page_info = pages["data"]["organization"]["repositories"]["pageInfo"]

        # remove repos with no CVE and grab additional CVE info if needed
        repos_with_cve = []
        for repo in request["data"]["organization"]["repositories"]["edges"]:
            if len(repo["node"]["vulnerabilityAlerts"]["edges"]) > 0:
                cve_page_info = repo["node"]["vulnerabilityAlerts"]["pageInfo"]
                while cve_page_info["hasNextPage"]:
                    # repo has more than the 100 listed CVEs so grab all
                    edges = repo["node"]["vulnerabilityAlerts"]["edges"]
                    extra_CVE = self.get_cve_for_repo(
                        org, repo["node"]["name"], cve_page_info
                    )
                    repo["node"]["vulnerabilityAlerts"]["edges"] = (
                        edges
                        + extra_CVE["data"]["organization"]["repository"][
                            "vulnerabilityAlerts"
                        ]["edges"]
                    )

                repos_with_cve.append(repo)
                currDate = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                self.write_structured_json(
                    f"{org}-{repo}-CVE-{currDate}.json", repo, "cve"
                )
        request["data"]["organization"]["repositories"]["edges"] = repos_with_cve
        return request

    def get_cve_for_repo(
        self, org, repo, cve_page_info={"endCursor": None, "hasNextPage": False}
    ):
        """
        Get CVEs for a repo and or continue getting them
        """
        query = self.cve.get_repo_cve_info_query(org, repo)
        request = self.make_graphql_query(query, self.github_v4_cve_headers)
        cve_page_info = request["data"]["organization"]["repository"][
            "vulnerabilityAlerts"
        ]["pageInfo"]
        while cve_page_info["hasNextPage"]:
            # play some cup and ball to get everything
            query = self.cve.get_repo_cve_info_query(
                org, repo, cve_page_info["endCursor"]
            )
            pages = self.make_graphql_query(query, self.github_v4_cve_headers)
            edges = (
                request["data"]["organization"]["repository"]["vulnerabilityAlerts"][
                    "edges"
                ]
                + pages["data"]["organization"]["repository"]["vulnerabilityAlerts"][
                    "edges"
                ]
            )
            request["data"]["organization"]["repository"]["vulnerabilityAlerts"][
                "edges"
            ] = edges
            cve_page_info = pages["data"]["organization"]["repository"][
                "vulnerabilityAlerts"
            ]["pageInfo"]
        request["data"]["organization"]["repository"]["vulnerabilityAlerts"][
            "pageInfo"
        ] = cve_page_info
        return request

    def get_org_repo_list(self, org_name):
        """
        Returns an array of repo data in an org and the id for the v4 API
        """
        query = self.repo.get_full_org_repos(org_name)
        request = self.make_graphql_query(query, self.github_v4_normal_headers)
        repo_data = request["data"]["organization"]["repositories"]["edges"]
        repo_page_info = request["data"]["organization"]["repositories"]["pageInfo"]
        while repo_page_info["hasNextPage"]:
            query = self.repo.get_full_org_repos(org_name, repo_page_info["endCursor"])
            request = self.make_graphql_query(query, self.github_v4_normal_headers)
            repo_data += request["data"]["organization"]["repositories"]["edges"]
            repo_page_info = request["data"]["organization"]["repositories"]["pageInfo"]
        repo_list = []
        for repo_info in repo_data:
            repo_list.append(repo_info["node"])
        return repo_list

    def get_org_all_repo_details(self, org, repo):
        """
        Pull all the data for a repos in an org
        Writes the timestamped data to an output directory
        """
        currDate = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        self.write_structured_json(
            f"{org}-{repo}-{currDate}.json", self.get_full_repo(org, repo), "repo"
        )

    def get_full_repo(self, org, repo):
        """
        Gets all the information for a specific repo
        """
        # TODO: figure out how to request on the new information without using events
        logging.info(f"Requesting base info for {org}/{repo}")
        query = self.repo.get_single_repo_base(
            org, repo, self.repo.get_repo_base_info()
        )
        request = self.make_graphql_query(query, self.github_v4_normal_headers)
        repo_info = request

        if (repo_info["data"]["organization"] is not None) and (
            repo_info["data"]["organization"]["repository"] is not None
        ):
            # gather additional assignable_users
            assignable_users = repo_info["data"]["organization"]["repository"][
                "assignableUsers"
            ]
            if assignable_users is not None:
                repo_info["data"]["organization"]["repository"][
                    "assignableUsers"
                ] = self.paginate_assignable_users(org, repo, assignable_users)

            # gather additional branch_protection_rules
            branch_protection_rules = repo_info["data"]["organization"]["repository"][
                "branchProtectionRules"
            ]
            if branch_protection_rules is not None:
                repo_info["data"]["organization"]["repository"][
                    "branchProtectionRules"
                ] = self.paginate_branch_protection_rules(
                    org, repo, branch_protection_rules
                )

            # gather additional collaborators
            collaborators = repo_info["data"]["organization"]["repository"][
                "collaborators"
            ]
            if collaborators is not None:
                repo_info["data"]["organization"]["repository"][
                    "collaborators"
                ] = self.paginate_collaborators(org, repo, collaborators)

            # gather additional issues
            issues = repo_info["data"]["organization"]["repository"]["issues"]
            if issues is not None:
                repo_info["data"]["organization"]["repository"][
                    "issues"
                ] = self.paginate_issues(org, repo, issues)

            # gather additional labels
            labels = repo_info["data"]["organization"]["repository"]["labels"]
            if labels is not None:
                repo_info["data"]["organization"]["repository"][
                    "labels"
                ] = self.paginate_labels(org, repo, labels)

            # gather additional languages
            languages = repo_info["data"]["organization"]["repository"]["languages"]
            if languages is not None:
                repo_info["data"]["organization"]["repository"][
                    "languages"
                ] = self.paginate_languages(org, repo, languages)

            # gather additional milestones
            milestones = repo_info["data"]["organization"]["repository"]["milestones"]
            if milestones is not None:
                repo_info["data"]["organization"]["repository"][
                    "milestones"
                ] = self.paginate_milestones(org, repo, milestones)

            # gather additional projects
            projects = repo_info["data"]["organization"]["repository"]["projects"]
            if projects is not None:
                repo_info["data"]["organization"]["repository"][
                    "projects"
                ] = self.paginate_projects(org, repo, projects)

            # gather pull_requests
            # v4 API still buggy on pull requests and waiting for info from GitHub

            # gather additional releases
            releases = repo_info["data"]["organization"]["repository"]["releases"]
            if releases is not None:
                repo_info["data"]["organization"]["repository"][
                    "releases"
                ] = self.paginate_releases(org, repo, releases)

            # gather additional repository_topics
            repository_topics = repo_info["data"]["organization"]["repository"][
                "repositoryTopics"
            ]
            if repository_topics is not None:
                repo_info["data"]["organization"]["repository"][
                    "repositoryTopics"
                ] = self.paginate_repository_topics(org, repo, repository_topics)

        return repo_info

    def get_user_orgs(self, user):
        """
        Returns array of orgs that a user has access.
        """
        query = self.user.get_user_orgs(user)
        request = self.make_graphql_query(query, self.github_v4_normal_headers)
        user_page_info = request["data"]["user"]["organizations"]["pageInfo"]
        org_list = request["data"]["user"]["organizations"]["edges"]
        while user_page_info["hasNextPage"]:
            query = self.user.get_user_orgs(user, user_page_info["endCursor"])
            request = self.make_graphql_query(query, self.github_v4_normal_headers)
            org_list += request["data"]["user"]["organizations"]["edges"]
            user_page_info = request["data"]["user"]["organizations"]["pageInfo"]
        return org_list

    # pagination fuctions for specific data
    def paginate_assignable_users(self, org, repo, assignable_users):
        """
        Returns an object of edges and pageInfo of assignable users
        """
        while assignable_users["pageInfo"]["hasNextPage"]:
            query = self.repo.get_single_repo_base(
                org,
                repo,
                self.repo.part_users_min(
                    "assignableUsers", assignable_users["pageInfo"]["endCursor"]
                ),
            )
            request = self.make_graphql_query(query, self.github_v4_cve_headers)
            edges = (
                assignable_users["edges"]
                + request["data"]["organization"]["repository"]["assignableUsers"][
                    "edges"
                ]
            )
            assignable_users["edges"] = edges
            assignable_users["pageInfo"] = request["data"]["organization"][
                "repository"
            ]["assignableUsers"]["pageInfo"]
        return assignable_users

    def paginate_branch_protection_rules(self, org, repo, branch_protection_rules):
        """
        Returns an object of edges and pageInfo of assignable users
        """
        while branch_protection_rules["pageInfo"]["hasNextPage"]:
            query = self.repo.get_single_repo_base(
                org,
                repo,
                self.repo.part_repo_branch_protection_rules(
                    branch_protection_rules["pageInfo"]["endCursor"]
                ),
            )
            request = self.make_graphql_query(query, self.github_v4_cve_headers)
            edges = (
                branch_protection_rules["edges"]
                + request["data"]["organization"]["repository"][
                    "branchProtectionRules"
                ]["edges"]
            )
            branch_protection_rules["edges"] = edges
            branch_protection_rules["pageInfo"] = request["data"]["organization"][
                "repository"
            ]["branchProtectionRules"]["pageInfo"]
        return branch_protection_rules

    def paginate_collaborators(self, org, repo, collaborators):
        """
        Returns an object of edges and pageInfo of collaborators
        """
        while collaborators["pageInfo"]["hasNextPage"]:
            query = self.repo.get_single_repo_base(
                org,
                repo,
                self.repo.part_users_min(
                    "collaborators", collaborators["pageInfo"]["endCursor"]
                ),
            )
            request = self.make_graphql_query(query, self.github_v4_cve_headers)
            edges = (
                collaborators["edges"]
                + request["data"]["organization"]["repository"]["collaborators"][
                    "edges"
                ]
            )
            collaborators["edges"] = edges
            collaborators["pageInfo"] = request["data"]["organization"]["repository"][
                "collaborators"
            ]["pageInfo"]
        return collaborators

    def paginate_issues(self, org, repo, issues):
        """
        Returns an object of edges and pageInfo of issues
        """
        while issues["pageInfo"]["hasNextPage"]:
            query = self.repo.get_single_repo_base(
                org, repo, self.repo.part_issues(issues["pageInfo"]["endCursor"])
            )
            request = self.make_graphql_query(query, self.github_v4_cve_headers)
            edges = (
                issues["edges"]
                + request["data"]["organization"]["repository"]["issues"]["edges"]
            )
            issues["edges"] = edges
            issues["pageInfo"] = request["data"]["organization"]["repository"][
                "issues"
            ]["pageInfo"]
        return issues

    def paginate_labels(self, org, repo, labels):
        """
        Returns an object of edges and pageInfo of labels
        """
        while labels["pageInfo"]["hasNextPage"]:
            query = self.repo.get_single_repo_base(
                org,
                repo,
                self.repo.part_label("labels", labels["pageInfo"]["endCursor"]),
            )
            request = self.make_graphql_query(query, self.github_v4_cve_headers)
            edges = (
                labels["edges"]
                + request["data"]["organization"]["repository"]["labels"]["edges"]
            )
            labels["edges"] = edges
            labels["pageInfo"] = request["data"]["organization"]["repository"][
                "labels"
            ]["pageInfo"]
        return labels

    def paginate_languages(self, org, repo, languages):
        """
        Returns an object of edges and pageInfo of languages
        """
        while languages["pageInfo"]["hasNextPage"]:
            query = self.repo.get_single_repo_base(
                org, repo, self.repo.part_languages(languages["pageInfo"]["endCursor"])
            )
            request = self.make_graphql_query(query, self.github_v4_cve_headers)
            edges = (
                languages["edges"]
                + request["data"]["organization"]["repository"]["languages"]["edges"]
            )
            languages["edges"] = edges
            languages["pageInfo"] = request["data"]["organization"]["repository"][
                "languages"
            ]["pageInfo"]
        return languages

    def paginate_milestones(self, org, repo, milestones):
        """
        Returns an object of edges and pageInfo of milestones
        """
        while milestones["pageInfo"]["hasNextPage"]:
            query = self.repo.get_single_repo_base(
                org,
                repo,
                self.repo.part_milestones(milestones["pageInfo"]["endCursor"]),
            )
            request = self.make_graphql_query(query, self.github_v4_cve_headers)
            edges = (
                milestones["edges"]
                + request["data"]["organization"]["repository"]["milestones"]["edges"]
            )
            milestones["edges"] = edges
            milestones["pageInfo"] = request["data"]["organization"]["repository"][
                "milestones"
            ]["pageInfo"]
        return milestones

    def paginate_projects(self, org, repo, projects):
        """
        Returns an object of edges and pageInfo of projects
        """
        while projects["pageInfo"]["hasNextPage"]:
            query = self.repo.get_single_repo_base(
                org, repo, self.repo.part_projects(projects["pageInfo"]["endCursor"])
            )
            request = self.make_graphql_query(query, self.github_v4_cve_headers)
            edges = (
                projects["edges"]
                + request["data"]["organization"]["repository"]["projects"]["edges"]
            )
            projects["edges"] = edges
            projects["pageInfo"] = request["data"]["organization"]["repository"][
                "projects"
            ]["pageInfo"]
        return projects

    def paginate_pull_requests(self, org, repo):
        """
        Returns an object of edges and pageInfo of pull_requests
        """
        # TODO: waiting for GitHub info why this fails on their end
        query = self.repo.get_single_repo_base(
            org, repo, self.repo.part_pull_requests()
        )
        request = self.make_graphql_query(query, self.github_v4_cve_headers)
        pull_requests = request["data"]["organization"]["repository"]["pullRequests"]
        while pull_requests["pageInfo"]["hasNextPage"]:
            query = self.repo.get_single_repo_base(
                org,
                repo,
                self.repo.part_pull_requests(pull_requests["pageInfo"]["endCursor"]),
            )
            request = self.make_graphql_query(query, self.github_v4_cve_headers)
            edges = (
                pull_requests["edges"]
                + request["data"]["organization"]["repository"]["pullRequests"]["edges"]
            )
            pull_requests["edges"] = edges
            pull_requests["pageInfo"] = request["data"]["organization"]["repository"][
                "pullRequests"
            ]["pageInfo"]
        return pull_requests

    def paginate_releases(self, org, repo, releases):
        """
        Returns an object of edges and pageInfo of releases
        """
        while releases["pageInfo"]["hasNextPage"]:
            query = self.repo.get_single_repo_base(
                org, repo, self.repo.part_releases(releases["pageInfo"]["endCursor"])
            )
            request = self.make_graphql_query(query, self.github_v4_cve_headers)
            edges = (
                releases["edges"]
                + request["data"]["organization"]["repository"]["releases"]["edges"]
            )
            releases["edges"] = edges
            releases["pageInfo"] = request["data"]["organization"]["repository"][
                "releases"
            ]["pageInfo"]
        return releases

    def paginate_repository_topics(self, org, repo, repository_topics):
        """
        Returns an object of edges and pageInfo of repository_topics
        """
        while repository_topics["pageInfo"]["hasNextPage"]:
            query = self.repo.get_single_repo_base(
                org,
                repo,
                self.repo.part_repository_topics(
                    repository_topics["pageInfo"]["endCursor"]
                ),
            )
            request = self.make_graphql_query(query, self.github_v4_cve_headers)
            edges = (
                repository_topics["edges"]
                + request["data"]["organization"]["repository"]["repositoryTopics"][
                    "edges"
                ]
            )
            repository_topics["edges"] = edges
            repository_topics["pageInfo"] = request["data"]["organization"][
                "repository"
            ]["repositoryTopics"]["pageInfo"]
        return repository_topics
