#!/bin/bash

echo "========================================"
echo "RESTARTING TRAIN CONTROL DASHBOARD"
echo "========================================"

# Kill any existing dashboard processes
echo ""
echo "1. Stopping any running dashboard processes..."
pkill -f "train_control_platform.py" 2>/dev/null || echo "   No running processes found"

# Clear Python cache
echo ""
echo "2. Clearing Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null
echo "   ✓ Python cache cleared"

# Wait a moment
sleep 1

# Start the dashboard
echo ""
echo "3. Starting dashboard..."
echo "========================================"
python3 train_control_platform.py
