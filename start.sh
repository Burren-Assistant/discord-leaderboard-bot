#!/bin/bash
echo "🚀 Installing dependencies..."
pip install discord.py==2.3.2 flask==2.3.3

echo "🤖 Starting Discord bot..."
python main.py
