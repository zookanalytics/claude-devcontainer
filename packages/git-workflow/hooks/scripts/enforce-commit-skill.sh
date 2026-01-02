#!/usr/bin/env bash
#
# enforce-commit-skill.sh
#
# PreToolUse hook for Bash commands that ensures the creating-commits skill
# workflow is followed before any git commit.
#
# Exit codes:
#   0 - Command is allowed
#   2 - Command is blocked (provides feedback to Claude)

set -euo pipefail

# Validate required environment variable
if [[ -z "${CLAUDE_PROJECT_DIR:-}" ]]; then
    echo "Error: CLAUDE_PROJECT_DIR environment variable not set" >&2
    exit 1
fi

# Read JSON input from stdin
input=$(cat)

# Extract tool name and command from JSON
tool_name=$(echo "$input" | jq -r '.tool_name // ""')
command=$(echo "$input" | jq -r '.tool_input.command // ""')

# Only process Bash commands
if [[ "$tool_name" != "Bash" ]]; then
    exit 0
fi

# Only process git commit commands (not git commit --amend which is handled separately)
if ! echo "$command" | grep -qE '^\s*git\s+commit(\s|$)'; then
    exit 0
fi

# Allow git commit --amend (special case for pre-commit hook fixes)
if echo "$command" | grep -qE '(\s|^)--amend\b'; then
    exit 0
fi

STATE_FILE="$CLAUDE_PROJECT_DIR/.claude/.commit-state.json"

# Check if state file exists
if [[ ! -f "$STATE_FILE" ]]; then
    cat >&2 <<EOF
🚫 Commit blocked - creating-commits skill not followed

You MUST use the 'creating-commits' skill before committing.

Required workflow:
1. Use Skill tool: Skill(creating-commits)
2. Follow ALL checklist steps (use TodoWrite for tracking):
   - Run 'pnpm fix' to auto-fix and validate
   - Review changes with 'git diff'
   - Stage files with 'git add <files>'
   - Preview staged changes with 'git diff --staged'
   - Prepare commit message following conventional commits
   - Write commit state file (.claude/.commit-state.json)
   - Create commit

This ensures commits:
✓ Pass pre-commit hooks
✓ Follow atomic commit principles
✓ Use proper conventional commit format
✓ Maintain clean git history

Never skip this workflow - even for "simple" changes.
Simple changes cause hook failures too.
EOF
    exit 2
fi

# Verify state file is recent (within last 5 minutes)
if [[ "$(uname)" == "Darwin" ]]; then
    file_age=$(($(date +%s) - $(stat -f %m "$STATE_FILE")))
else
    file_age=$(($(date +%s) - $(stat -c %Y "$STATE_FILE")))
fi

if [[ $file_age -gt 300 ]]; then
    cat >&2 <<EOF
🚫 Commit blocked - stale commit state

The commit state file is older than 5 minutes.

Please re-run the 'creating-commits' skill to ensure fresh validation
before committing. This prevents accidentally committing without running
recent quality checks.

Run: Skill(creating-commits)
EOF
    rm -f "$STATE_FILE"
    exit 2
fi

# Verify workflow was completed
if ! jq -e '.workflow_completed == true' "$STATE_FILE" >/dev/null 2>&1; then
    cat >&2 <<EOF
🚫 Commit blocked - incomplete workflow

The commit state file exists but does not indicate workflow completion.

Please re-run the 'creating-commits' skill and complete all steps.
EOF
    rm -f "$STATE_FILE"
    exit 2
fi

# Clean up state file on successful validation
rm -f "$STATE_FILE"

# Allow commit to proceed
exit 0
