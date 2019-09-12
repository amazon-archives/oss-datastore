import boto3
import datetime
import json

from GitHub_V3 import GitHub_v3 as ghv3_api
from GitHub_V3 import GitHubV3Error
from GitHub_V4 import GitHub_v4 as ghv4_api
from GitHub_V4 import GitHubV4Error


def get_sqs_url(sqs_client):
    """
    Get the datastores SQS URL.
    """
    sqs_map = sqs_client.list_queues()
    sqs_url = ""
    for url in sqs_map["QueueUrls"]:
        split = url.split("/")
        if split[-1] == "GitHubDatastoreQueue":
            sqs_url = url
    return sqs_url


def github_repo_handler(event, context):
    """
    Once a day grab all the repos from our orgs and add their names to an SQS queue
    """
    # secrets manager setup for GitHub token
    secrets_client = boto3.client(
        service_name="secretsmanager", region_name="us-west-2"
    )
    secret_data = secrets_client.get_secret_value(SecretId="OSS-Datastore-GitHub-Token")
    secret_token = json.loads(secret_data["SecretString"])
    secret = secret_token["OSS-Datastore-GitHub-Token"]

    # systems manager setup
    config_client = boto3.client(service_name="ssm", region_name="us-west-2")

    # GitHub client setup
    ghv3 = ghv3_api(secret)
    org_list = config_client.get_parameter(
        Name="GitHubDatastoreOrgList", WithDecryption=True
    )["Parameter"]["Value"]

    # sqs setup
    sqs_client = boto3.client(service_name="sqs", region_name="us-west-2")
    sqs_url = get_sqs_url(sqs_client)
    date = datetime.datetime.now()
    print(f"TriggerGitHubDataPull {date}")
    # get all repos for each org and add them to the queue
    for org in org_list.split(","):
        repo_list = ghv3.get_repos(org.strip())
        for repo in repo_list:
            sqs_client.send_message(QueueUrl=sqs_url, MessageBody=repo["full_name"])
    print(f"TriggerGitHubDataPullComplete {date}")
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "text/plain"},
        "body": f"Triggered data pull from GitHub @ {date}",
    }


def github_data_handler(event, context):
    """
    Triggered by a CloudWatch monitor and pulls data to act on from an SQS queue
    """
    # secrets manager setup
    secrets_client = boto3.client(
        service_name="secretsmanager", region_name="us-west-2"
    )
    # sqs setup
    sqs_client = boto3.client(service_name="sqs", region_name="us-west-2")
    sqs_url = get_sqs_url(sqs_client)
    secret_data = secrets_client.get_secret_value(SecretId="OSS-Datastore-GitHub-Token")
    secret_token = json.loads(secret_data["SecretString"])
    secret = secret_token["OSS-Datastore-GitHub-Token"]

    ghv3 = ghv3_api(secret)
    ghv4 = ghv4_api(secret)

    event_info = event["Records"]
    for record in event_info:
        full_name = record["body"]
        org, repo = record["body"].split("/")
        try:
            ghv3.write_repo_traffic_to_s3(org, repo)
            ghv4.write_repo_traffic_to_s3(org, repo)
        except (GitHubV3Error, GitHubV4Error) as err:
            # if either request fails readd the to the queue
            print(f"Failed to get data for {full_name}. Putting back in queue.")
            print(f"Error: {err}")
            sqs_client.send_message(QueueUrl=sqs_url, MessageBody=full_name)
