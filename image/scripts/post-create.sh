#!/bin/bash
set -euo pipefail

# Post-create command for Claude DevContainer base image
# Handles initialization tasks after container creation
# Projects can extend via <workspace>/.devcontainer/post-create-project.sh

# Detect workspace root - environment variable or git root fallback
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

# Prevent Corepack from prompting during package installations
export COREPACK_ENABLE_DOWNLOAD_PROMPT=0

echo "==============================================="
echo "Starting Claude DevContainer post-create setup..."
echo "==============================================="

# Step 1: Assemble Claude Code managed settings
echo ""
echo "[1/11] Assembling Claude Code managed settings..."
sudo /usr/local/bin/assemble-managed-settings.sh
echo "✓ Managed settings assembled"

# Step 2: DevPod instance isolation (if applicable)
echo ""
echo "[2/11] Checking for DevPod instance isolation..."

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
echo "[3/11] Checking for package updates..."
/usr/local/bin/check-daily-updates.sh
echo "✓ Package update check complete"

# Step 4: Fix node_modules ownership
echo ""
echo "[4/11] Fixing node_modules ownership..."
sudo /usr/local/bin/fix-node-modules-ownership.sh
echo "✓ Node modules ownership fixed"

# Step 5: Install CLI tools
echo ""
echo "[5/11] Installing CLI tools..."

# Install Claude Code via official installer (https://claude.ai/install.sh)
# Security note: Piping to bash is the official install method. The script is served
# over HTTPS from Anthropic's domain. For additional security, you could download,
# inspect, and run manually, but this would break automated container builds.
# CLAUDE_CODE_VERSION can be: empty (latest), "stable", or specific version like "1.0.58"
CLAUDE_CODE_VERSION="${CLAUDE_CODE_VERSION:-}"
if [ -n "$CLAUDE_CODE_VERSION" ]; then
  echo "  - Installing Claude Code (version: $CLAUDE_CODE_VERSION)..."
  if ! curl -fsSL https://claude.ai/install.sh | bash -s "$CLAUDE_CODE_VERSION"; then
    echo "  ⚠ Claude Code installation failed for version: $CLAUDE_CODE_VERSION"
    echo "  Check https://claude.ai/install.sh for valid versions"
  fi
else
  echo "  - Installing Claude Code (latest)..."
  if ! curl -fsSL https://claude.ai/install.sh | bash; then
    echo "  ⚠ Claude Code installation failed"
  fi
fi

# Verify Claude Code installation
if command -v claude >/dev/null 2>&1; then
  echo "  ✓ Claude Code installed: $(claude --version 2>/dev/null || echo 'version unknown')"
else
  echo "  ⚠ Claude Code binary not found in PATH after installation"
fi

# Install Gemini CLI via pnpm
GEMINI_CLI_VERSION="${GEMINI_CLI_VERSION:-latest}"
echo "  - Installing @google/gemini-cli@${GEMINI_CLI_VERSION}..."
pnpm install -g "@google/gemini-cli@${GEMINI_CLI_VERSION}"

echo "✓ CLI tools installed"

# Step 6: Update keystone packages
echo ""
echo "[6/11] Updating keystone packages..."
/usr/local/bin/update-keystone.sh
echo "✓ Keystone packages updated"

# Step 7: Start dnsmasq for DNS logging
echo ""
echo "[7/11] Starting dnsmasq DNS forwarder..."
sudo /usr/local/bin/start-dnsmasq.sh

# Step 8: Start ulogd for firewall logging
echo ""
echo "[8/11] Starting ulogd firewall logger..."
sudo /usr/local/bin/start-ulogd.sh
echo "✓ ulogd started"

# Step 9: Initialize firewall
echo ""
echo "[9/11] Initializing firewall rules..."
sudo /usr/local/bin/init-firewall.sh
echo "✓ Firewall initialized"

# Step 10: Run sanity check
echo ""
echo "[10/11] Running sanity check..."
if /usr/local/bin/devcontainer-sanity-check.sh; then
  echo "✓ Sanity check passed"
else
  echo "⚠ Sanity check reported failures (see above) - container continues"
fi

# Step 11: Run project-specific post-create if it exists
echo ""
echo "[11/11] Running project-specific setup..."
PROJECT_POST_CREATE="$WORKSPACE_ROOT/.devcontainer/post-create-project.sh"
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
