#!/bin/bash
# setup-claude-auth-sharing.sh
# Copies local Claude auth to shared volume for use by other instances
#
# Run this AFTER authenticating with Claude in the first instance.
# This is a MANUAL operation - explicit user action ensures informed consent.
#
# Usage:
#   setup-claude-auth-sharing
#
# What it does:
#   1. Verifies ~/.claude.json exists (from Claude authentication)
#   2. Copies ~/.claude.json to /shared-data/auth/claude.json (atomic)
#   3. Replaces local file with symlink to shared auth
#   4. Future instances will use the shared auth automatically

set -e

SHARED_DATA="${SHARED_DATA_DIR:-/shared-data}"
LOCAL_AUTH="$HOME/.claude.json"
SHARED_AUTH="$SHARED_DATA/auth/claude.json"
LOCKFILE="$SHARED_DATA/auth/.claude-auth-sharing.lock"

echo "=== Claude Auth Sharing Setup ==="
echo ""

# --- Step 1: Check if already a symlink (already shared) ---
if [ -L "$LOCAL_AUTH" ]; then
  echo "Auth is already shared (symlink exists)."
  echo "  $LOCAL_AUTH -> $(readlink -f "$LOCAL_AUTH")"
  exit 0
fi

# --- Step 2: Check if local auth exists ---
if [ ! -f "$LOCAL_AUTH" ]; then
  echo "ERROR: No auth file found at $LOCAL_AUTH"
  echo ""
  echo "Please authenticate with Claude first:"
  echo "  1. Run 'claude' to start Claude Code"
  echo "  2. Complete the authentication flow"
  echo "  3. Run this script again"
  exit 1
fi

# --- Step 3: Ensure shared directory exists ---
mkdir -p "$SHARED_DATA/auth"

# --- Step 4: Acquire lock to prevent concurrent execution ---
echo "Acquiring lock..."
exec 200>"$LOCKFILE"
if ! flock -n 200; then
  echo "ERROR: Another instance is currently sharing auth."
  echo "Please wait and try again."
  exit 1
fi

# --- Step 5: Check if another instance beat us ---
if [ -f "$SHARED_AUTH" ]; then
  echo "Auth was already shared by another instance."
  echo "Creating local symlink..."

  # Backup local file
  BACKUP="$LOCAL_AUTH.bak"
  if [ -e "$BACKUP" ]; then
    BACKUP="$LOCAL_AUTH.bak.$(date +%s)"
  fi
  mv "$LOCAL_AUTH" "$BACKUP"
  echo "  Local auth backed up to: $BACKUP"

  # Create symlink
  ln -sf "$SHARED_AUTH" "$LOCAL_AUTH"
  echo "  $LOCAL_AUTH -> $SHARED_AUTH"
  echo ""
  echo "Done! Your local Claude auth now uses shared credentials."
  exit 0
fi

# --- Step 6: Copy local auth to shared (atomic: write to .tmp, then mv) ---
echo "Copying auth to shared volume..."
TEMP_FILE="$SHARED_AUTH.tmp.$$"
cp "$LOCAL_AUTH" "$TEMP_FILE"
mv "$TEMP_FILE" "$SHARED_AUTH"
echo "  Copied to: $SHARED_AUTH"

# --- Step 7: Backup and remove local file ---
BACKUP="$LOCAL_AUTH.bak"
if [ -e "$BACKUP" ]; then
  BACKUP="$LOCAL_AUTH.bak.$(date +%s)"
fi
mv "$LOCAL_AUTH" "$BACKUP"
echo "  Local auth backed up to: $BACKUP"

# --- Step 8: Create symlink ---
ln -sf "$SHARED_AUTH" "$LOCAL_AUTH"
echo "  Created symlink: $LOCAL_AUTH -> $SHARED_AUTH"

# --- Step 9: Verify symlink works ---
if [ ! -L "$LOCAL_AUTH" ] || [ ! -r "$LOCAL_AUTH" ]; then
  echo "ERROR: Symlink verification failed!"
  echo "Restoring backup..."
  rm -f "$LOCAL_AUTH"
  mv "$BACKUP" "$LOCAL_AUTH"
  rm -f "$SHARED_AUTH"
  exit 1
fi

# Lock is automatically released on script exit

echo ""
echo "Claude auth shared successfully!"
echo ""
echo "New instances will skip authentication automatically."
echo "Your local backup is at: $BACKUP"
