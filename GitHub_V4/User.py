class User:
    def __init__(self):
        """
        Contains the graphql query structure for getting information about a user.
        """

    def get_user_orgs(self, username, org_last=""):
        # add cursor tracking if wanting to grab additional CVEs for a repo
        if len(org_last) > 0:
            org_last = 'after: "{}"'.format(org_last)
        query = """
            query {{
              user(login: "{user}") {{
                organizations(first: 100 {user_cursor}) {{
                  edges {{
                    cursor
                    node {{
                      id
                      login
                      name
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
        """.format(
            user=username, user_cursor=org_last
        )
        return query
