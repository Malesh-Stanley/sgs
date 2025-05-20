#!/bin/bash

# Install Python dependencies
python3 -m pip install --no-cache-dir -r requirements.txt

# Create staticfiles directory
mkdir -p staticfiles

# Collect static files
python3 manage.py collectstatic --noinput --clear

# Copy static files to staticfiles directory
cp -r static/* staticfiles/ 2>/dev/null || :
