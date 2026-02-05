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

# Read JSON input from stdin
input=$(cat)

# Extract tool name and command from JSON
tool_name=$(echo "$input" | jq -r '.tool_name // ""')
command=$(echo "$input" | jq -r '.tool_input.command // ""')

# Only process Bash commands
if [[ "$tool_name" != "Bash" ]]; then
    exit 0
fi

# Only process commands containing git commit (not git commit --amend which is handled separately)
# Match "git" followed by optional flags (like --no-pager, -C path) then "commit"
# This prevents bypass via global git flags (e.g., "git --no-pager commit")
if ! echo "$command" | grep -qE '\bgit\b.*\bcommit\b'; then
    exit 0
fi

# Allow git commit --amend (special case for pre-commit hook fixes)
# Check that --amend appears as a real flag (before any quotes), not inside a commit message
# e.g., "git commit --amend" OK, but "git commit -m 'has --amend'" should NOT be allowed
if echo "$command" | grep -qE "\bcommit\b[^\"']*--amend"; then
    exit 0
fi

# Get git repository root (more reliable than CLAUDE_PROJECT_DIR for git operations)
GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || {
    echo "Warning: Not in a git repository, skipping commit validation" >&2
    exit 0
}

STATE_FILE="$GIT_ROOT/.claude/.commit-state.json"

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

# State file validated successfully. Don't delete it here - let it expire naturally (5 min).
# This allows retry if git's own pre-commit hook fails, without requiring the workflow
# to be re-run. The file will be cleaned up by the staleness check on the next commit.

# Allow commit to proceed
exit 0
