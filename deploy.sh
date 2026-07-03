#!/bin/bash
# ARGOS Microservice Deployment Script for VPS
# Run this script on your VPS after cloning the repository

set -e  # Exit on error

echo "🚀 Starting ARGOS deployment..."

# 1. Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Installing..."
    sudo apt update
    sudo apt install python3 python3-venv python3-pip -y
fi

# 2. Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv env

# 3. Activate virtual environment
echo "🔌 Activating virtual environment..."
source env/bin/activate

# 4. Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# 5. Install dependencies
echo "📥 Installing dependencies from requirements.txt..."
pip install -r requirements.txt

# 6. Install Gunicorn for production
echo "🦄 Installing Gunicorn..."
pip install gunicorn

# 7. Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️ .env file not found. Creating template..."
    cat > .env << EOF
FLASK_ENV=production
ICARUS_API_URL=http://localhost:5090/api
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
DEBUG=False
EOF
    echo "✅ .env template created. Please configure it with your settings."
fi

# 8. Test the application
echo "🧪 Testing ARGOS application..."
python3 -c "from ARGOS import app; print('✅ ARGOS module loaded successfully')"

# 9. Display next steps
echo ""
echo "✅ ARGOS deployment completed!"
echo ""
echo "📋 Next steps:"
echo "1. Configure .env file: nano .env"
echo "2. Start Gunicorn: gunicorn --bind 0.0.0.0:8000 --workers 4 ARGOS.wsgi:app"
echo "3. Or use systemd service (see documentation)"
echo ""
echo "🔗 ARGOS will be available at: http://your-vps-ip:8000"
