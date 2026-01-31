#!/bin/bash
# Start script for backend (Linux/Mac)

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
fi

# Start the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

