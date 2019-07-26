class Repo:
    def __init__(self):
        """
      Contains the graphql query structure for getting all repo information for an org and individually.
      """

    def get_full_org_repos(self, org, repo_after="", repo_count=100):
        if len(repo_after) > 0:
            repo_after = 'after: "{}"'.format(repo_after)
        query = """
            query {{
              organization(login: "{org_name}") {{
                repositories(first: 100 {repo_cursor}) {{
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
          """.format(
            org_name=org, repo_cursor=repo_after
        )
        return query

    def get_single_repo_base(self, org, repo, additional_query):
        query = """
          query {{
            organization(login: "{org_name}") {{
              repository(name: "{repo_name}") {{
                {query}
              }}
            }}
          }}
        """.format(
            org_name=org, repo_name=repo, query=additional_query
        )
        return query

    def get_repo_base_info(self):
        query = """
            {assignable_users}
            {branch_protection_rules}
            {collaborators}
            {forks}
            {labels}
            {languages}
            {issues}
            {milestones}
            {projects}
            {pull_requests}
            {releases}
            {repository_topics}
            {stargazers}
            {watchers}
            codeOfConduct {{
              body
              id
              key
              name
              resourcePath
              url
            }}
            createdAt
            databaseId
            defaultBranchRef{{
              id
              name
              prefix
            }}
            description
            diskUsage
            hasIssuesEnabled
            hasWikiEnabled
            homepageUrl
            id
            isArchived
            isDisabled
            isFork
            isLocked
            isMirror
            isPrivate
            licenseInfo {{
              body
              conditions {{
                description
                key
                label
              }}
              description
              featured
              hidden
              id
              implementation
              key
              limitations {{
                description
                key
                label
              }}
              name
              nickname
              permissions {{
                description
                key
                label
              }}
              spdxId
              url
            }}
            lockReason
            mergeCommitAllowed
            mirrorUrl
            name
            nameWithOwner
            owner {{
              avatarUrl
              id
              login
              resourcePath
              url
            }}
            parent {{
              id
              nameWithOwner
            }}
            primaryLanguage {{
              color
              id
              name
            }}
            projectsResourcePath
            projectsUrl
            pushedAt
            rebaseMergeAllowed
            resourcePath
            squashMergeAllowed
            sshUrl
            updatedAt
            url
          """.format(
            assignable_users=self.part_users_min("assignableUsers"),
            branch_protection_rules=self.part_repo_branch_protection_rules(),
            collaborators=self.part_users_min("collaborators"),
            forks=self.part_repo_forks(),
            issues=self.part_issues(),
            labels=self.part_label("labels"),
            languages=self.part_languages(),
            milestones=self.part_milestones(),
            projects=self.part_projects(),
            pull_requests=self.part_pull_requests(),
            releases=self.part_releases(),
            repository_topics=self.part_repository_topics(),
            stargazers=self.part_users_count("stargazers"),
            watchers=self.part_users_count("watchers"),
        )
        return query

    # Partials for usage in query creation
    def part_users_min(self, shifty_name, user_last=""):
        """
        Returns the minimum user information for tracking
        Parameter 'shifty_name' changes on calling connection
        """
        if len(user_last) > 0:
            user_last = 'after: "{}"'.format(user_last)
        query = """
          {connector_name} (first: 100 {user_cursor}) {{
            edges {{
              cursor
              node {{
                email
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
        """.format(
            connector_name=shifty_name, user_cursor=user_last
        )
        return query

    def part_users_count(self, shifty_name, user_last=""):
        """
        Returns the minimum user information for tracking
        Parameter 'shifty_name' changes on calling connection
        """
        if len(user_last) > 0:
            user_last = 'after: "{}"'.format(user_last)
        query = """
            {connector_name} (first: 100 {user_cursor}) {{
              totalCount
            }}
        """.format(
            connector_name=shifty_name, user_cursor=user_last
        )
        return query

    def part_repo_branch_protection_rules(self, rule_last=""):
        if len(rule_last) > 0:
            rule_last = 'after: "{}"'.format(rule_last)
        query = """
            branchProtectionRules (first: 100 {rule_cursor}) {{
              edges {{
                cursor
                node {{
                  creator {{
                    login
                    resourcePath
                    url
                  }}
                  databaseId
                  dismissesStaleReviews
                  id
                  isAdminEnforced
                  pattern
                  requiredApprovingReviewCount
                  requiredStatusCheckContexts
                  requiresApprovingReviews
                  requiresCommitSignatures
                  requiresStatusChecks
                  requiresStrictStatusChecks
                  restrictsPushes
                  restrictsReviewDismissals
                }}
              }}
              pageInfo {{
                endCursor
                hasNextPage
              }}
              totalCount
            }}
        """.format(
            rule_cursor=rule_last
        )
        return query

    def part_repo_forks(self, forks_last=""):
        if len(forks_last) > 0:
            forks_last = 'after: "{}"'.format(forks_last)
        query = """
            forks (first: 100 {forks_cursor}) {{
              totalCount
            }}
        """.format(
            forks_cursor=forks_last
        )
        return query

    def part_issue_comments(self, shifty_name, comments_last=""):
        """
        Returns the info for a issueComment connector
        Parameter 'shifty_name' changes on calling connection
        """
        if len(comments_last) > 0:
            comments_last = 'after: "{}"'.format(comments_last)

        """
        Reactions are not included as it causes the query to request too many nodes
        If wanting to add in the future use self.part_reaction()
        """
        query = """
            {connection_name} (first: 100 {comments_cursor}) {{
              edges {{
                cursor
                node {{
                  author {{
                    login
                    resourcePath
                    url
                  }}
                  authorAssociation
                  body
                  createdAt
                  createdViaEmail
                  databaseId
                  editor {{
                    login
                    resourcePath
                    url
                  }}
                  id
                  isMinimized
                  lastEditedAt
                  minimizedReason
                  publishedAt
                  resourcePath
                  updatedAt
                  url
                }}
              }}
              pageInfo {{
                endCursor
                hasNextPage
              }}
              totalCount
            }}
        """.format(
            connection_name=shifty_name, comments_cursor=comments_last
        )
        return query

    def part_issues(self, issues_last=""):
        if len(issues_last) > 0:
            issues_last = 'after: "{}"'.format(issues_last)
        query = """
          issues (first: 50 {issues_cursor}) {{
            edges {{
              cursor
              node {{
                {assignees}
                {comments}
                {labels}
                {participants}
                activeLockReason
                author {{
                  login
                  resourcePath
                  url
                }}
                authorAssociation
                body
                closed
                closedAt
                createdAt
                createdViaEmail
                databaseId
                editor {{
                  login
                  resourcePath
                  url
                }}
                id
                includesCreatedEdit
                lastEditedAt
                locked
                milestone {{
                  closed
                  closedAt
                  createdAt
                  creator {{
                    login
                    resourcePath
                    url
                  }}
                  description
                  dueOn
                  id
                  number
                  resourcePath
                  state
                  title
                  updatedAt
                  url
                }}
                number
                publishedAt
                reactionGroups {{
                  content
                  createdAt
                  subject {{
                    databaseId
                    id
                  }}
                }}
                resourcePath
                state
                title
                updatedAt
                url
              }}
            }}
            pageInfo {{
              endCursor
              hasNextPage
            }}
            totalCount
          }}
        """.format(
            issues_cursor=issues_last,
            assignees=self.part_users_min("assignees"),
            comments=self.part_issue_comments("comments"),
            labels=self.part_label("labels"),
            participants=self.part_users_min("participants"),
        )
        return query

    def part_label(self, shifty_name, labels_last=""):
        """
        Returns the info for a label connector
        Parameter 'shifty_name' changes on calling connection
        """
        if len(labels_last) > 0:
            labels_last = 'after: "{}"'.format(labels_last)
        query = """
            {connection_name} (first: 100 {labels_cursor}) {{
              edges {{
                cursor
                node {{
                  color
                  createdAt
                  description
                  id
                  isDefault
                  name
                  resourcePath
                  updatedAt
                  url
                }}
              }}
              pageInfo {{
                endCursor
                hasNextPage
              }}
              totalCount
            }}
        """.format(
            connection_name=shifty_name, labels_cursor=labels_last
        )
        return query

    def part_languages(self, languages_last=""):
        if len(languages_last) > 0:
            languages_last = 'after: "{}"'.format(languages_last)
        query = """
          languages (first: 100 {languages_cursor}) {{
            edges {{
              cursor
              node {{
                color
                id
                name
              }}
              size
            }}
            pageInfo {{
              endCursor
              hasNextPage
            }}
            totalCount
            totalSize
          }}
        """.format(
            languages_cursor=languages_last
        )
        return query

    def part_milestones(self, with_issues=False, milestones_last=""):
        # getting issues is togglable for different situations
        issue_connector = ""
        if with_issues:
            issue_connector = self.part_issues()

        if len(milestones_last) > 0:
            milestones_last = 'after: "{}"'.format(milestones_last)
        query = """
            milestones (first: 100 {milestones_cursor}) {{
              edges {{
                cursor
                node {{
                  {issues}
                  closed
                  closedAt
                  createdAt
                  creator {{
                    login
                    resourcePath
                    url
                  }}
                  description
                  dueOn
                  id
                  number
                  resourcePath
                  state
                  title
                  updatedAt
                  url
                }}
              }}
              pageInfo {{
                endCursor
                hasNextPage
              }}
              totalCount
            }}
        """.format(
            issues=issue_connector, milestones_cursor=milestones_last
        )
        return query

    def part_columns(self, columns_last=""):
        if len(columns_last) > 0:
            columns_last = 'after: "{}"'.format(columns_last)
        query = """
            columns (first: 100 {columns_cursor}) {{
              edges {{
                cursor
                node {{
                  createdAt
                  databaseId
                  id
                  name
                  purpose
                  resourcePath
                  updatedAt
                  url
                }}
              }}
              pageInfo {{
                endCursor
                hasNextPage
              }}
              totalCount
            }}
        """.format(
            columns_cursor=columns_last
        )
        return query

    def part_pending_cards(self, pending_cards_last=""):
        if len(pending_cards_last) > 0:
            pending_cards_last = 'after: "{}"'.format(pending_cards_last)
        query = """
            pendingCards (first: 100 {pending_cards_cursor}) {{
              edges {{
                cursor
                node {{
                  createdAt
                  creator {{
                    login
                    resourcePath
                    url
                  }}
                  databaseId
                  id
                  isArchived
                  note
                  resourcePath
                  state
                  updatedAt
                  url
                }}
              }}
              pageInfo {{
                endCursor
                hasNextPage
              }}
              totalCount
            }}
        """.format(
            pending_cards_cursor=pending_cards_last
        )
        return query

    def part_projects(self, projects_last=""):
        if len(projects_last) > 0:
            projects_last = 'after: "{}"'.format(projects_last)
        query = """
            projects (first: 100 {projects_cursor}) {{
              edges {{
                cursor
                node {{
                  {columns}
                  {pending_cards}
                  body
                  closed
                  closedAt
                  createdAt
                  creator {{
                    login
                    resourcePath
                    url
                  }}
                  databaseId
                  id
                  name
                  number
                  owner {{
                    id
                    projectsResourcePath
                    projectsUrl
                  }}
                  resourcePath
                  state
                  updatedAt
                  url
                }}
              }}
              pageInfo {{
                endCursor
                hasNextPage
              }}
              totalCount
            }}
        """.format(
            columns=self.part_columns(),
            pending_cards=self.part_pending_cards(),
            projects_cursor=projects_last,
        )
        return query

    def part_files(self, files_last=""):
        if len(files_last) > 0:
            files_last = 'after: "{}"'.format(files_last)
        query = """
            files (first: 100 {files_cursor}) {{
              edges {{
                cursor
                node {{
                  additions
                  deletions
                  path
                }}
              }}
              pageInfo {{
                endCursor
                hasNextPage
              }}
              totalCount
            }}
        """.format(
            files_cursor=files_last
        )
        return query

    def part_reviews(self, reviews_last=""):
        if len(reviews_last) > 0:
            reviews_last = 'after: "{}"'.format(reviews_last)
        query = """
            reviews (first: 100 {reviews_cursor}) {{
              edges {{
                cursor
                node {{
                  author {{
                    login
                    resourcePath
                    url
                  }}
                  body
                  createdAt
                  createdViaEmail
                  databaseId
                  id
                  lastEditedAt
                  resourcePath
                  state
                  submittedAt
                  url
                }}
              }}
              pageInfo {{
                endCursor
                hasNextPage
              }}
              totalCount
            }}
        """.format(
            reviews_cursor=reviews_last
        )
        return query

    def part_pull_request_commit(self, commits_last=""):
        if len(commits_last) > 0:
            commits_last = 'after: "{}"'.format(commits_last)
        query = """
            commits (first: 50 {commits_cursor}) {{
              edges {{
                cursor
                node {{
                  commit {{
                    abbreviatedOid
                    additions
                    author {{
                      date
                      email
                      name
                      user {{
                        id
                        login
                      }}
                    }}
                    authoredByCommitter
                    authoredDate
                    changedFiles
                    commitResourcePath
                    commitUrl
                    committedDate
                    committedViaWeb
                    committer {{
                      date
                      email
                      name
                      user {{
                        id
                        login
                      }}
                    }}
                    deletions
                    id
                    message
                    oid
                    pushedDate
                    resourcePath
                    status {{
                      id
                      state
                    }}
                    tarballUrl
                    treeResourcePath
                    treeUrl
                    url
                  }}
                  id
                  resourcePath
                  url
                }}
              }}
              pageInfo {{
                endCursor
                hasNextPage
              }}
              totalCount
            }}
        """.format(
            commits_cursor=commits_last
        )
        return query

    def part_pull_requests(self, pull_requests_last=""):
        if len(pull_requests_last) > 0:
            pull_requests_last = 'after: "{}"'.format(pull_requests_last)
        query = """
            pullRequests (first: 20 {pull_requests_cursor}) {{
              edges {{
                cursor
                node {{
                  {comments}
                  {commits}
                  {files}
                  {participants}
                  {reviews}
                  activeLockReason
                  additions
                  author {{
                    login
                    resourcePath
                    url
                  }}
                  authorAssociation
                  baseRef {{
                    id
                    name
                    prefix
                    target {{
                      abbreviatedOid
                      commitResourcePath
                      commitUrl
                      id
                      oid
                    }}
                  }}
                  baseRefName
                  baseRefOid
                  body
                  changedFiles
                  closed
                  closedAt
                  createdAt
                  createdViaEmail
                  databaseId
                  deletions
                  editor {{
                    login
                    resourcePath
                    url
                  }}
                  headRef {{
                    id
                    name
                    prefix
                    target {{
                      abbreviatedOid
                      commitResourcePath
                      commitUrl
                      id
                      oid
                    }}
                  }}
                  headRefName
                  headRefOid
                  headRepositoryOwner {{
                    id
                    login
                    resourcePath
                    url
                  }}
                  id
                  isCrossRepository
                  lastEditedAt
                  locked
                  maintainerCanModify
                  mergeCommit {{
                    abbreviatedOid
                    additions
                    author {{
                      date
                      email
                      name
                      user {{
                        email
                        id
                        login
                        name
                      }}
                    }}
                    authoredByCommitter
                    authoredDate
                    changedFiles
                    commitResourcePath
                    commitUrl
                    committedDate
                    committedViaWeb
                    committer {{
                      date
                      email
                      name
                      user {{
                        email
                        id
                        login
                        name
                      }}
                    }}
                    deletions
                    id
                    message
                    messageHeadline
                    oid
                    pushedDate
                    resourcePath
                    status {{
                      contexts {{
                        commit {{
                          id
                          oid
                        }}
                        context
                        createdAt
                        creator {{
                          login
                          resourcePath
                          url
                        }}
                        description
                        id
                        state
                        targetUrl
                      }}
                      id
                      state
                    }}
                    tarballUrl
                    treeResourcePath
                    treeUrl
                    url
                    zipballUrl
                  }}
                  mergeable
                  merged
                  mergedAt
                  mergedBy {{
                    login
                    resourcePath
                    url
                  }}
                  milestone {{
                    closed
                    closedAt
                    createdAt
                    creator {{
                      login
                      resourcePath
                      url
                    }}
                    description
                    dueOn
                    id
                    number
                    resourcePath
                    state
                    title
                    updatedAt
                    url
                  }}
                  number
                  permalink
                  publishedAt
                  reactionGroups {{
                    content
                    createdAt
                    subject {{
                      databaseId
                      id
                    }}
                  }}
                  resourcePath
                  revertResourcePath
                  revertUrl
                  state
                  suggestedReviewers {{
                    isAuthor
                    isCommenter
                    reviewer {{
                      email
                      id
                      login
                      name
                    }}
                  }}
                  title
                  updatedAt
                  url
                }}
              }}
              pageInfo {{
                endCursor
                hasNextPage
              }}
              totalCount
            }}
        """.format(
            comments=self.part_issue_comments("comments"),
            commits=self.part_pull_request_commit(),
            files=self.part_files(),
            participants=self.part_users_min("participants"),
            pull_requests_cursor=pull_requests_last,
            reviews=self.part_reviews(),
        )
        return query

    def part_release_assets(self, release_assets_last=""):
        if len(release_assets_last) > 0:
            release_assets_last = 'after: "{}"'.format(release_assets_last)
        query = """
            releaseAssets (first: 100 {release_assets_cursor}) {{
              edges {{
                cursor
                node {{
                  contentType
                  createdAt
                  downloadCount
                  downloadUrl
                  id
                  size
                  updatedAt
                  uploadedBy {{
                    email
                    id
                    login
                    name
                  }}
                  url
                }}
              }}
              pageInfo {{
                endCursor
                hasNextPage
              }}
              totalCount
            }}
        """.format(
            release_assets_cursor=release_assets_last
        )
        return query

    def part_releases(self, releases_last=""):
        if len(releases_last) > 0:
            releases_last = 'after: "{}"'.format(releases_last)
        query = """
            releases (first: 100 {releases_cursor}) {{
              edges {{
                cursor
                node {{
                  {release_assets}
                  author {{
                    login
                    resourcePath
                    url
                  }}
                  createdAt
                  description
                  id
                  isDraft
                  isPrerelease
                  name
                  publishedAt
                  resourcePath
                  tag {{
                    id
                    name
                    prefix
                    target {{
                      abbreviatedOid
                      commitResourcePath
                      commitUrl
                      id
                      oid
                    }}
                  }}
                  tagName
                  updatedAt
                  url
                }}
              }}
              pageInfo {{
                endCursor
                hasNextPage
              }}
              totalCount
            }}
        """.format(
            releases_cursor=releases_last, release_assets=self.part_release_assets()
        )
        return query

    def part_repository_topics(self, repository_topics_last=""):
        if len(repository_topics_last) > 0:
            repository_topics_last = f'after: "{repository_topics_last}"'
        query = """
            repositoryTopics (first: 100 {repository_topics_cursor}) {{
              edges {{
                cursor
                node {{
                  id
                  resourcePath
                  topic {{
                    id
                    name
                  }}
                  url
                }}
              }}
              pageInfo {{
                endCursor
                hasNextPage
              }}
              totalCount
            }}
        """.format(
            repository_topics_cursor=repository_topics_last
        )
        return query

    # currently unused. remove functions from this section as they are used
    def part_repo_deploy_keys(self, deploy_keys_last=""):
        if len(deploy_keys_last) > 0:
            deploy_keys_last = 'after: "{}"'.format(deploy_keys_last)
        query = """
            deployKeys (first: 100 {deploy_keys_cursor}) {{
              edges {{
                cursor
                node {{
                  createdAt
                  id
                  key
                  readOnly
                  title
                  verified
                }}
              }}
              pageInfo {{
                endCursor
                hasNextPage
              }}
              totalCount
            }}
        """.format(
            deploy_keys_cursor=deploy_keys_last
        )
        return query

    def part_reaction(self, shifty_name, reaction_last=""):
        """
        Returns the info for a reaction connector
        Parameter 'shifty_name' changes on calling connection
        """
        if len(reaction_last) > 0:
            reaction_last = 'after: "{}"'.format(reaction_last)
        query = """
            {connection_name} (first: 100 {reaction_cursor}) {{
              edges {{
                cursor
                node {{
                  content
                  createdAt
                  databaseId
                  id
                  user {{
                    email
                    id
                    login
                    name
                  }}
                }}
              }}
              pageInfo {{
                endCursor
                hasNextPage
              }}
              totalCount
            }}
        """.format(
            connection_name=shifty_name,
            reaction_cursor=reaction_last,
            user=self.part_users_min("user"),
        )
        return query
