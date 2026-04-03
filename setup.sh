#!/bin/bash
# EC2 User Data — runs automatically when instance starts

yum update -y
yum install -y python3.11 python3.11-pip git

python3.11 -m pip install --upgrade pip

# Create app directory
mkdir -p /app
cd /app

# Install systemd service so backend starts on reboot
cat > /etc/systemd/system/smartac.service << 'SERVICE'
[Unit]
Description=SmartAC FastAPI Backend
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/app
EnvironmentFile=/app/.env
ExecStart=/usr/local/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable smartac
