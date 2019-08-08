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

import argparse
import boto3
import logging
import os
import shutil
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


def upload_files_to_s3(s3):
    bucket_name = os.getenv("S3_ROOT_BUCKET")
    bucket = s3.Bucket(bucket_name)
    upload_path = "output"
    for subdir, dirs, files in os.walk(upload_path):
        for file in files:
            full_path = os.path.join(subdir, file)
            with open(full_path, "rb") as data:
                bucket.put_object(Key=full_path[len(upload_path) + 1 :], Body=data)
            # delete file after upload
            os.remove(full_path)
    # delete output folder and remaining directories
    shutil.rmtree(upload_path)


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
        ghv4.get_cves_for_org(org_name)
        ghv3.get_org_traffic(org_name)

    # now upload the json to S3
    access = os.getenv("AWS_ACCESS")
    secret = os.getenv("AWS_SECRET")
    token = os.getenv("AWS_TOKEN")
    s3 = boto3.resource(
        "s3",
        aws_access_key_id=access,
        aws_secret_access_key=secret,
        aws_session_token=token,
    )
    upload_files_to_s3(s3)
