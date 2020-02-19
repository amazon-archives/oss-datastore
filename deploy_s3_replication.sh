#!/bin/bash

./infra/bin/config_checks.py
if [ "$?" -ne "0" ]; then
  echo "Stopping deployment of S3 Replicator Lambda function."
  exit 1
fi
./infra/s3_replication/cfn_deploy.sh
