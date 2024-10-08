import boto3
from datetime import datetime
import json
import subprocess
import logging

# ERROR LOGGING SETUP
subprocess.run("clear")
logging.basicConfig(filename='logs.txt', level=logging.ERROR, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

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

# KEYPAIR SETUP
subprocess.run(["sudo", "chmod", "700", f"{keypair}.pem"], check=True)

# IMAGE SETUP
# print("Downloading Logo...")
# try:
#     subprocess.run(["curl", "-o", 'logo.jpg', IMAGE_URL], check=True)
#     print("Download Complete!")
# except Exception as error:
#     print("Failed to download Logo.")
#     logging.error(error)  

# SPINNING UP INSTANCE
ec2 = boto3.resource('ec2')
ec2_client = boto3.client('ec2')
print("Starting instance...")
new_instances = ec2.create_instances(
    ImageId=instance_image_id,
    MinCount=1,
    MaxCount=1,
    SecurityGroupIds=sg_ids,
    KeyName=keypair,
    UserData=userdata,
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
print(f"Instance ID: {instance_id}")
new_instances[0].wait_until_running()
print("Instance Running!")

# SPINNING UP BUCKET
# s3 = boto3.resource("s3")
# s3_client = boto3.client("s3")
# bucket_name = f"{datetime.now().strftime('%Y-%m-%d-%s')}-glipceanu"
# print(f"Launching {bucket_name}...")
# try:
#     response = s3.create_bucket(Bucket=bucket_name)
#     print (response)

#     s3_client.delete_public_access_block(Bucket=bucket_name)

#     website_configuration = {
#         'ErrorDocument': {'Key': 'error.html'},
#         'IndexDocument': {'Suffix': 'index.html'},
#     }
#     bucket_website = s3.BucketWebsite(bucket_name)
#     response = bucket_website.put(WebsiteConfiguration=website_configuration)

#     bucket_policy = {
#         "Version": "2012-10-17",
#         "Statement": [
#             {
#                 "Sid": "PublicReadGetObject",
#                 "Effect": "Allow",
#                 "Principal": "*",
#                 "Action": "s3:GetObject",
#                 "Resource": f"arn:aws:s3:::{bucket_name}/*"
#             }
#         ]
#     }

#     s3.Bucket(bucket_name).upload_file('logo.jpg', 'logo.jpg', ExtraArgs={'ContentType': 'image/jpeg'})

#     bucket_policy_json = json.dumps(bucket_policy) # convert the policy to JSON and apply it
#     s3_client.put_bucket_policy(Bucket=bucket_name, Policy=bucket_policy_json)
#     print("Bucket Completed!")
# except Exception as error:
#     print (error)

# WRITING URLS TO FILE
print(f"Retrieving DNS of {instance_id}...") # INSTANCE RETRIEVAL
try:
    ec2_details = ec2_client.describe_instances(InstanceIds=[instance_id])
    instance_url = ec2_details['Reservations'][0]['Instances'][0].get('PublicDnsName')
    print("DNS retrieved!")
except Exception as error:
    print("Failed to retrieve instance URL")
    logging.error(error)
# print(f"Retrieving URL of {bucket_name}...") # BUCKET RETRIEVAL
# try:
#     bucket_location = s3_client.get_bucket_location(Bucket=bucket_name)
#     region = bucket_location['LocationConstraint'] if bucket_location['LocationConstraint'] else 'us-east-1'
# except Exception as error:
#     print("Failed to retrieve bucket URL")
#     logging.error(error)
with open('glipceanu-websites.txt', 'w') as file: # WRITING TO glipceanu-websites.txt
    file.write(instance_url)
    #file.write(bucket_url)

# MONITORING INSTALL
print("Installing monitoring...")
#instance_ip = new_instances[0].public_ip_address
instance_ip = ec2_details['Reservations'][0]['Instances'][0].get('PublicIpAddress')
try:
    print(f"Copying monitoring.sh to {instance_id} at {instance_ip}...")
    subprocess.run(["scp", "-i", f"{keypair}.pem", "-o", "StrictHostKeyChecking=no", "monitoring.sh", f"ec2-user@{instance_ip}:."], check=True)
    print(f"Connecting to {instance_id} at {instance_ip}...")
    subprocess.run(["ssh", "-i", f"{keypair}.pem", f"ec2-user@{instance_ip}", "-o", "StrictHostKeyChecking=no", "chmod 700 monitoring.sh"], check=True)
    print(f"Running...")
    subprocess.run(["ssh", "-i", f"{keypair}.pem", f"ec2-user@{instance_ip}", "-o", "StrictHostKeyChecking=no", "./monitoring.sh"], check=True)
    print(f"Monitoring installed and running!")
except Exception as error:
    print("Failed to install monitoring.")
    logging.error(error) 