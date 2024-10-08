import boto3
from datetime import datetime
import json
import subprocess

subprocess.run("clear")
# ADJUSTABLE VARIABLES
addtional_text = "This is additional text! :)"
keypair = 'rfstudentkey'
sg_ids = ['sg-015185af0d0cd3ff9']
instance_image_id = 'ami-0ebfd941bbafe70c6'
userdata = f"""#!/bin/bash
        yum install httpd -y
        systemctl enable httpd
        systemctl start httpd
        echo '<html>' > index.html
        echo 'Private IP address: ' >> index.html
        TOKEN=`curl -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600"`
        curl -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/local-ipv4 >> index.html
        echo '<br>Instance ID: ' >> index.html
        curl -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id >> index.html
        echo '<br>Instance Type: ' >> index.html
        curl -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-type >> index.html
        echo '<br>Availabilty Zone: ' >> index.html
        curl -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/placement/availability-zone >> index.html
        echo '<br> {addtional_text}' >> index.html
        cp index.html /var/www/html/index.html"""
IMAGE_URL = 'http://devops.witdemo.net/logo.jpg'
print("Downloading Logo...")
subprocess.run(["curl", "-o", 'logo.jpg', IMAGE_URL])

# ec2 = boto3.resource('ec2')
# new_instances = ec2.create_instances(
#     ImageId=instance_image_id,
#     MinCount=1,
#     MaxCount=1,
#     SecurityGroupIds=sg_ids,
#     KeyName=keypair,
#     UserData=userdata,
#     InstanceType='t2.nano',
#     TagSpecifications=[
#         {
#             'ResourceType': 'instance',
#             'Tags': [
#                 {'Key': 'Name', 'Value': 'MyWebServer'},
#             ]
#         }
#     ])

# instance_id = new_instances[0].id
# print(instance_id)
# new_instances[0].wait_until_running()
# print("Instance Running.")

s3 = boto3.resource("s3")
s3_client = boto3.client("s3")

bucket_name = f"{datetime.now().strftime('%Y-%m-%d-%s')}-glipceanu"
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

    s3.Bucket(bucket_name).upload_file('logo.jpg', 'logo.jpg', ExtraArgs={'ContentType': 'image/jpeg'})

    bucket_policy_json = json.dumps(bucket_policy) # convert the policy to JSON and apply it
    s3_client.put_bucket_policy(Bucket=bucket_name, Policy=bucket_policy_json)

    print("check it")
except Exception as error:
    print (error)
