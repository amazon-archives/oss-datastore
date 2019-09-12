#!/usr/bin/env python3

import os

from aws_cdk import core
from dotenv import load_dotenv
from oss_datastore_lambda.oss_datastore_lambda_stack import OssDatastoreLambdaStack

load_dotenv()

app = core.App()
aws_account = os.getenv("AWS_ACCOUNT")
OssDatastoreLambdaStack(
    app, "oss-datastore-lambda", env={"account": aws_account, "region": "us-west-2"}
)
app.synth()
