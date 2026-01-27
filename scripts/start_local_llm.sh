#!/bin/bash
# Nexus Agent - Local LLM Setup Script
# This script installs and starts Ollama with Qwen2.5-14B

set -e

echo "🚀 Nexus Agent - Local LLM Setup"
echo "=================================="

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama not found. Installing..."
    
    # Detect OS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install ollama
        else
            echo "Please install Homebrew first: https://brew.sh"
            exit 1
        fi
    else
        # Linux
        curl -fsSL https://ollama.com/install.sh | sh
    fi
    
    echo "✅ Ollama installed successfully"
else
    echo "✅ Ollama already installed"
fi

# Start Ollama service in background
echo ""
echo "🔧 Starting Ollama service..."
ollama serve > /dev/null 2>&1 &
OLLAMA_PID=$!

# Wait for service to be ready
sleep 3

# Pull Qwen2.5-14B model
echo ""
echo "📦 Downloading Qwen2.5-14B model (this may take a few minutes)..."
ollama pull qwen2.5:14b

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Configuration:"
echo "   LLM_BASE_URL: http://localhost:11434/v1"
echo "   LLM_MODEL: qwen2.5:14b"
echo "   LLM_API_KEY: (any value, not validated)"
echo ""
echo "🔗 Ollama is running on port 11434"
echo "   To stop: kill $OLLAMA_PID"
echo "   To test: curl http://localhost:11434/api/tags"
echo ""
echo "💡 Next steps:"
echo "   1. Start embedding server: python scripts/start_embedding_server.py"
echo "   2. Start Nexus Agent: docker-compose up"
