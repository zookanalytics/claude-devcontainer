#!/bin/bash
# setup-instance-isolation.sh
# Creates per-instance directories for history while sharing credentials/config
#
# Final architecture (from tech-spec):
#   /shared-data/
#   ├── auth/
#   │   └── claude.json           # Claude OAuth (-> symlink to ~/.claude.json)
#   ├── gemini/                    # SHARED - entire ~/.gemini directory
#   │   ├── oauth_creds.json
#   │   ├── google_accounts.json
#   │   ├── installation_id
#   │   ├── settings.json
#   │   └── tmp/
#   ├── config/
#   │   └── claude-settings.json   # SHARED Claude preferences
#   └── history/                   # PER-INSTANCE isolation
#       └── <instance-id>/
#           ├── claude/            # -> symlink target for ~/.claude
#           │   ├── history.jsonl  # Per-instance conversations
#           │   └── settings.json  # -> symlink to /shared-data/config/claude-settings.json
#           └── zsh_history
#
# Error codes:
#   E001: /shared-data is read-only
#   E002: /shared-data write test timed out
#   E003: DEVPOD_WORKSPACE_ID is not set
#   E004: DEVPOD_WORKSPACE_ID contains invalid characters
#   E005: Failed to create directory
#   E006: Failed to create symlink
#   E007: Symlink verification failed
#   E008: Final health check failed

# --- Testing support ---
# FAIL_AT_STEP: If set, script will fail after completing that step (for rollback testing)
# Example: FAIL_AT_STEP=5 causes exit 1 after step 5

# Track created symlinks and directories for rollback
TRACKING_FILE="/tmp/isolation-$$.created"
TRACKING_DIRS="/tmp/isolation-$$.dirs"
touch "$TRACKING_FILE"
touch "$TRACKING_DIRS"

# Cleanup function (runs on EXIT)
cleanup() {
  local exit_code=$?
  if [ $exit_code -ne 0 ]; then
    echo "ERROR: Script failed, initiating rollback..."
    rollback
  fi
  rm -f "$TRACKING_FILE" 2>/dev/null || true
  rm -f "$TRACKING_DIRS" 2>/dev/null || true
}

# Rollback function - restore backups, remove created symlinks and directories
rollback() {
  echo "Rolling back changes..."

  # Remove symlinks we created
  if [ -f "$TRACKING_FILE" ]; then
    while IFS= read -r symlink; do
      if [ -L "$symlink" ]; then
        echo "  Removing symlink: $symlink"
        rm -f "$symlink"
      fi
    done < "$TRACKING_FILE"
  fi

  # Remove directories we created (in reverse order, only if empty)
  if [ -f "$TRACKING_DIRS" ]; then
    # Read dirs in reverse order (deepest first)
    tac "$TRACKING_DIRS" 2>/dev/null | while IFS= read -r dir; do
      if [ -d "$dir" ] && [ -z "$(ls -A "$dir" 2>/dev/null)" ]; then
        echo "  Removing empty directory: $dir"
        rmdir "$dir" 2>/dev/null || true
      fi
    done
  fi

  # Restore backups
  for backup in "$HOME"/.claude.json.bak* "$HOME"/.claude.bak* "$HOME"/.gemini.bak*; do
    if [ -f "$backup" ] || [ -d "$backup" ]; then
      # Find the original name by removing .bak suffix
      original="${backup%.bak*}"
      if [ ! -e "$original" ]; then
        echo "  Restoring: $backup -> $original"
        mv "$backup" "$original"
      fi
    fi
  done

  echo "Rollback complete. Manual recovery may be needed."
  echo "Check: ~/.claude.json, ~/.claude, ~/.gemini"
}

# Track a symlink for potential rollback
track_symlink() {
  echo "$1" >> "$TRACKING_FILE"
}

# Track a directory for potential rollback (only if we created it)
track_dir() {
  echo "$1" >> "$TRACKING_DIRS"
}

# Check if we should fail at this step (for testing)
check_fail_at_step() {
  local step="$1"
  if [ -n "${FAIL_AT_STEP:-}" ] && [ "$step" -eq "$FAIL_AT_STEP" ]; then
    echo "TEST MODE: Simulating failure at step $step"
    exit 1
  fi
}

# Set up trap BEFORE set -e to ensure cleanup runs
trap cleanup EXIT

set -e

# --- Configuration ---
SHARED_DATA="${SHARED_DATA_DIR:-/shared-data}"
SHARED_DATA_TIMEOUT="${SHARED_DATA_TIMEOUT:-5}"

# --- Step 0: Early checks ---
echo "=== DevPod Instance Isolation Setup ==="
echo ""

# 0a: Verify /shared-data is writable with timeout
echo "[0] Verifying /shared-data is accessible..."
if ! timeout "${SHARED_DATA_TIMEOUT}s" bash -c "touch '$SHARED_DATA/.write-test' && rm '$SHARED_DATA/.write-test'" 2>/dev/null; then
  if [ ! -w "$SHARED_DATA" ]; then
    echo "E001: ERROR: /shared-data is read-only. Check volume mount configuration."
  else
    echo "E002: ERROR: /shared-data write test timed out. Network volume may be unresponsive."
  fi
  exit 1
fi
echo "  /shared-data is writable"

check_fail_at_step 0

# --- Step 1: Validate DEVPOD_WORKSPACE_ID ---
echo ""
echo "[1] Validating DEVPOD_WORKSPACE_ID..."

if [ -z "${DEVPOD_WORKSPACE_ID:-}" ]; then
  echo "E003: ERROR: DEVPOD_WORKSPACE_ID is not set. Cannot proceed with isolation."
  exit 1
fi

# Validate format: alphanumeric, hyphens, underscores only
SANITIZED_ID="${DEVPOD_WORKSPACE_ID//[^a-zA-Z0-9_-]/}"
if [ "$SANITIZED_ID" != "$DEVPOD_WORKSPACE_ID" ]; then
  echo "E004: ERROR: DEVPOD_WORKSPACE_ID contains invalid characters: '$DEVPOD_WORKSPACE_ID'"
  echo "  Allowed: alphanumeric, hyphens, underscores"
  exit 1
fi

INSTANCE_ID="$DEVPOD_WORKSPACE_ID"
echo "  Instance ID: $INSTANCE_ID"

check_fail_at_step 1

# --- Step 2: Create directory structure ---
echo ""
echo "[2] Creating directory structure..."

create_dir() {
  local dir="$1"
  local existed=false
  [ -d "$dir" ] && existed=true

  if ! mkdir -p "$dir"; then
    echo "E005: ERROR: Failed to create directory: $dir"
    exit 1
  fi
  # Verify writable
  if ! timeout "${SHARED_DATA_TIMEOUT}s" bash -c "touch '$dir/.write-test' && rm '$dir/.write-test'" 2>/dev/null; then
    echo "E005: ERROR: Directory not writable: $dir"
    exit 1
  fi

  # Track for rollback only if we created it
  if [ "$existed" = "false" ]; then
    track_dir "$dir"
  fi
  echo "  Created: $dir"
}

create_dir "$SHARED_DATA/auth"
create_dir "$SHARED_DATA/gemini"
create_dir "$SHARED_DATA/config"
create_dir "$SHARED_DATA/history/$INSTANCE_ID/claude"

check_fail_at_step 2

# --- Step 3: Handle existing files (backup if needed) ---
echo ""
echo "[3] Handling existing files..."

backup_if_not_symlink() {
  local path="$1"
  if [ -e "$path" ] && [ ! -L "$path" ]; then
    local backup="$path.bak"
    # If .bak exists, use timestamped version
    if [ -e "$backup" ]; then
      backup="$path.bak.$(date +%s)"
    fi
    echo "  Backing up: $path -> $backup"
    mv "$path" "$backup"
  elif [ -L "$path" ]; then
    echo "  Removing existing symlink: $path"
    rm -f "$path"
  fi
}

backup_if_not_symlink "$HOME/.claude.json"
backup_if_not_symlink "$HOME/.claude"
backup_if_not_symlink "$HOME/.gemini"

check_fail_at_step 3

# --- Step 4: Handle Claude auth bootstrap ---
echo ""
echo "[4] Setting up Claude authentication..."

if [ -f "$SHARED_DATA/auth/claude.json" ]; then
  echo "  Shared auth found, creating symlink..."
  if ! ln -sf "$SHARED_DATA/auth/claude.json" "$HOME/.claude.json"; then
    echo "E006: ERROR: Failed to create symlink: ~/.claude.json -> $SHARED_DATA/auth/claude.json"
    exit 1
  fi
  track_symlink "$HOME/.claude.json"

  # Verify symlink
  if [ ! -L "$HOME/.claude.json" ]; then
    echo "E007: ERROR: Symlink verification failed for: ~/.claude.json"
    exit 1
  fi
  echo "  ~/.claude.json -> $SHARED_DATA/auth/claude.json"
else
  echo "I001: INFO: No shared auth found."
  echo "  Run 'setup-claude-auth-sharing' after first Claude authentication."
fi

check_fail_at_step 4

# --- Step 5: Symlink ~/.claude -> per-instance directory ---
echo ""
echo "[5] Setting up Claude data directory..."

if ! ln -sf "$SHARED_DATA/history/$INSTANCE_ID/claude" "$HOME/.claude"; then
  echo "E006: ERROR: Failed to create symlink: ~/.claude -> $SHARED_DATA/history/$INSTANCE_ID/claude"
  exit 1
fi
track_symlink "$HOME/.claude"

# Verify symlink points to directory
if [ ! -L "$HOME/.claude" ] || [ ! -d "$HOME/.claude" ]; then
  echo "E007: ERROR: Symlink verification failed for: ~/.claude"
  exit 1
fi
echo "  ~/.claude -> $SHARED_DATA/history/$INSTANCE_ID/claude"

check_fail_at_step 5

# --- Step 6: Bootstrap and symlink Claude settings (SHARED) ---
echo ""
echo "[6] Setting up shared Claude settings..."

SETTINGS_FILE="$SHARED_DATA/config/claude-settings.json"
if [ ! -f "$SETTINGS_FILE" ]; then
  echo "  Bootstrapping empty settings file..."
  echo '{}' > "$SETTINGS_FILE"
else
  # Validate JSON, repair if corrupted
  if ! jq empty "$SETTINGS_FILE" 2>/dev/null; then
    echo "  Settings file corrupted, resetting to empty..."
    echo '{}' > "$SETTINGS_FILE"
  fi
fi

# Create symlink inside the per-instance claude directory
if ! ln -sf "$SETTINGS_FILE" "$HOME/.claude/settings.json"; then
  echo "E006: ERROR: Failed to create symlink: ~/.claude/settings.json -> $SETTINGS_FILE"
  exit 1
fi
track_symlink "$HOME/.claude/settings.json"

# Verify symlink
if [ ! -L "$HOME/.claude/settings.json" ]; then
  echo "E007: ERROR: Symlink verification failed for: ~/.claude/settings.json"
  exit 1
fi
echo "  ~/.claude/settings.json -> $SETTINGS_FILE"

check_fail_at_step 6

# --- Step 7: Symlink ~/.gemini -> shared directory ---
echo ""
echo "[7] Setting up Gemini directory (shared)..."

if ! ln -sf "$SHARED_DATA/gemini" "$HOME/.gemini"; then
  echo "E006: ERROR: Failed to create symlink: ~/.gemini -> $SHARED_DATA/gemini"
  exit 1
fi
track_symlink "$HOME/.gemini"

# Verify symlink
if [ ! -L "$HOME/.gemini" ]; then
  echo "E007: ERROR: Symlink verification failed for: ~/.gemini"
  exit 1
fi
echo "  ~/.gemini -> $SHARED_DATA/gemini"

check_fail_at_step 7

# --- Step 8: Configure ZSH HISTFILE ---
echo ""
echo "[8] Configuring ZSH history isolation..."

HISTFILE_PATH="$SHARED_DATA/history/$INSTANCE_ID/zsh_history"
touch "$HISTFILE_PATH"

# Disable any existing HISTFILE exports in .zshrc
if [ -f "$HOME/.zshrc" ]; then
  sed -i 's/^export HISTFILE=/#DISABLED_BY_ISOLATION# export HISTFILE=/' "$HOME/.zshrc" 2>/dev/null || true
fi

# Use marker line for idempotent updates
MARKER_LINE="# [setup-instance-isolation] export HISTFILE=\"$HISTFILE_PATH\""

if grep -q "\[setup-instance-isolation\]" "$HOME/.zshrc" 2>/dev/null; then
  # Update existing line
  sed -i "s|.*\[setup-instance-isolation\].*|$MARKER_LINE|" "$HOME/.zshrc"
  echo "  Updated HISTFILE in .zshrc"
else
  # Append new line
  echo "" >> "$HOME/.zshrc"
  echo "$MARKER_LINE" >> "$HOME/.zshrc"
  echo "  Added HISTFILE to .zshrc"
fi

# Set in this script's environment (new zsh sessions will read from .zshrc)
export HISTFILE="$HISTFILE_PATH"
echo "  HISTFILE=$HISTFILE_PATH (effective on next shell session)"

check_fail_at_step 8

# --- Step 9: Final health check ---
echo ""
echo "[9] Running final health check..."

verify_writable() {
  local path="$1"
  local target
  if [ -L "$path" ]; then
    target=$(readlink -f "$path")
  else
    target="$path"
  fi

  if [ -d "$target" ]; then
    if ! timeout "${SHARED_DATA_TIMEOUT}s" bash -c "touch '$target/.health-check' && rm '$target/.health-check'" 2>/dev/null; then
      return 1
    fi
  elif [ -f "$target" ]; then
    if [ ! -w "$target" ]; then
      return 1
    fi
  fi
  return 0
}

HEALTH_CHECK_FAILED=false

if ! verify_writable "$HOME/.claude"; then
  echo "  WARNING: ~/.claude is not writable"
  HEALTH_CHECK_FAILED=true
fi

if ! verify_writable "$HOME/.gemini"; then
  echo "  WARNING: ~/.gemini is not writable"
  HEALTH_CHECK_FAILED=true
fi

if [ "$HEALTH_CHECK_FAILED" = true ]; then
  echo "E008: ERROR: Final health check failed. Rolling back..."
  exit 1
fi
echo "  All symlinks verified writable"

check_fail_at_step 9

# --- Step 10: Export CLAUDE_INSTANCE ---
echo ""
echo "[10] Exporting instance ID..."

INSTANCE_MARKER_LINE="# [setup-instance-isolation] export CLAUDE_INSTANCE=\"$INSTANCE_ID\""

if grep -q "CLAUDE_INSTANCE=" "$HOME/.zshrc" 2>/dev/null; then
  # Update existing line
  sed -i "s|.*CLAUDE_INSTANCE=.*|$INSTANCE_MARKER_LINE|" "$HOME/.zshrc"
else
  # Append new line
  echo "$INSTANCE_MARKER_LINE" >> "$HOME/.zshrc"
fi

export CLAUDE_INSTANCE="$INSTANCE_ID"
echo "  CLAUDE_INSTANCE=$INSTANCE_ID"

check_fail_at_step 10

# --- Success ---
echo ""
echo "I002: INFO: Instance isolation complete for: $INSTANCE_ID"
echo ""
echo "Summary:"
echo "  Instance ID:      $INSTANCE_ID"
echo "  ZSH history:      $SHARED_DATA/history/$INSTANCE_ID/zsh_history"
echo "  Claude data:      $SHARED_DATA/history/$INSTANCE_ID/claude/"
echo "  Claude settings:  $SHARED_DATA/config/claude-settings.json (shared)"
echo "  Gemini:           $SHARED_DATA/gemini/ (shared)"

if [ ! -f "$SHARED_DATA/auth/claude.json" ]; then
  echo ""
  echo "NOTE: No shared Claude auth found. After authenticating with 'claude',"
  echo "      run 'setup-claude-auth-sharing' to share credentials with other instances."
fi
