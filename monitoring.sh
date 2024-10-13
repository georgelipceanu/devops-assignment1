#!/usr/bin/bash
#
# Some basic monitoring functionality; Tested on Amazon Linux 2023.
#
TOKEN=`curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600"`
INSTANCE_ID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id)
MEMORYUSAGE=$(free -m | awk 'NR==2{printf "%.2f%%", $3*100/$2 }')
PROCESSES=$(expr $(ps -A | grep -c .) - 1)
HTTPD_PROCESSES=$(ps -A | grep -c httpd)
# source: https://kloudvm.medium.com/simple-bash-script-to-monitor-cpu-memory-and-disk-usage-on-linux-in-10-lines-of-code-e4819fe38bf1
DISKUSAGE=$(df -h | awk '$NF=="/"{printf "%s\t\t", $5}')
CPU=$(top -bn1 | grep load | awk '{printf "%.2f%%\t\t\n", $(NF-2)}')

echo "Instance ID: $INSTANCE_ID"
echo "Memory utilisation: $MEMORYUSAGE"
echo "Disk utilisation: $DISKUSAGE"
echo "CPU utilisation: $CPU"
echo "No of processes: $PROCESSES"
if [ $HTTPD_PROCESSES -ge 1 ]
then
    echo "Web server is running"
else
    echo "Web server is NOT running"
fi
