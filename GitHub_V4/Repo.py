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


class Repo:
    def __init__(self):
        """
      Contains the graphql query structure for getting all repo information
      for an org.
      """

    def get_full_org_repos(self):
        query = f"""
            query($login: String!, $first: Int!, $after: String) {{
              organization(login: $login) {{
                repositories(first: $first after: $after) {{
                  edges {{
                    cursor
                    node {{
                      id
                      name
                      nameWithOwner
                    }}
                  }}
                  pageInfo {{
                    endCursor
                    hasNextPage
                  }}
                  totalCount
                }}
              }}
            }}
          """
        return query

    def get_repo_info_query(self):
        query = f"""
            query($org_name: String!, $repo_name: String!, $first: Int!, $after: String) {{
              organization(login: $org_name) {{
                repository(name: $repo_name) {{
                  forks(first: 100) {{
                    totalCount
                  }}
                  issues(first: 100) {{
                    totalCount
                  }}
                  name
                  nameWithOwner
                  pullRequests(first: 100) {{
                    totalCount
                  }}
                  stargazers (first: 100) {{
                    totalCount
                  }}
                  vulnerabilityAlerts (first: $first after: $after) {{
                    edges {{
                      node {{
                        dismissReason
                        dismissedAt
                        id
                        securityVulnerability {{
                          advisory {{
                            description
                            id
                            publishedAt
                            severity
                            summary
                          }}
                          firstPatchedVersion {{
                            identifier
                          }}
                          package {{
                            ecosystem
                            name
                          }}
                          severity
                          updatedAt
                          vulnerableVersionRange
                        }}
                        vulnerableManifestFilename
                        vulnerableManifestPath
                        vulnerableRequirements
                      }}
                      cursor
                    }}
                    pageInfo {{
                      endCursor
                      hasNextPage
                    }}
                  }}
                  watchers (first: 100) {{
                    totalCount
                  }}
                }}
              }}
            }}
        """
        return query
