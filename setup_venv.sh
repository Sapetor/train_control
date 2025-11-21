#!/bin/bash
# Setup script for Train Control Platform
# Creates virtual environment and installs dependencies

set -e

VENV_DIR="venv"

echo "=== Train Control Platform Setup ==="

# Create virtual environment
if [ -d "$VENV_DIR" ]; then
    echo "Virtual environment already exists. Removing..."
    rm -rf "$VENV_DIR"
fi

echo "Creating virtual environment..."
python3 -m venv "$VENV_DIR"

# Activate and install
echo "Installing dependencies..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "=== Setup Complete ==="
echo "To activate: source venv/bin/activate"
echo "To run:      python train_control_platform.py"
echo "             python multi_train_wrapper.py"
