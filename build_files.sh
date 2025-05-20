#!/bin/bash

# Install Python dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput

# Create staticfiles directory if it doesn't exist
mkdir -p staticfiles

# Copy static files to staticfiles directory
cp -r static/* staticfiles/
