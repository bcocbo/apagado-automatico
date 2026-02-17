#!/bin/bash
# Start backend with AWS credentials from environment

# Export AWS credentials if they exist
if [ -n "$AWS_ACCESS_KEY_ID" ]; then
    export AWS_ACCESS_KEY_ID
fi
if [ -n "$AWS_SECRET_ACCESS_KEY" ]; then
    export AWS_SECRET_ACCESS_KEY
fi
if [ -n "$AWS_SESSION_TOKEN" ]; then
    export AWS_SESSION_TOKEN
fi
if [ -n "$AWS_REGION" ]; then
    export AWS_REGION
fi

# Run the Python backend
exec python3 run-production.py
