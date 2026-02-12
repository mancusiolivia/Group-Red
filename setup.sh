#!/bin/bash
# Linux/Mac shell script for easy setup
# This script installs dependencies and runs the setup

echo "============================================================"
echo "Essay Testing System - Setup Script"
echo "============================================================"
echo ""

echo "Step 1: Installing Python dependencies..."
if command -v pip3 &> /dev/null; then
    pip3 install -r server/requirements.txt
elif command -v pip &> /dev/null; then
    pip install -r server/requirements.txt
else
    echo "ERROR: pip not found. Please install pip first."
    exit 1
fi

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Failed to install dependencies."
    exit 1
fi

echo ""
echo "Step 2: Running database setup..."
if command -v python3 &> /dev/null; then
    python3 setup.py
elif command -v python &> /dev/null; then
    python setup.py
else
    echo "ERROR: Python not found. Please install Python first."
    exit 1
fi

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Setup failed. Please check the errors above."
    exit 1
fi

echo ""
echo "============================================================"
echo "Setup Complete!"
echo "============================================================"
echo ""
echo "Next: Create a .env file with your API key:"
echo "   TOGETHER_AI_API_KEY=your_api_key_here"
echo ""
echo "Then start the server with:"
echo "   python3 run_server.py"
echo ""
