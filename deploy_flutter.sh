#!/bin/bash
# Usage: bash deploy_flutter.sh <S3_BUCKET> <EC2_IP>
# Example: bash deploy_flutter.sh smartac-frontend-123 54.123.456.789

S3_BUCKET=$1
EC2_IP=$2

if [ -z "$S3_BUCKET" ] || [ -z "$EC2_IP" ]; then
    echo "Usage: bash deploy_flutter.sh <S3_BUCKET> <EC2_IP>"
    exit 1
fi

echo "Step 1: Updating backend URL in Flutter app..."
sed -i '' "s|http://127.0.0.1:8000|http://$EC2_IP:8000|g" \
    flutter/lib/services/api_service.dart 2>/dev/null || \
sed -i '' "s|http://127.0.0.1:8000|http://$EC2_IP:8000|g" \
    flutter/lib/api/smart_ac_api.dart 2>/dev/null

echo "Step 2: Building Flutter Web..."
cd flutter
flutter build web --release
cd ..

echo "Step 3: Uploading to S3..."
aws s3 sync flutter/build/web s3://$S3_BUCKET \
    --delete \
    --cache-control "max-age=31536000" \
    --exclude "index.html"

aws s3 cp flutter/build/web/index.html s3://$S3_BUCKET/index.html \
    --cache-control "no-cache"

REGION="eu-west-2"
echo ""
echo "✅ Flutter Web deployed!"
echo ""
echo "Your app is live at:"
echo "http://$S3_BUCKET.s3-website.$REGION.amazonaws.com"
echo ""
echo "Backend API:"
echo "http://$EC2_IP:8000/docs"
