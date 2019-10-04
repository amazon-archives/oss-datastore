from aws_cdk import (
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_lambda_event_sources as lambda_events,
    aws_s3 as s3,
    aws_sqs as sqs,
    aws_ssm as ssm,
    core,
)
from dotenv import load_dotenv
from os import getenv
from sys import exit


class OssDatastoreLambdaStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        load_dotenv(override=True)

        org_list = getenv("GITHUB_ORGS").split(",")

        # S3 bucket
        bucket_name = getenv("S3_ROOT_BUCKET")
        bucket = s3.Bucket(
            self,
            bucket_name,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            bucket_name=bucket_name,
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=False,
        )

        # SQS queue
        sqs_queue = sqs.Queue(
            self,
            "GitHubDatastoreQueue",
            encryption=sqs.QueueEncryption.KMS_MANAGED,
            queue_name="GitHubDatastoreQueue",
            visibility_timeout=core.Duration.minutes(15),
        )

        # SSM config
        config_manager = ssm.StringListParameter(
            self,
            "GitHubDatastoreOrgList",
            string_list_value=org_list,
            description="List of orgs to get data",
            parameter_name="GitHubDatastoreOrgList",
        )

        # Lambda function role
        lambda_role = iam.Role(
            self,
            "GitHubDataLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSQSFullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMFullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AWSLambdaFullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "SecretsManagerReadWrite"
                ),
            ],
        )

        # Lambda function(s)
        oss_datastore_repo_lambda = _lambda.Function(
            self,
            "GitHubRepoAggregate",
            runtime=_lambda.Runtime.PYTHON_3_6,
            code=_lambda.Code.from_asset("lambda/package.zip"),
            handler="github-data-pull.github_repo_handler",
            role=lambda_role,
            timeout=core.Duration.minutes(15),
        )

        # TODO: rate limit this as I am running out of tokens
        oss_datastore_pull_lambda = _lambda.Function(
            self,
            "GitHubDataHandler",
            runtime=_lambda.Runtime.PYTHON_3_6,
            code=_lambda.Code.from_asset("lambda/package.zip"),
            events=[lambda_events.SqsEventSource(sqs_queue)],
            handler="github-data-pull.github_data_handler",
            reserved_concurrent_executions=2,  # To slow down the token drain
            role=lambda_role,
            timeout=core.Duration.minutes(15),
        )

        # lambda scheduler
        lambda_rule = events.Rule(
            self,
            "Cron Rule",
            description="Setup cron schedule to get org data",
            schedule=events.Schedule.cron(
                # timezone is GMT and unconfigurable
                # adjust accordingly for your desired timezone
                minute="0",
                hour="7",
                month="*",
                year="*",
                week_day="*",
            ),
            targets=[targets.LambdaFunction(oss_datastore_repo_lambda)],
        )
