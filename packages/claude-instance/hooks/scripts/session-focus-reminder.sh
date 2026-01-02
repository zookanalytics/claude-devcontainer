#!/usr/bin/env bash
set -euo pipefail

# Validate required environment variable
if [[ -z "${CLAUDE_PROJECT_DIR:-}" ]]; then
    echo "Error: CLAUDE_PROJECT_DIR environment variable not set" >&2
    exit 1
fi

# Remind Claude to maintain the purpose field in .claude-metadata.json
#
# This hook runs at SessionStart to provide context about the conversation purpose.
# It does NOT tell Claude to act on the previous purpose - just to be aware and update if needed.

METADATA_FILE="$CLAUDE_PROJECT_DIR/.claude-metadata.json"

# Check that jq is installed
if ! command -v jq >/dev/null 2>&1; then
  echo "Note: jq is not installed. Cannot display session purpose."
  echo "Install with: brew install jq (macOS) or apt-get install jq (Ubuntu/Debian)"
  exit 0
fi

if [ -f "$METADATA_FILE" ]; then
  purpose=$(jq -r '.purpose // ""' "$METADATA_FILE" 2>/dev/null)
  if [ -z "$purpose" ] || [ "$purpose" = "null" ]; then
    echo "Session purpose: not set. After the user provides direction, set the purpose field in .claude-metadata.json."
  else
    echo "Previous session purpose was: $purpose"
    echo "Do NOT assume this is current. Wait for user direction, then update the purpose if it has changed."
  fi
else
  echo "No .claude-metadata.json found. After the user provides direction, create it with a purpose field."
fi
