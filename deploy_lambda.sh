#!/bin/bash

./infra/bin/config_checks.py
if [ "$?" -ne "0" ]; then
  echo "Stopping deployment of AWS Lambda functions."
  exit 1
fi
./infra/bin/lambda_package.sh

cdk deploy
