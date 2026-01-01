#!/bin/bash
# Fix ownership of node_modules volume for the node user
# This runs once during container creation

chown -R node:node /workspace/node_modules 2>/dev/null || true
