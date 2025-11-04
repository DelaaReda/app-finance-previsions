#!/bin/bash
# Script to run the ingestion service with proper virtual environment

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies if not already installed
pip3 install -r services/ingestion/requirements.txt

echo "Starting ingestion service..."
python3 services/ingestion/ingestion_service.py