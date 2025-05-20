#!/bin/bash

# Install Python dependencies
python3 -m pip install -r requirements.txt

# Collect static files
python3 manage.py collectstatic --noinput

# Create staticfiles directory if it doesn't exist
mkdir -p staticfiles

# Copy static files to staticfiles directory
cp -r static/* staticfiles/
