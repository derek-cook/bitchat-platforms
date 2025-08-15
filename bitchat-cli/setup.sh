#!/bin/bash

# BitChat CLI Setup Script
# Creates virtual environment and installs dependencies

echo "BitChat CLI Setup"
echo "================="

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3.7 or higher."
    exit 1
fi

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "Setup complete!"
echo ""
echo "To use BitChat CLI:"
echo "1. Activate the virtual environment: source venv/bin/activate"
echo "2. Run the CLI: python bitchat_cli.py --name \"Your Name\" --message \"Hello!\""
echo ""
echo "To deactivate the virtual environment when done: deactivate"