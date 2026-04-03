# #!/bin/bash
# # SmartAC AWS Deployment Script
# # Run this from your project root: bash deploy.sh

# set -e

# echo "======================================"
# echo "  SmartAC AWS Deployment"
# echo "======================================"

# # ── Config ────────────────────────────────
# REGION="eu-west-2"
# EC2_NAME="smartac-backend"
# S3_BUCKET="smartac-frontend-$(date +%s)"
# KEY_NAME="smartac-key"
# INSTANCE_TYPE="t3.small"

# # Amazon Linux 2023 AMI for eu-west-2
# # AMI_ID="ami-0c1c30571d2dae5c9"
# AMI_ID="ami-0f1b092c39d616d45"


# echo ""
# echo "Step 1: Creating EC2 key pair..."
# aws ec2 create-key-pair \
#     --key-name $KEY_NAME \
#     --region $REGION \
#     --query 'KeyMaterial' \
#     --output text > ~/.ssh/smartac-key.pem
# chmod 400 ~/.ssh/smartac-key.pem
# echo "✅ Key pair saved to ~/.ssh/smartac-key.pem"

# echo ""
# echo "Step 2: Creating security group..."
# SG_ID=$(aws ec2 create-security-group \
#     --group-name smartac-sg \
#     --description "SmartAC backend security group" \
#     --region $REGION \
#     --query 'GroupId' \
#     --output text)

# aws ec2 authorize-security-group-ingress \
#     --group-id $SG_ID \
#     --protocol tcp --port 22 --cidr 0.0.0.0/0 \
#     --region $REGION

# aws ec2 authorize-security-group-ingress \
#     --group-id $SG_ID \
#     --protocol tcp --port 8000 --cidr 0.0.0.0/0 \
#     --region $REGION

# aws ec2 authorize-security-group-ingress \
#     --group-id $SG_ID \
#     --protocol tcp --port 80 --cidr 0.0.0.0/0 \
#     --region $REGION
# echo "✅ Security group created: $SG_ID"

# echo ""
# echo "Step 3: Launching EC2 instance..."
# INSTANCE_ID=$(aws ec2 run-instances \
#     --image-id $AMI_ID \
#     --instance-type $INSTANCE_TYPE \
#     --key-name $KEY_NAME \
#     --security-group-ids $SG_ID \
#     --region $REGION \
#     --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$EC2_NAME}]" \
#     --user-data file://setup.sh \
#     --query 'Instances[0].InstanceId' \
#     --output text)

# echo "✅ Instance launched: $INSTANCE_ID"
# echo "⏳ Waiting for instance to be running..."
# aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $REGION

# PUBLIC_IP=$(aws ec2 describe-instances \
#     --instance-ids $INSTANCE_ID \
#     --region $REGION \
#     --query 'Reservations[0].Instances[0].PublicIpAddress' \
#     --output text)

# echo "✅ Instance running at: $PUBLIC_IP"

# echo ""
# echo "Step 4: Creating S3 bucket for Flutter Web..."
# aws s3 mb s3://$S3_BUCKET --region $REGION
# aws s3 website s3://$S3_BUCKET \
#     --index-document index.html \
#     --error-document index.html

# aws s3api put-bucket-policy \
#     --bucket $S3_BUCKET \
#     --policy "{
#         \"Version\": \"2012-10-17\",
#         \"Statement\": [{
#             \"Sid\": \"PublicRead\",
#             \"Effect\": \"Allow\",
#             \"Principal\": \"*\",
#             \"Action\": \"s3:GetObject\",
#             \"Resource\": \"arn:aws:s3:::$S3_BUCKET/*\"
#         }]
#     }"
# echo "✅ S3 bucket created: $S3_BUCKET"

# echo ""
# echo "======================================"
# echo "  Deployment Summary"
# echo "======================================"
# echo ""
# echo "Backend IP:    $PUBLIC_IP"
# echo "Backend URL:   http://$PUBLIC_IP:8000"
# echo "S3 Bucket:     $S3_BUCKET"
# echo "S3 URL:        http://$S3_BUCKET.s3-website.$REGION.amazonaws.com"
# echo ""
# echo "Next steps:"
# echo "1. Wait 2 mins for EC2 to finish setup"
# echo "2. Copy backend files: bash copy_backend.sh $PUBLIC_IP"
# echo "3. Build Flutter web: bash deploy_flutter.sh $S3_BUCKET"
# echo ""
# echo "======================================"



# ///



# #!/bin/bash
# # SmartAC AWS Deployment Script
# # Run this from your project root: bash deploy.sh

# set -e

# echo "======================================"
# echo "  SmartAC AWS Deployment"
# echo "======================================"

# # ── Config ────────────────────────────────
# REGION="eu-west-2"
# EC2_NAME="smartac-backend"
# S3_BUCKET="smartac-frontend-$(date +%s)"
# KEY_NAME="smartac-key"
# INSTANCE_TYPE="t3.small"

# # Amazon Linux 2023 AMI for eu-west-2
# AMI_ID="ami-0f1b092c39d616d45"

# echo ""
# echo "Step 1: Creating EC2 key pair..."
# aws ec2 create-key-pair \
#     --key-name $KEY_NAME \
#     --region $REGION \
#     --query 'KeyMaterial' \
#     --output text > ~/.ssh/smartac-key.pem
# chmod 400 ~/.ssh/smartac-key.pem
# echo "✅ Key pair saved to ~/.ssh/smartac-key.pem"

# echo ""
# echo "Step 2: Creating security group..."
# SG_ID=$(aws ec2 create-security-group \
#     --group-name smartac-sg \
#     --description "SmartAC backend security group" \
#     --region $REGION \
#     --query 'GroupId' \
#     --output text)

# aws ec2 authorize-security-group-ingress \
#     --group-id $SG_ID \
#     --protocol tcp --port 22 --cidr 0.0.0.0/0 \
#     --region $REGION

# aws ec2 authorize-security-group-ingress \
#     --group-id $SG_ID \
#     --protocol tcp --port 8000 --cidr 0.0.0.0/0 \
#     --region $REGION

# aws ec2 authorize-security-group-ingress \
#     --group-id $SG_ID \
#     --protocol tcp --port 80 --cidr 0.0.0.0/0 \
#     --region $REGION
# echo "✅ Security group created: $SG_ID"

# echo ""
# echo "Step 3: Launching EC2 instance..."
# INSTANCE_ID=$(aws ec2 run-instances \
#     --image-id $AMI_ID \
#     --instance-type $INSTANCE_TYPE \
#     --key-name $KEY_NAME \
#     --security-group-ids $SG_ID \
#     --region $REGION \
#     --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$EC2_NAME}]" \
#     --user-data file://setup.sh \
#     --query 'Instances[0].InstanceId' \
#     --output text)

# echo "✅ Instance launched: $INSTANCE_ID"
# echo "⏳ Waiting for instance to be running..."
# aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $REGION

# PUBLIC_IP=$(aws ec2 describe-instances \
#     --instance-ids $INSTANCE_ID \
#     --region $REGION \
#     --query 'Reservations[0].Instances[0].PublicIpAddress' \
#     --output text)

# echo "✅ Instance running at: $PUBLIC_IP"

# echo ""
# echo "Step 4: Creating S3 bucket for Flutter Web..."
# aws s3 mb s3://$S3_BUCKET --region $REGION
# aws s3 website s3://$S3_BUCKET \
#     --index-document index.html \
#     --error-document index.html

# aws s3api put-bucket-policy \
#     --bucket $S3_BUCKET \
#     --policy "{
#         \"Version\": \"2012-10-17\",
#         \"Statement\": [{
#             \"Sid\": \"PublicRead\",
#             \"Effect\": \"Allow\",
#             \"Principal\": \"*\",
#             \"Action\": \"s3:GetObject\",
#             \"Resource\": \"arn:aws:s3:::$S3_BUCKET/*\"
#         }]
#     }"
# echo "✅ S3 bucket created: $S3_BUCKET"

# echo ""
# echo "======================================"
# echo "  Deployment Summary"
# echo "======================================"
# echo ""
# echo "Backend IP:    $PUBLIC_IP"
# echo "Backend URL:   http://$PUBLIC_IP:8000"
# echo "S3 Bucket:     $S3_BUCKET"
# echo "S3 URL:        http://$S3_BUCKET.s3-website.$REGION.amazonaws.com"
# echo ""
# echo "Next steps:"
# echo "1. Wait 2 mins for EC2 to finish setup"
# echo "2. Copy backend files: bash copy_backend.sh $PUBLIC_IP"
# echo "3. Build Flutter web: bash deploy_flutter.sh $S3_BUCKET"
# echo ""
# echo "======================================"


# //////////////


#!/bin/bash
# SmartAC AWS Deployment Script
# Run this from your project root: bash deploy.sh

set -e

echo "======================================"
echo "  SmartAC AWS Deployment"
echo "======================================"

# ── Config ────────────────────────────────
REGION="eu-west-2"
EC2_NAME="smartac-backend"
S3_BUCKET="smartac-frontend-$(date +%s)"
KEY_NAME="smartac-key"
INSTANCE_TYPE="t3.small"

# Amazon Linux 2023 AMI for eu-west-2
AMI_ID="ami-0f1b092c39d616d45"

echo ""
echo "Step 1: Creating EC2 key pair..."
aws ec2 create-key-pair \
    --key-name $KEY_NAME \
    --region $REGION \
    --query 'KeyMaterial' \
    --output text > ./smartac-key.pem
chmod 400 ./smartac-key.pem
echo "✅ Key pair saved to ./smartac-key.pem"

echo ""
echo "Step 2: Creating security group..."
SG_ID=$(aws ec2 create-security-group \
    --group-name smartac-sg \
    --description "SmartAC backend security group" \
    --region $REGION \
    --query 'GroupId' \
    --output text)

aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --protocol tcp --port 22 --cidr 0.0.0.0/0 \
    --region $REGION

aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --protocol tcp --port 8000 --cidr 0.0.0.0/0 \
    --region $REGION

aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --protocol tcp --port 80 --cidr 0.0.0.0/0 \
    --region $REGION
echo "✅ Security group created: $SG_ID"

echo ""
echo "Step 3: Launching EC2 instance..."
INSTANCE_ID=$(aws ec2 run-instances \
    --image-id $AMI_ID \
    --instance-type $INSTANCE_TYPE \
    --key-name $KEY_NAME \
    --security-group-ids $SG_ID \
    --region $REGION \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$EC2_NAME}]" \
    --user-data file://setup.sh \
    --query 'Instances[0].InstanceId' \
    --output text)

echo "✅ Instance launched: $INSTANCE_ID"
echo "⏳ Waiting for instance to be running..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $REGION

PUBLIC_IP=$(aws ec2 describe-instances \
    --instance-ids $INSTANCE_ID \
    --region $REGION \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text)

echo "✅ Instance running at: $PUBLIC_IP"

echo ""
echo "Step 4: Creating S3 bucket for Flutter Web..."
aws s3 mb s3://$S3_BUCKET --region $REGION

# Must disable block public access BEFORE setting bucket policy
aws s3api put-public-access-block \
    --bucket $S3_BUCKET \
    --region $REGION \
    --public-access-block-configuration \
    "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"

aws s3 website s3://$S3_BUCKET \
    --index-document index.html \
    --error-document index.html

aws s3api put-bucket-policy \
    --bucket $S3_BUCKET \
    --policy "{
        \"Version\": \"2012-10-17\",
        \"Statement\": [{
            \"Sid\": \"PublicRead\",
            \"Effect\": \"Allow\",
            \"Principal\": \"*\",
            \"Action\": \"s3:GetObject\",
            \"Resource\": \"arn:aws:s3:::$S3_BUCKET/*\"
        }]
    }"
echo "✅ S3 bucket created: $S3_BUCKET"

echo ""
echo "======================================"
echo "  Deployment Summary"
echo "======================================"
echo ""
echo "Backend IP:    $PUBLIC_IP"
echo "Backend URL:   http://$PUBLIC_IP:8000"
echo "S3 Bucket:     $S3_BUCKET"
echo "S3 URL:        http://$S3_BUCKET.s3-website.$REGION.amazonaws.com"
echo ""
echo "Next steps:"
echo "1. Wait 2 mins for EC2 to finish setup"
echo "2. Copy backend files: bash copy_backend.sh $PUBLIC_IP"
echo "3. Build Flutter web: bash deploy_flutter.sh $S3_BUCKET"
echo ""
echo "======================================"