#!/bin/bash
# Nexus Agent - Complete Local Deployment Guide

set -e

echo "🚀 Nexus Agent - Local Deployment Setup"
echo "========================================"
echo ""

# Step 1: Ollama Setup
echo "📦 Step 1/3: Setting up Ollama (LLM)"
echo "-----------------------------------"
if ! command -v ollama &> /dev/null; then
    echo "Installing Ollama..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install ollama
    else
        curl -fsSL https://ollama.com/install.sh | sh
    fi
fi

echo "Starting Ollama service..."
ollama serve > /tmp/ollama.log 2>&1 &
OLLAMA_PID=$!
echo "Ollama PID: $OLLAMA_PID"
sleep 3

echo "Pulling Qwen2.5-14B model..."
ollama pull qwen2.5:14b

echo "✅ Ollama ready on port 11434"
echo ""

# Step 2: Embedding Server Setup
echo "🧠 Step 2/3: Setting up Local Embedding Server"
echo "----------------------------------------------"
echo "Installing Python dependencies..."
pip install -q sentence-transformers torch fastapi uvicorn

echo "Starting embedding server..."
python scripts/start_embedding_server.py --port 9292 > /tmp/embedding.log 2>&1 &
EMBEDDING_PID=$!
echo "Embedding Server PID: $EMBEDDING_PID"
sleep 5

echo "✅ Embedding server ready on port 9292"
echo ""

# Step 3: Nexus Agent
echo "🤖 Step 3/3: Starting Nexus Agent"
echo "---------------------------------"
echo "Building Docker containers..."
docker-compose up -d --build

echo ""
echo "✅ All services started successfully!"
echo ""
echo "📋 Service Status:"
echo "   - Ollama (LLM):        http://localhost:11434 (PID: $OLLAMA_PID)"
echo "   - Embedding Server:    http://localhost:9292 (PID: $EMBEDDING_PID)"
echo "   - Nexus Agent API:     http://localhost:8000"
echo "   - PostgreSQL:          localhost:5432"
echo "   - Redis:               localhost:6379"
echo ""
echo "📝 Logs:"
echo "   - Ollama:      tail -f /tmp/ollama.log"
echo "   - Embedding:   tail -f /tmp/embedding.log"
echo "   - Nexus:       docker-compose logs -f nexus-app"
echo ""
echo "🛑 To stop all services:"
echo "   kill $OLLAMA_PID $EMBEDDING_PID && docker-compose down"
echo ""
echo "💡 Next: Test with 'curl http://localhost:8000/'"
