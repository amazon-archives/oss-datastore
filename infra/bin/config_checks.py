#!/usr/bin/env python3

from dotenv import load_dotenv
from os import getenv
from sys import exit

if __name__ == "__main__":
    """
    Verify the orgs being monitored are the ones we want

    Note: Put this hear because putting it in CDK code caused failures
    """
    load_dotenv(override=True)
    org_list = getenv("GITHUB_ORGS").split(",")
    print(f"\nThe following GitHub organizations will be tracked:\n{org_list}")
    proceed_response = input("Proceed? (y/N): ")
    if proceed_response == "y" or proceed_response == "Y":
        exit(0)
    else:
        exit(1)
