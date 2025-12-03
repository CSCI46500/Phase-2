#!/bin/bash
# Quick start script for local Docker development

echo "🚀 Starting Phase 2 Model Registry (Local Docker Mode)"
echo "=================================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed or not in PATH"
    echo "Please install Docker Desktop from https://www.docker.com/products/docker-desktop"
    exit 1
fi

# Load environment variables
export $(cat .env.docker | grep -v '^#' | xargs)

# Build and start all services
echo "📦 Building Docker images..."
docker compose build

echo "🔧 Starting services (PostgreSQL, MinIO, API, Frontend)..."
docker compose up -d

echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check service health
echo ""
echo "📊 Service Status:"
docker compose ps

echo ""
echo "✅ Services started! Access points:"
echo "   - API: http://localhost:8000"
echo "   - API Docs: http://localhost:8000/docs"
echo "   - Frontend: http://localhost:5173"
echo "   - MinIO Console: http://localhost:9001 (admin/minioadmin123)"
echo "   - PostgreSQL: localhost:5432"
echo ""
echo "📝 View logs:"
echo "   docker compose logs -f api      # API logs"
echo "   docker compose logs -f frontend # Frontend logs"
echo "   docker compose logs -f postgres # Database logs"
echo ""
echo "🛑 Stop services:"
echo "   docker compose down"
echo "   docker compose down -v  # Also remove volumes"
