#!/bin/bash
# ARGOS Deployment Script for VPS
# This script deploys ARGOS microservice to the VPS

set -e

echo "🚀 Deploying ARGOS Face Recognition Microservice..."

# Variables
DEPLOY_USER="root"
DEPLOY_HOST="194.164.171.217"
REMOTE_PATH="/var/apps/icarus/microservicios/argos"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 1. Build locally (optional, for testing)
echo -e "${YELLOW}📦 Building ARGOS Docker image locally...${NC}"
docker build -f Dockerfile -t argos:latest .

# 2. Create remote directory structure
echo -e "${YELLOW}📁 Creating remote directories...${NC}"
ssh ${DEPLOY_USER}@${DEPLOY_HOST} "mkdir -p ${REMOTE_PATH}/{logs,ARGOS}"

# 3. Copy files to VPS
echo -e "${YELLOW}📤 Copying files to VPS...${NC}"
rsync -avz --progress \
    --exclude='env/' \
    --exclude='env_new/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='.git/' \
    --exclude='logs/*.log' \
    ./ ${DEPLOY_USER}@${DEPLOY_HOST}:${REMOTE_PATH}/

# 4. Deploy on VPS
echo -e "${YELLOW}🐳 Building and starting ARGOS container on VPS...${NC}"
ssh ${DEPLOY_USER}@${DEPLOY_HOST} << 'ENDSSH'
cd /var/apps/icarus/microservicios/argos

# Stop and remove old container
docker stop argos 2>/dev/null || true
docker rm argos 2>/dev/null || true

# Build new image
docker build -f Dockerfile -t argos:latest .

# Start container
docker run -d \
    --name argos \
    --network trajano-shared-network \
    --restart unless-stopped \
    --env-file .env.production \
    -v $(pwd)/logs:/app/logs \
    argos:latest

# Wait for container to be healthy
echo "⏳ Waiting for ARGOS to be ready..."
sleep 10

# Check health
if docker exec argos curl -f http://localhost:5000/health > /dev/null 2>&1; then
    echo "✅ ARGOS is healthy!"
else
    echo "❌ ARGOS health check failed!"
    docker logs argos --tail 50
    exit 1
fi

echo "📊 ARGOS container status:"
docker ps | grep argos

ENDSSH

echo -e "${GREEN}✅ ARGOS deployed successfully!${NC}"
echo ""
echo "📋 Next steps:"
echo "  - Check logs: ssh ${DEPLOY_USER}@${DEPLOY_HOST} 'docker logs argos -f'"
echo "  - Health check: ssh ${DEPLOY_USER}@${DEPLOY_HOST} 'docker exec argos curl http://localhost:5000/health'"
echo "  - Update ICARUS.API to use: http://argos:5000"
