#!/bin/bash

LOCAL_PATH=$(dirname "$0")

#First, authenticate AWS CLI
aws configure set aws_access_key_id `echo $AWS_ACCESS_KEY_ID`
aws configure set aws_secret_access_key `echo $AWS_SECRET_ACCESS_KEY`
aws configure set aws_session_token `echo $AWS_SESSION_TOKEN`
aws configure set default.region `echo $AWS_DEFAULT_REGION`

roleName=lambda-replicate-$S3_REPLICATE_OTHER_ACCOUNT

#Create a tmp json file with the substitutions made
cp $LOCAL_PATH/trustRelationShipExample.json trustRelationShipExample.json.tmp
sed -i '' "s/AWS_ACCOUNT/$AWS_ACCOUNT/g" trustRelationShipExample.json.tmp
sed -i '' "s/ROLE_NAME/$roleName/g" trustRelationShipExample.json.tmp

#Do the same with sourceBucketPolicy.json
cp $LOCAL_PATH/sourceBucketPolicy.json sourceBucketPolicy.json.tmp
sed -i '' "s/S3_REPLICATE_OTHER_ACCOUNT/$S3_REPLICATE_OTHER_ACCOUNT/g" sourceBucketPolicy.json.tmp
sed -i '' "s/S3_ROOT_BUCKET/$S3_ROOT_BUCKET/g" sourceBucketPolicy.json.tmp

#And with roleDefinitionDestinationExample.json
cp $LOCAL_PATH/roleDefinitionDestinationExample.json roleDefinitionDestinationExample.json.tmp
sed -i '' "s/S3_REPLICATE_BUCKET_NAME/$S3_REPLICATE_BUCKET_NAME/g" roleDefinitionDestinationExample.json.tmp
sed -i '' "s/S3_ROOT_BUCKET/$S3_ROOT_BUCKET/g" roleDefinitionDestinationExample.json.tmp

#Now, let's create the CFN stack to point to the new bucket name
aws cloudformation create-stack --stack-name replicate-to-$S3_REPLICATE_BUCKET_NAME --capabilities CAPABILITY_AUTO_EXPAND CAPABILITY_IAM CAPABILITY_NAMED_IAM --template-body file://$LOCAL_PATH/pushS3Template.yml --parameters ParameterKey=S3DestinationBucket,ParameterValue=$S3_REPLICATE_BUCKET_NAME,ParameterKey=S3SourceBucket,ParameterValue=$S3_ROOT_BUCKET,ParameterKey=IAMRoleToAssume,ParameterValue=$S3_REPLICATE_OTHER_ROLE_ARN,ParameterKey=ListOfGithubOrgs,ParameterValue=$S3_REPLICATE_OTHER_ROLE_ARN,ParameterKey=LambdaRoleName,ParameterValue=$roleName
