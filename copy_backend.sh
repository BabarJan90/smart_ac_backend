EC2_IP=$1
KEY="./smartac-key.pem"

if [ -z "$EC2_IP" ]; then
    echo "Usage: bash copy_backend.sh <EC2_PUBLIC_IP>"
    exit 1
fi

echo "Copying backend files to EC2..."

# Copy only essential files — exclude venv, __pycache__, .db files
rsync -avz \
    --exclude 'venv/' \
    --exclude '__pycache__/' \
    --exclude '*.pyc' \
    --exclude '*.db' \
    --exclude '.env' \
    -e "ssh -i $KEY -o StrictHostKeyChecking=no" \
    ./backend/ ec2-user@$EC2_IP:/app/

echo "Installing Python dependencies on server..."
ssh -i $KEY -o StrictHostKeyChecking=no ec2-user@$EC2_IP "
    cd /app
    python3.11 -m pip install -r requirements.txt --quiet
"

echo "Enter your Anthropic API key:"
read -s API_KEY

ssh -i $KEY -o StrictHostKeyChecking=no ec2-user@$EC2_IP "
    echo 'ANTHROPIC_API_KEY=$API_KEY' > /app/.env
"

echo "Starting backend service..."
ssh -i $KEY -o StrictHostKeyChecking=no ec2-user@$EC2_IP "
    sudo systemctl restart smartac
    sleep 3
    sudo systemctl status smartac --no-pager
"

echo ""
echo "✅ Backend deployed!"
echo "Test it: curl http://$EC2_IP:8000"