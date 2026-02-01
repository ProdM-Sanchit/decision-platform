#!/bin/bash

# Decision Platform - One-Command Deployment Script
# Usage: ./deploy.sh [development|production]

set -e  # Exit on error

MODE=${1:-development}
COMPOSE_FILE="docker-compose.yml"

if [ "$MODE" = "production" ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
fi

echo "========================================="
echo "Decision Platform Deployment"
echo "Mode: $MODE"
echo "========================================="
echo

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your configuration before continuing."
    echo "   Minimum required: SECRET_KEY, POSTGRES_PASSWORD"
    echo
    read -p "Press Enter after you've updated .env..."
fi

# Validate critical env vars
echo "🔍 Validating configuration..."
source .env

if [ "$SECRET_KEY" = "your-super-secret-key-change-this-in-production-use-openssl-rand-hex-32" ]; then
    echo "❌ ERROR: Please change SECRET_KEY in .env file"
    echo "   Generate one with: openssl rand -hex 32"
    exit 1
fi

if [ -z "$POSTGRES_PASSWORD" ] || [ "$POSTGRES_PASSWORD" = "change-this-secure-database-password" ]; then
    echo "❌ ERROR: Please set POSTGRES_PASSWORD in .env file"
    exit 1
fi

echo "✓ Configuration validated"
echo

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose -f $COMPOSE_FILE down 2>/dev/null || true
echo

# Build images
echo "🔨 Building Docker images..."
docker-compose -f $COMPOSE_FILE build --no-cache
echo

# Start services
echo "🚀 Starting services..."
docker-compose -f $COMPOSE_FILE up -d
echo

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check health
MAX_RETRIES=30
RETRY=0
while [ $RETRY -lt $MAX_RETRIES ]; do
    if docker-compose -f $COMPOSE_FILE ps | grep -q "healthy"; then
        break
    fi
    echo "   Waiting... ($RETRY/$MAX_RETRIES)"
    sleep 2
    RETRY=$((RETRY+1))
done

if [ $RETRY -eq $MAX_RETRIES ]; then
    echo "❌ Services failed to become healthy"
    docker-compose -f $COMPOSE_FILE logs
    exit 1
fi

echo "✓ Services are healthy"
echo

# Initialize database
echo "📊 Initializing database..."
docker-compose -f $COMPOSE_FILE exec -T api python scripts/init_db.py
echo

# Run tests (optional)
if [ "$MODE" = "production" ]; then
    echo "✅ Deployment complete!"
else
    echo "🧪 Running quick health check..."
    sleep 5
    HEALTH=$(curl -s http://localhost:8000/health || echo "failed")
    if [[ $HEALTH == *"healthy"* ]]; then
        echo "✓ API is healthy"
    else
        echo "❌ API health check failed"
        docker-compose -f $COMPOSE_FILE logs api
        exit 1
    fi
fi

echo
echo "========================================="
echo "✅ Deployment Successful!"
echo "========================================="
echo
echo "Services:"
echo "  API:      http://localhost:${API_PORT:-8000}"
echo "  API Docs: http://localhost:${API_PORT:-8000}/docs"
echo "  Frontend: http://localhost:${FRONTEND_PORT:-3000}"
echo "  MinIO:    http://localhost:${MINIO_CONSOLE_PORT:-9001}"
echo
echo "Default Credentials:"
echo "  Email:    admin@example.com"
echo "  Password: admin123"
echo "  ⚠️  CHANGE PASSWORD IMMEDIATELY!"
echo
echo "Useful Commands:"
echo "  View logs:    docker-compose -f $COMPOSE_FILE logs -f"
echo "  Stop:         docker-compose -f $COMPOSE_FILE down"
echo "  Restart:      docker-compose -f $COMPOSE_FILE restart"
echo
echo "For more information, see DEPLOYMENT.md"
echo
