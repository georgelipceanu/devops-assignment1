import boto3
from datetime import datetime
import json

keypair = 'rfstudentkey'
sg_ids = ['sg-015185af0d0cd3ff9']
image_id = 'ami-0ebfd941bbafe70c6'

ec2 = boto3.resource('ec2')
new_instances = ec2.create_instances(
    ImageId=image_id,
    MinCount=1,
    MaxCount=1,
    SecurityGroupIds=sg_ids,
    KeyName=keypair,
    UserData="""#!/bin/bash
        yum install httpd -y
        systemctl enable httpd
        systemctl start httpd""",
    InstanceType='t2.nano',
    TagSpecifications=[
        {
            'ResourceType': 'instance',
            'Tags': [
                {'Key': 'Name', 'Value': 'MyWebServer'},
            ]
        }
    ])

instance_id = new_instances[0].id
print(instance_id)
new_instances[0].wait_until_running()
print("Instance Running.")

s3 = boto3.resource("s3")
s3_client = boto3.client("s3")

bucket_name = f"projectx-bucket1-{datetime.now().strftime('%Y-%m-%d-%s')}"
try:
    response = s3.create_bucket(Bucket=bucket_name)
    print (response)

    s3_client.delete_public_access_block(Bucket=bucket_name)

    website_configuration = {
        'ErrorDocument': {'Key': 'error.html'},
        'IndexDocument': {'Suffix': 'index.html'},
    }
    bucket_website = s3.BucketWebsite(bucket_name)
    response = bucket_website.put(WebsiteConfiguration=website_configuration)
    print(response)

    bucket_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "PublicReadGetObject",
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{bucket_name}/*"
            }
        ]
    }

    # Convert the policy to JSON and apply it
    bucket_policy_json = json.dumps(bucket_policy)
    s3_client.put_bucket_policy(Bucket=bucket_name, Policy=bucket_policy_json)

    print("Upload an index.html file to test it works!")
except Exception as error:
    print (error)
