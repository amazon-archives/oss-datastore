# Custom S3 Push

This section has the infrastructure and code to push to an S3 bucket that has the appropriate permissions. 

## Steps:

### Pre-steps

Before using this. Make sure there is an IAM Role that can interface with the Destination bucket in the destination account. 

## Add the bucket policy

The source bucket in this account needs a policy addition in order for the assuming role to get objects from it. Upload the sourceBucketPolicy.json to the S3 source bucket now.

## Run the script:

Upload the pushS3Template.yml in Cloudformation. 

Enter the source S3 bucket in this account. Enter the Destination bucket in the other account. Enter the ARN to the IAM Role controlling access to the destination account (created in the pre-steps)

Run the script. This will create the resources (IAM Role, Cloudwatch event, Lambda). The lambda code is inlined in the template.

## Post Script Authorization

Now that the Role is created in the source account, we need to add a trusted entity to the role in the destination account.

## Test

Go to Lambda and test it out!

## TODO
Add in Cloudwatch event? Or some other mechanism to continually run. Ideally right after the pull lambda happens.
