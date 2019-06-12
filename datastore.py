import argparse
import logging
import json
from pg import DB

from GitHub_V3 import GitHub_v3 as ghv3_api
from GitHub_V4 import GitHub_v4 as ghv4_api

parser = argparse.ArgumentParser(description='Triggers gathering data from GitHub')
parser.add_argument('--config', '-c', help = 'Define alternate JSON config to use',
                    default = 'Config.json'
                   )
parser.add_argument('--token', '-t', help = 'GitHub developer token to use instead of one in config')
parser.add_argument('--logging', '-l', help = 'Set the log level (default: INFO)',
                    choices = ['DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL'], default = 'INFO'
                   )

args = parser.parse_args()

with open (args.config, 'r') as f:
  Config = json.load(f)

def get_single_repo_info(ghv4, org_name, repo_name):
  '''
    Used for getting a single repos data from the v4 API
  '''
  return ghv4.get_full_repo(org_name, repo_name)

def get_org_repo_info():
  orgs_array = Config['github_orgs']
  for org in orgs_array:
    logging.info('Pulling data for {} org.'.format(org))
    ghv4.get_cves_for_org(org)
    repo_list = ghv4.get_org_repo_list(org)
    ghv4.get_org_all_repo_details(org, repo_list)
    ghv3.get_repo_traffic(org, repo_list)
    logging.info('Data for {} logged.'.format(org))

if __name__ == '__main__':
  logging.basicConfig(format='%(levelname)s:%(message)s', level=args.logging)
  token = args.token if args.token is not None else Config['github_token']
  db = DB(dbname = Config['database']['db_name'], host = Config['database']['endpoint'],
          port = Config['database']['port'], user = Config['database']['user'],
          passwd = Config['database']['password'])
  ghv4 = ghv4_api(token, db)
  ghv3 = ghv3_api(token, db)

  get_org_repo_info()
 