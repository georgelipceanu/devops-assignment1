import boto3
import sys
#from datetime import datetime
import string
import random
import json
import subprocess
import logging
import webbrowser
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

# ADJUSTABLE VARIABLES
if len(sys.argv) > 1: # source: https://www.geeksforgeeks.org/python-sys-module/
    addtional_text = f"{''.join(sys.argv[1:])}"
else: addtional_text = "This is additional text! :)"
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
subprocess.run(["chmod", "700", f"{keypair}.pem"], check=True)

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
    print(dir(new_instances[0]))
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
print(f"---Retrieving DNS of {instance_id}---") # INSTANCE RETRIEVAL
try:
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
    file.write(instance_url+'\n')
    file.write(bucket_url)

# MONITORING INSTALL
print("---Installing monitoring---")
instance_ip = new_instances[0].public_ip_address
waiter = ec2_client.get_waiter('instance_status_ok')
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