import argparse
import logging
import os
from dotenv import load_dotenv
from pg import DB

from GitHub_V3 import GitHub_v3 as ghv3_api
from GitHub_V4 import GitHub_v4 as ghv4_api

parser = argparse.ArgumentParser(description="Triggers gathering data from GitHub")
parser.add_argument(
    "--token", "-t", help="GitHub developer token to use instead of one in config"
)
parser.add_argument(
    "--logging",
    "-l",
    help="Set the log level (default: INFO)",
    choices=["DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"],
    default="INFO",
)


def get_single_repo_info(ghv4, org_name, repo_name):
    """
    Used for getting a single repos data from the v4 API
    """
    return ghv4.get_full_repo(org_name, repo_name)


def get_org_repo_info():
    orgs_array = os.getenv("GITHUB_ORGS").split(",")
    for org in orgs_array:
        logging.info("Pulling data for {} org.".format(org))
        ghv4.get_cves_for_org(org)
        repo_list = ghv4.get_org_repo_list(org)
        ghv4.get_org_all_repo_details(org, repo_list)
        ghv3.get_repo_traffic(org, repo_list)
        logging.info("Data for {} logged.".format(org))


if __name__ == "__main__":
    args = parser.parse_args()
    load_dotenv()

    logging.basicConfig(format="%(levelname)s:%(message)s", level=args.logging)
    db = DB(
        dbname=os.getenv("DATABASE_NAME"),
        host=os.getenv("DATABASE_ENDPOINT"),
        port=int(os.getenv("DATABASE_PORT")),
        user=os.getenv("DATABASE_USER"),
        passwd=os.getenv("DATABASE_PASSWORD"),
    )

    token = args.token if args.token is not None else os.getenv("GITHUB_TOKEN")
    ghv4 = ghv4_api(token, db)
    ghv3 = ghv3_api(token, db)

    for org_name in os.getenv("GITHUB_ORGS").split(","):
        org_info = ghv4.get_cves_for_org(org_name)
    # get_org_repo_info()
    # ghv3.get_repo_traffic("amzn", "oss-contribution-tracker")

    # ghv4.get_org_all_repo_details("amzn", ["oss-contribution-tracker"])
    # json_obj = ghv4.get_cve_for_repo("amzn", "oss-contribution-tracker")
    # json_obj = ghv4.get_full_repo("awslabs", "s2n")
    # with open("pr_request.json", "wt") as f:
    #    json.dump(json_obj, f, sort_keys=True, indent=2)
