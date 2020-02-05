import boto3
import os
import datetime
import logging
from botocore.exceptions import ClientError

BACKFILL_EVENT_KEY = 'backfill'
CONTENTS_KEY = 'Contents'

def replicate(event, context):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    dates = [today]
    if BACKFILL_EVENT_KEY in event.keys() :
        dates = event[BACKFILL_EVENT_KEY]

    REPOS = ['alexa', 'alexa-labs', 'alexa-games']
    logger = logging.getLogger()
    logger.setLevel(logging.INFO) #Todo bump up to warn

    IAM_ROLE_ASSUME = os.environ['iamRole']
    destinationS3Bucket = os.environ['DestinationS3Bucket']
    sourceS3Bucket = os.environ['SourceS3Bucket']
    try :
        # Get our info from the assumed role
        sts = boto3.client('sts')
        stsAssumedCredentials = sts.assume_role(
            RoleArn=IAM_ROLE_ASSUME,
            RoleSessionName='assumeForS3Copy'
        )['Credentials'] 

        accessId = stsAssumedCredentials['AccessKeyId']
        secretId = stsAssumedCredentials['SecretAccessKey']
        sessionToken = stsAssumedCredentials['SessionToken']

        #Now Make our call to S3 local and S3 away.
        s3Client = boto3.client(
            's3',
            aws_access_key_id=accessId,
            aws_secret_access_key=secretId,
            aws_session_token=sessionToken,
        )

        KEY_STRUCTURE_PREFIX = '{date}/traffic/{parentRepo}'#-{name}-traffic-{timestamp}.json

        for date in dates:
            for repo in REPOS :
                allObjectsWithPrefix = s3Client.list_objects_v2(
                    Bucket=sourceS3Bucket,
                    Prefix=KEY_STRUCTURE_PREFIX.format(date=date, parentRepo=repo)
                )
                # jsonObjectsWithPrefix = json.loads(allObjectsWithPrefix)
                if CONTENTS_KEY in allObjectsWithPrefix.keys():
                    for record in allObjectsWithPrefix[CONTENTS_KEY]:
                        key = record['Key']
                        # For each record, copy
                        copySource = {
                            'Bucket':sourceS3Bucket,
                            'Key': key
                        }
                        s3Client.copy(copySource, destinationS3Bucket, key)
                else:
                    logging.warn('Failed to find contents for repo {key} on {date}'.format(key=repo, date=date))
    except ClientError as e: 
        logging.critical(e)
        logging.error('Failed to copy on {today}'.format(today));
        return {
            'statusCode': 500,
            'headers': {"Content-Type": "text/plain"},
            'body': 'failed on {today}'.format(today=today),
        }
    return {
        'statusCode': 200,
        'headers': {"Content-Type": "text/plain"},
        'body': 'Succeeded on {today}'.format(today=today),
    }
