#!/bin/bash
# Startup script for SfM Orthomosaic Viewer

echo "🚀 Starting SfM Orthomosaic Tile Viewer..."
echo ""

# Check if config.yaml exists
if [ ! -f "config.yaml" ]; then
    echo "⚠️  Warning: config.yaml not found. Using default configuration."
fi

# Check if data directory exists
if [ ! -d "data" ]; then
    echo "📁 Creating data directory..."
    mkdir -p data
fi

# Load config
if [ -f "config.yaml" ]; then
    PORT=$(grep -A 1 "server:" config.yaml | grep "port:" | awk '{print $2}')
    HOST=$(grep -A 1 "server:" config.yaml | grep "host:" | awk '{print $2}' | tr -d '"')
else
    PORT=8000
    HOST="0.0.0.0"
fi

echo "📋 Configuration:"
echo "   Host: $HOST"
echo "   Port: $PORT"
echo "   Data Directory: $(pwd)/data"
echo ""

# Start server
echo "🌐 Starting server..."
echo "   Open browser to: http://localhost:$PORT"
echo ""
uvicorn main:app --host $HOST --port $PORT --reload
