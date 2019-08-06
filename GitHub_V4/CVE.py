class CVE:
    def __init__(self):
        """
      Contains the graphql query structure for getting CVE information for an org.
    """

    def get_full_org_cve_info_query(
        self, org, repo_last="", repo_count_new=100, cve_count=100
    ):
        query = f"""
            query {{
              organization(login: "{org}") {{
                repositories(first: {repo_count_new} after: "{repo_last}") {{
                  edges {{
                    node {{
                      owner {{
                        id
                      }}
                      name
                      vulnerabilityAlerts ( first: {cve_count}) {{
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
                    }}
                    cursor
                  }}
                  pageInfo {{
                    endCursor
                    hasNextPage
                  }}
                }}
              }}
            }}
          """
        return query

    def get_repo_cve_info_query(self, org, repo, cve_last="", cve_first=100):
        # add cursor tracking if wanting to grab additional CVEs for a repo
        if len(cve_last) > 0:
            cve_last = 'after: "{}"'.format(cve_last)
        query = f"""
            query {{
              organization(login: "{org}") {{
                repository(name: "{repo}") {{
                  name
                  nameWithOwner
                  vulnerabilityAlerts ( first: {cve_first} {cve_last}) {{
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
                }}
              }}
            }}
        """
        return query
