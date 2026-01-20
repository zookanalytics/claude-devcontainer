#!/bin/bash
set -e

# Post-create command for Claude DevContainer base image
# Handles initialization tasks after container creation
# Projects can extend via /workspace/.devcontainer/post-create-project.sh

# Prevent Corepack from prompting during package installations
export COREPACK_ENABLE_DOWNLOAD_PROMPT=0

echo "==============================================="
echo "Starting Claude DevContainer post-create setup..."
echo "==============================================="

# Step 1: Assemble Claude Code managed settings
echo ""
echo "[1/9] Assembling Claude Code managed settings..."
sudo /usr/local/bin/assemble-managed-settings.sh
echo "✓ Managed settings assembled"

# Step 2: DevPod instance isolation (if applicable)
echo ""
echo "[2/9] Checking for DevPod instance isolation..."

# Fix shared-data volume permissions if needed (Docker creates volumes as root)
if [ -n "${SHARED_DATA_DIR:-}" ] && [ -d "$SHARED_DATA_DIR" ] && [ ! -w "$SHARED_DATA_DIR" ]; then
  echo "  Fixing $SHARED_DATA_DIR permissions..."
  sudo /usr/local/bin/fix-shared-data-permissions.sh
fi

# DevPod mode detection - ALL conditions must be true:
# a. SHARED_DATA_DIR environment variable is set AND non-empty
# b. DEVPOD_WORKSPACE_ID environment variable is set AND non-empty
# c. Directory $SHARED_DATA_DIR exists and is writable
DEVPOD_MODE=false

if [ -z "${SHARED_DATA_DIR:-}" ]; then
  echo "  SHARED_DATA_DIR not set (VS Code mode or no shared volume)"
elif [ -z "${DEVPOD_WORKSPACE_ID:-}" ]; then
  echo "  DEVPOD_WORKSPACE_ID not set (not a DevPod workspace)"
elif [ ! -d "$SHARED_DATA_DIR" ]; then
  echo "  $SHARED_DATA_DIR directory does not exist"
elif [ ! -w "$SHARED_DATA_DIR" ]; then
  echo "  $SHARED_DATA_DIR is not writable"
else
  DEVPOD_MODE=true
fi

if [ "$DEVPOD_MODE" = true ]; then
  echo "  DevPod mode detected, running instance isolation..."
  /usr/local/bin/setup-instance-isolation.sh
  echo "✓ Instance isolation complete"
else
  echo "  Skipping instance isolation (not in DevPod mode)"
fi

# Step 3: Check for package updates (daily)
echo ""
echo "[3/9] Checking for package updates..."
/usr/local/bin/check-daily-updates.sh
echo "✓ Package update check complete"

# Step 4: Fix node_modules ownership
echo ""
echo "[4/9] Fixing node_modules ownership..."
sudo /usr/local/bin/fix-node-modules-ownership.sh
echo "✓ Node modules ownership fixed"

# Step 5: Install global pnpm packages
echo ""
echo "[5/9] Installing global pnpm packages..."

# Configure global pnpm to allow build scripts for native dependencies
pnpm config set -g --json onlyBuiltDependencies '["@clerk/shared","@tailwindcss/oxide","cbor-extract","esbuild","ffmpeg-static","sharp","node-pty","protobufjs","tree-sitter-bash"]'

# Read CLI versions from environment (default to latest)
CLAUDE_CODE_VERSION="${CLAUDE_CODE_VERSION:-latest}"
GEMINI_CLI_VERSION="${GEMINI_CLI_VERSION:-latest}"

echo "  - Installing @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}..."
pnpm install -g "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}"

echo "  - Installing @google/gemini-cli@${GEMINI_CLI_VERSION}..."
pnpm install -g "@google/gemini-cli@${GEMINI_CLI_VERSION}"

echo "✓ Global packages installed"

# Step 6: Start dnsmasq for DNS logging
echo ""
echo "[6/9] Starting dnsmasq DNS forwarder..."
sudo /usr/local/bin/start-dnsmasq.sh

# Step 7: Start ulogd for firewall logging
echo ""
echo "[7/9] Starting ulogd firewall logger..."
sudo /usr/local/bin/start-ulogd.sh
echo "✓ ulogd started"

# Step 8: Initialize firewall
echo ""
echo "[8/9] Initializing firewall rules..."
sudo /usr/local/bin/init-firewall.sh
echo "✓ Firewall initialized"

# Step 9: Run project-specific post-create if it exists
echo ""
echo "[9/9] Running project-specific setup..."
PROJECT_POST_CREATE="/workspace/.devcontainer/post-create-project.sh"
if [ -f "$PROJECT_POST_CREATE" ]; then
    echo "Running $PROJECT_POST_CREATE..."
    chmod +x "$PROJECT_POST_CREATE"
    "$PROJECT_POST_CREATE"
    echo "✓ Project-specific setup complete"
else
    echo "No project-specific post-create script found (optional)"
fi

echo ""
echo "==============================================="
echo "Claude DevContainer setup complete!"
echo "==============================================="
