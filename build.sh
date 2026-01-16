#!/bin/bash
echo "🔧 Setting up Python 3.10.13 environment..."
python --version
echo "Installing dependencies..."
pip install --upgrade pip
pip install discord.py==2.3.2
pip install flask==2.3.3
echo "✅ All dependencies installed!"
