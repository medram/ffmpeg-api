#!/bin/bash
# FFmpeg API Startup Guide

echo "🚀 FFmpeg API - Startup Guide"
echo "=============================="
echo ""

# Step 1: Check FFmpeg installation
echo "1️⃣  Checking FFmpeg installation..."
if command -v ffmpeg &> /dev/null; then
    echo "   ✓ FFmpeg is installed"
    ffmpeg -version | head -n 1
else
    echo "   ❌ FFmpeg is NOT installed"
    echo "   Install it with: sudo apt-get install ffmpeg"
    exit 1
fi

echo ""

# Step 2: Activate virtual environment
echo "2️⃣  Activating virtual environment..."
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "   ✓ Virtual environment activated"
else
    echo "   ❌ Virtual environment not found"
    echo "   Run: uv sync"
    exit 1
fi

echo ""

# Step 3: Check environment variables
echo "3️⃣  Checking environment variables..."
if [ -z "$S3_BUCKET" ]; then
    echo "   ⚠️  S3_BUCKET not set (using default: ffmpeg-output)"
else
    echo "   ✓ S3_BUCKET=$S3_BUCKET"
fi

if [ -z "$AWS_ACCESS_KEY_ID" ]; then
    echo "   ⚠️  AWS_ACCESS_KEY_ID not set"
else
    echo "   ✓ AWS_ACCESS_KEY_ID is set"
fi

if [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "   ⚠️  AWS_SECRET_ACCESS_KEY not set"
else
    echo "   ✓ AWS_SECRET_ACCESS_KEY is set"
fi

echo ""
echo "4️⃣  Configuration (set these environment variables for full S3 functionality):"
echo ""
echo "   export S3_BUCKET=\"your-bucket-name\""
echo "   export AWS_ACCESS_KEY_ID=\"your-access-key\""
echo "   export AWS_SECRET_ACCESS_KEY=\"your-secret-key\""
echo "   export AWS_REGION=\"us-east-1\"  # Optional"
echo ""

echo "5️⃣  Starting the server..."
echo ""
echo "   Run: python -m uvicorn main:main --reload"
echo ""
echo "   Or: python -m main"
echo ""

echo "6️⃣  API Documentation:"
echo ""
echo "   Swagger UI: http://localhost:8000/docs"
echo "   ReDoc: http://localhost:8000/redoc"
echo ""

echo "7️⃣  Quick Test:"
echo ""
echo "   curl http://localhost:8000/health"
echo "   curl http://localhost:8000/ffmpeg/health"
echo ""
