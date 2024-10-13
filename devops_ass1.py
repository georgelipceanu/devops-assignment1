import boto3
import argparse
from datetime import datetime, timedelta
import string
import random
import json
import subprocess
import logging
import webbrowser
import time
# from selenium import webdriver
# from selenium.webdriver.firefox.options import Options
# from selenium.webdriver.firefox.service import Service
# import os

# ERROR LOGGING SETUP
subprocess.run("clear")
logging.basicConfig(filename='error_logs.txt', level=logging.ERROR, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
   
# source: https://www.browserstack.com/guide/geckodriver-selenium-python
# print("---Setting up web driver---") DID NOT WORK USING THIS METHOD, WORKING WEB CONNECTION DOWN BELOW
# try:
#     cwd = os.getcwd()  
#     geckodriver_path = os.path.join(cwd, 'geckodriver')
#     options = Options()
#     options.binary_location = r'/usr/bin/firefox'
#     profile_path = r"/home/vboxuser/snap/firefox/common/.mozilla/firefox/wv7wjvux.george"  # Update with your actual path
#     options.set_preference('profile', profile_path)
#     service = Service(geckodriver_path)
#     driver = webdriver.Firefox(service=service, options=options)
#     driver.get('https://www.bstackdemo.com/')
# except Exception as error:
#     print("Failed to setup web driver.")
#     logging.error(error)
#     quit()
# quit()

# SETTING UP ARGPARSER (ADDITIONAL, source: https://docs.python.org/3/library/argparse.html)
parser = argparse.ArgumentParser(
            prog='DevOpsAssignment',
            description='Script that spins up EC2 and Bucket')
parser.add_argument('-b', '--bold', action='store_true', help="Make the EC2 text bold.")
parser.add_argument('-h1', '--header', action='store_true', help="Make the EC2 text H1.")
parser.add_argument('-i', '--italics', action='store_true', help="Make the EC2 text italics.")
parser.add_argument('additional_text', nargs='*', help="Additional text to display")
args = parser.parse_args()
if args.additional_text:
    additional_text = ' '.join(args.additional_text) 
else: additional_text = "This is additional text! :)"
if args.bold:
    additional_text = f"<b>{additional_text}</b>"
elif args.header:
    additional_text = f"<h1>{additional_text}</h1>"
elif args.italics:
    additional_text = f"<i>{additional_text}</i>"

# ADJUSTABLE VARIABLES
print("---Variable Setup---")
print("Retrieving AMI...")
try:
    # source: https://aws.amazon.com/blogs/compute/query-for-the-latest-amazon-linux-ami-ids-using-aws-systems-manager-parameter-store/
    instance_image_id = subprocess.run(
        """aws ec2 describe-images \
        --region us-east-1 \
        --owners amazon \
        --filters "Name=name,Values=amzn2-ami-kernel-*-x86_64-gp2" \
        --query "Images | sort_by(@, &CreationDate)[-1].ImageId" --output text""",
        shell=True, check=True, stdout=subprocess.PIPE, text=True
        ).stdout.strip()
    print(f"Retrieved {instance_image_id}!")
except Exception as error:
    instance_image_id = 'ami-0ebfd941bbafe70c6'
    print(f"Unable to retrieve AMI, using {instance_image_id} as default.")
keypair = 'rfstudentkey'
sg_ids = ['sg-015185af0d0cd3ff9'] # SECURITY GROUP THAT TAKES IN SSH AND HTTP TRAFFIC
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
        echo '<br> {additional_text}' >> index.html
        cp index.html /var/www/html/index.html"""
IMAGE_URL = 'http://devops.witdemo.net/logo.jpg'

# KEYPAIR SETUP
print("Setting keypair with correct permissions...")
try:
    subprocess.run(["chmod", "700", f"{keypair}.pem"], check=True)
except Exception as error:
    print("No keypair of the same name in this directory.")
    logging.error(error)

# IMAGE SETUP AND WEBSITE
print("Downloading Logo...")
try:
    subprocess.run(["curl", "-o", 'logo.jpg', IMAGE_URL], check=True)
    print("Download Complete!")
except Exception as error:
    print("Failed to download Logo.")
    logging.error(error)
print("Setting up index.html for S3...")
try: 
    subprocess.run("""echo '<img src="logo.jpg">' > index.html""", shell=True, check=True)
    print("Website created.")
except Exception as error:
    print("Failed to create index.html.")
    logging.error(error)

# SPINNING UP INSTANCE
ec2 = boto3.resource('ec2')
ec2_client = boto3.client('ec2')
print("---Starting instance---")
try:
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
    print("Waiting for running...")
    new_instances[0].wait_until_running()
    print("Instance Running!")
    new_instances[0].reload()
    #print(dir(new_instances[0]))
except Exception as error:
    print("Failed to install instance.")
    logging.error(error)

# SPINNING UP BUCKET
s3 = boto3.resource("s3")
s3_client = boto3.client("s3")
ran = ''.join(random.choices(string.ascii_lowercase + string.digits, k = 6)) # source: https://www.javatpoint.com/python-program-to-generate-a-random-string
bucket_name = f"{ran}-glipceanu"
print(f"---Launching {bucket_name}---")
try:
    response = s3.create_bucket(Bucket=bucket_name)
    print("Bucket running")
except Exception as error:
    print("Bucket has not been created.")
    logging.error(error)
print("Configuring static hosting...")
try:  
    s3_client.delete_public_access_block(Bucket=bucket_name)
    website_configuration = {
        'ErrorDocument': {'Key': 'error.html'},
        'IndexDocument': {'Suffix': 'index.html'},
    }
    bucket_website = s3.BucketWebsite(bucket_name)
    response = bucket_website.put(WebsiteConfiguration=website_configuration)
except Exception as error:
    print("Unable to configure static hosting.")
    logging.error(error)
print("Updating bucket policies...")
try: 
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
    bucket_policy_json = json.dumps(bucket_policy) # CONVERT POLICY TO JSON AND APPLY
    s3_client.put_bucket_policy(Bucket=bucket_name, Policy=bucket_policy_json)
    print("Bucket policy put successfully!")
except Exception as error:
    print("Unable to put bucket policy.")
    logging.error(error)
print("Uploading logo.jpg...")
try:
    s3.Bucket(bucket_name).upload_file('logo.jpg', 'logo.jpg', ExtraArgs={'ContentType': 'image/jpeg'})
except Exception as error:
    print("Unable to upload logo.jpg.")
    logging.error(error)
print("Uploading index.html..")
try:
    s3.Bucket(bucket_name).upload_file('index.html', 'index.html', ExtraArgs={'ContentType': 'text/html'})
except Exception as error:
    print("Unable to upload logo.jpg.")
    logging.error(error)

# WRITING URLS TO FILE
try:
    print(f"---Retrieving DNS of {instance_id}---") # INSTANCE RETRIEVAL
    # ec2_details = ec2_client.describe_instances(InstanceIds=[instance_id])
    # instance_url = ec2_details['Reservations'][0]['Instances'][0].get('PublicDnsName')
    instance_url = new_instances[0].public_dns_name
    print(f"DNS retrieved!: {instance_url}")
except Exception as error:
    print("Failed to retrieve instance URL")
    logging.error(error)
print(f"---Retrieving URL of {bucket_name}---") # BUCKET RETRIEVAL
bucket_url = f"http://{bucket_name}.s3-website-us-east-1.amazonaws.com"
print(f"DNS retrieved!: {bucket_url}")
with open('glipceanu-websites.txt', 'w') as file: # WRITING TO glipceanu-websites.txt
    file.write(f'http://{instance_url}'+'\n')
    file.write(bucket_url)

# MONITORING INSTALL
print("---Installing monitoring---")
instance_ip = new_instances[0].public_ip_address
waiter = ec2_client.get_waiter('instance_status_ok') # WAITING UNTIL ALL INSTALLS ARE DONE IN ORDER FOR SSH PORT TO OPEN
print("Waiting for Instance status: OK...")
waiter.wait(InstanceIds=[instance_id])
try:
    print(f"Copying monitoring.sh to {instance_id} at {instance_ip}...")
    subprocess.run(["scp", "-i", f"{keypair}.pem", "-o", "StrictHostKeyChecking=no", "monitoring.sh", f"ec2-user@{instance_ip}:."], check=True)
    print(f"Connecting to {instance_id} at {instance_ip}...")
    subprocess.run(["ssh", "-i", f"{keypair}.pem", f"ec2-user@{instance_ip}", "-o", "StrictHostKeyChecking=no", "chmod 700 monitoring.sh"], check=True)
    print(f"Running...")
    subprocess.run(["ssh", "-i", f"{keypair}.pem", f"ec2-user@{instance_ip}", "-o", "StrictHostKeyChecking=no", "./monitoring.sh"], check=True)
except Exception as error:
    print("Failed to install monitoring.")
    logging.error(error) 

# WEBSITE CONNECTIONS (ADDITIONAL) 
print("---Connecting to websites---")
# NO NEED FOR AN ADDITIONAL WAITER SINCE INSTANCE STATUS IS OK BY THIS POINT
try:
    print("HTTP running, trying EC2 connection...")
    webbrowser.open(f'http://{instance_url}')
except Exception as error:
    print("Error connecting to EC2.")
    logging.error(error)
try:
    print("Trying S3 connection...")
    webbrowser.open(bucket_url)
except Exception as error:
    print("Error connecting to bucket.")
    logging.error(error)

# CLOUDWATCH MONITORING (ADDITIONAL)
print("---Implementing Cloudwatch---")
cloudwatch = boto3.resource('cloudwatch')
try: 
    #new_instances[0].monitor()  # Enables detailed monitoring on instance (1-minute intervals)
    instance = ec2.Instance(instance_id)
    instance.monitor() # Enables detailed monitoring on instance (1-minute intervals)
    metric_iterator = cloudwatch.metrics.filter(Namespace='AWS/EC2',
                                            MetricName='CPUUtilization',
                                            Dimensions=[{'Name':'InstanceId', 'Value': instance_id}])
    metric = list(metric_iterator)[0]
    response = metric.get_statistics(StartTime = datetime.utcnow() - timedelta(minutes=4),   # 4 minutes ago
                                    EndTime=datetime.utcnow(),                               # now
                                    Period=60,                                               # 4 min intervals
                                    Statistics=['Average'])
    print ("Average CPU utilisation:", response['Datapoints'][0]['Average'], response['Datapoints'][0]['Unit'])
except Exception as error:
    print("Error monitoring with Cloudwatch.")
    logging.error(error)
