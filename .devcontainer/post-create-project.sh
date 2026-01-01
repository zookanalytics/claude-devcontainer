#!/bin/bash
set -e

# Project-specific post-create setup
# This script is called by the base image's post-create.sh

echo "Running project-specific setup..."

# Install dependencies (uncomment as needed)
# pnpm install

# Install Playwright browsers (if using Playwright)
# pnpm exec playwright install

# Add any other project-specific initialization here

echo "✓ Project setup complete!"
