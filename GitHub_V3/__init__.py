import datetime
import json
import logging
import os
import requests
import time

from pg import DB

class GitHub_v3:
  github_v3_url = 'https://api.github.com'
  github_v3_normal_headers = {
    'Authorization': None
  }
  db = None

  sleep_time = 16 # number of seconds to sleep
  max_retry_count = 5
  
  # functions
  def __init__(self, token, db_handle):
    '''
      Contains the graphql query structure for getting CVE information for an org.
    '''
    self.github_v3_normal_headers['Authorization'] = 'token {0}'.format(token)
    self.db = db_handle

  def write_structured_json(self, file_name, json_obj):
    if not os.path.exists('output/traffic'):
      os.makedirs('output/traffic')
    with open('output/traffic/{}'.format(file_name), 'wt') as f:
     print(json.dumps(json_obj, indent=2, ensure_ascii=False, sort_keys=True), file=f)

  def github_v3_get_query(self, query, headers):
    '''
      Making raw calls because python doesn't have a very good octokit client
    '''
    for count in range(1, self.max_retry_count + 1):
      request = requests.get(self.github_v3_url + query, headers=headers)
      if request.status_code == 200:
        return request.json()
      elif request.status_code == 202 or request.status_code == 204:  # repo exists but doesn't have any traffic info
        return { 'error': 'No content returned.' }
      else:
        logging.warn('Request failed, retrying in {} seconds. Number of recounts left: {}'.format(self.sleep_time, self.max_retry_count - count))
        time.sleep(self.sleep_time)
    # retry failed, log in DLQ
    self.db.insert('dead_letter_queue',
                source = 'github_v3', query = query,
                request_time = datetime.datetime.now(), response = {
                  'body': request.text,
                  'headers': headers,
                  'status_code': request.status_code,
                }
              )

  def get_api_rate_limit(self):
    '''
      Get rate limit from v3 API
    '''
    return self.github_v3_get_query('/rate_limit', self.github_v3_normal_headers)

  def get_repo_traffic(self, org, repo_list):
    '''
      Get the traffic info (referrers, paths, views, clones) for a repo and write to file

      Note: These sometimes fail the first request but there is no pagination.
            That being said, the retry takes care of getting the data since it
            seems that the API just needs a kick on that first request sionce
            the second is almost always successful.
    '''
    for repo in repo_list:
      rate_limit = self.get_api_rate_limit()
      if rate_limit['rate']['remaining'] < 100:
        logging.warn('Not enough tokens to complete request. Waiting until token refresh to proceed.')
        # sleep until you have new tokens
        d1 = datetime.datetime.now()
        d2 = datetime.datetime.fromtimestamp(rate_limit['rate']['reset'])
        time.sleep((d2 - d1).seconds + self.sleep_time)
      repo_name = repo['name']
      logging.info('Getting traffic and stats for {}/{}'.format(org, repo_name))
      # traffic info found https://developer.github.com/v3/repos/traffic/
      repo_info = {}
      repo_info['referrers'] = self.github_v3_get_query('/repos/{}/{}/traffic/popular/referrers'.format(org, repo_name), self.github_v3_normal_headers)
      repo_info['paths'] = self.github_v3_get_query('/repos/{}/{}/traffic/popular/paths'.format(org, repo_name), self.github_v3_normal_headers)
      repo_info['views'] = self.github_v3_get_query('/repos/{}/{}/traffic/views'.format(org, repo_name), self.github_v3_normal_headers)
      repo_info['clones'] = self.github_v3_get_query('/repos/{}/{}/traffic/clones'.format(org, repo_name), self.github_v3_normal_headers)
      # stats info found https://developer.github.com/v3/repos/statistics/
      repo_info['stats'] = {}
      repo_info['stats']['contributors'] = self.github_v3_get_query('/repos/{}/{}/stats/contributors'.format(org, repo_name), self.github_v3_normal_headers)
      repo_info['stats']['comment_activity'] = self.github_v3_get_query('/repos/{}/{}/stats/commit_activity'.format(org, repo_name), self.github_v3_normal_headers)
      repo_info['stats']['code_frequency'] = self.github_v3_get_query('/repos/{}/{}/stats/code_frequency'.format(org, repo_name), self.github_v3_normal_headers)
      repo_info['stats']['participation'] = self.github_v3_get_query('/repos/{}/{}/stats/participation'.format(org, repo_name), self.github_v3_normal_headers)
      repo_info['stats']['punch_card'] = self.github_v3_get_query('/repos/{}/{}/stats/punch_card'.format(org, repo_name), self.github_v3_normal_headers)
      self.write_structured_json('{}-{}-traffic-{}.json'.format(org, repo_name,
                                                           datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')),
                                 repo_info
                                )
      logging.info('Traffic and stats for {}/{} written to file'.format(org, repo_name))