#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PACKAGE_DIR="$SCRIPT_DIR/.."
WORKFLOWS_DIR="$PACKAGE_DIR/workflows"
CONFIG_DIR="$PACKAGE_DIR/config"

# Validate package structure
if [ ! -d "$WORKFLOWS_DIR" ]; then
  echo "ERROR: Workflows directory not found at $WORKFLOWS_DIR" >&2
  exit 1
fi
if [ ! -d "$CONFIG_DIR" ]; then
  echo "ERROR: Config directory not found at $CONFIG_DIR" >&2
  exit 1
fi

# 1. Install workflows to ~/.keystone/workflows/
# Uses ln -sf to force-overwrite existing symlinks (handles updates cleanly)
WORKFLOW_TARGET="$HOME/.keystone/workflows"
mkdir -p "$WORKFLOW_TARGET"
WORKFLOW_COUNT=0
for f in "$WORKFLOWS_DIR"/*.yaml; do
  [ -e "$f" ] || continue  # Handle no matches
  ln -sf "$f" "$WORKFLOW_TARGET/$(basename "$f")"  # -f overwrites existing
  WORKFLOW_COUNT=$((WORKFLOW_COUNT + 1))
done
if [ "$WORKFLOW_COUNT" -eq 0 ]; then
  echo "WARNING: No workflow files found in $WORKFLOWS_DIR" >&2
else
  echo "Keystone workflows installed to $WORKFLOW_TARGET ($WORKFLOW_COUNT files)"
fi

# 2. Install default config to ~/.config/keystone/ (only if not exists)
CONFIG_TARGET="$HOME/.config/keystone"
if [ ! -f "$CONFIG_TARGET/config.yaml" ]; then
  mkdir -p "$CONFIG_TARGET"
  if [ -f "$CONFIG_DIR/keystone-config.yaml" ]; then
    cp "$CONFIG_DIR/keystone-config.yaml" "$CONFIG_TARGET/config.yaml"
    echo "Default keystone config installed to $CONFIG_TARGET/config.yaml"
  else
    echo "WARNING: Default config not found at $CONFIG_DIR/keystone-config.yaml" >&2
  fi
else
  echo "Keystone config already exists at $CONFIG_TARGET/config.yaml (skipped)"
fi
