#!/bin/bash
apt -y update
apt -y install nginx
echo "Hello from ${instance_name}" > /var/www/html/index.html
systemctl start nginx
