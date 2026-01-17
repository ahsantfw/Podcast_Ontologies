#!/bin/bash
# Quick setup script for Qdrant (Neo4j runs on cloud)

set -e

echo "🚀 Setting up services for Knowledge Graph Pipeline"
echo "=================================================="
echo ""
echo "ℹ️  Note: Neo4j is running on cloud (configure in .env)"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Try docker compose (newer) first, fallback to docker-compose
if docker compose version > /dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
elif docker-compose version > /dev/null 2>&1; then
    DOCKER_COMPOSE="docker-compose"
else
    echo "❌ Neither 'docker compose' nor 'docker-compose' is available."
    exit 1
fi

# Check if Qdrant already exists
if docker ps -a --format '{{.Names}}' | grep -q "^qdrant$"; then
    echo "⚠️  Qdrant container already exists"
    read -p "Remove and recreate? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker rm -f qdrant 2>/dev/null || true
    else
        echo "Starting existing Qdrant container..."
        docker start qdrant
    fi
else
    echo "📊 Starting Qdrant..."
    docker run -d \
        --name qdrant \
        -p 6333:6333 \
        -p 6334:6334 \
        qdrant/qdrant
    echo "✅ Qdrant started"
fi

# Wait for Qdrant to be ready
echo "⏳ Waiting for Qdrant to be ready..."
sleep 5

# Verify services
echo ""
echo "🔍 Verifying services..."
echo ""

# Check Qdrant
if docker ps --format '{{.Names}}' | grep -q "^qdrant$"; then
    echo "✅ Qdrant is running"
    echo "   HTTP: http://localhost:6333"
    echo "   Dashboard: http://localhost:6333/dashboard"
else
    echo "❌ Qdrant is not running"
fi

echo ""
echo "=================================================="
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Configure .env file:"
echo "   - Set NEO4J_URI to your Neo4j Cloud URI (e.g., neo4j+s://xxx.databases.neo4j.io)"
echo "   - Set NEO4J_USER and NEO4J_PASSWORD"
echo "   - Set OPENAI_API_KEY"
echo "2. Install dependencies: pip install -r requirements.txt"
echo "3. Run: python main.py process --input data/transcripts/"
echo "4. Query: python main.py query"
echo ""

