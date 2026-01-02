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
echo "[1/8] Assembling Claude Code managed settings..."
sudo /usr/local/bin/assemble-managed-settings.sh
echo "✓ Managed settings assembled"

# Step 2: Check for package updates (daily)
echo ""
echo "[2/8] Checking for package updates..."
/usr/local/bin/check-daily-updates.sh
echo "✓ Package update check complete"

# Step 3: Fix node_modules ownership
echo ""
echo "[3/8] Fixing node_modules ownership..."
sudo /usr/local/bin/fix-node-modules-ownership.sh
echo "✓ Node modules ownership fixed"

# Step 4: Install global pnpm packages
echo ""
echo "[4/8] Installing global pnpm packages..."

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

# Step 5: Start dnsmasq for DNS logging
echo ""
echo "[5/8] Starting dnsmasq DNS forwarder..."
sudo /usr/local/bin/start-dnsmasq.sh

# Step 6: Start ulogd for firewall logging
echo ""
echo "[6/8] Starting ulogd firewall logger..."
sudo /usr/local/bin/start-ulogd.sh
echo "✓ ulogd started"

# Step 7: Initialize firewall
echo ""
echo "[7/8] Initializing firewall rules..."
sudo /usr/local/bin/init-firewall.sh
echo "✓ Firewall initialized"

# Step 8: Run project-specific post-create if it exists
echo ""
echo "[8/8] Running project-specific setup..."
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
