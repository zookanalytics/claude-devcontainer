#!/bin/bash
# register-plugin-marketplaces.sh
# Auto-registers Claude Code plugin marketplaces defined in project settings.
#
# Reads extraKnownMarketplaces from <workspace>/.claude/settings.json and
# registers each via `claude plugin marketplace add` so enabled plugins
# resolve without manual intervention.
#
# Usage: register-plugin-marketplaces.sh [workspace-root]

set -euo pipefail

WORKSPACE_ROOT="${1:-${WORKSPACE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}}"
PROJECT_SETTINGS="$WORKSPACE_ROOT/.claude/settings.json"

if ! command -v claude >/dev/null 2>&1; then
  echo "  Claude Code not installed, skipping marketplace registration"
  exit 0
fi

if [ ! -f "$PROJECT_SETTINGS" ]; then
  echo "  No project settings found at $PROJECT_SETTINGS"
  exit 0
fi

# Extract git URLs from extraKnownMarketplaces
URLS=$(jq -r '
  .extraKnownMarketplaces // {} |
  to_entries[] |
  select(.value.source.source == "git") |
  .value.source.url
' "$PROJECT_SETTINGS" 2>/dev/null)

if [ -z "$URLS" ]; then
  echo "  No extraKnownMarketplaces defined in project settings"
  exit 0
fi

echo "$URLS" | while read -r url; do
  echo "  Registering marketplace: $url"
  if claude plugin marketplace add "$url" 2>&1; then
    echo "  ✓ Registered: $url"
  else
    echo "  ⚠ Failed to register: $url"
  fi
done
