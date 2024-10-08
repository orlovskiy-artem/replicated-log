#!/bin/bash

# Get the current directory name
PROJECT_NAME=$(basename "$PWD")

# Append the PROJECT_NAME to the .env file
echo "PROJECT_NAME=$PROJECT_NAME" >> .env

echo "PROJECT_NAME appended to .env file successfully."