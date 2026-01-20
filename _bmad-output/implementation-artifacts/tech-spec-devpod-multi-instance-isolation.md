---
title: 'DevPod Multi-Instance Isolation'
slug: 'devpod-multi-instance-isolation'
created: '2026-01-19'
status: 'completed'
stepsCompleted: [1, 2, 3, 4]
tech_stack:
  - DevPod CLI (host-side orchestration)
  - Docker/devcontainer (container spec)
  - Bash scripting (setup scripts)
  - zsh (shell history isolation)
  - JSONL format (Claude history.jsonl)
files_to_modify:
  - .devcontainer/devpod/devcontainer.json (minor updates)
  - image/scripts/setup-instance-isolation.sh (COMPLETE REWRITE)
  - image/scripts/search-history.sh (update for history.jsonl format)
  - image/scripts/post-create.sh (add isolation step)
  - image/Dockerfile (add new scripts, permissions)
code_patterns:
  - Shell scripts use `set -e` for fail-fast
  - Scripts run as `node` user, use `sudo` for privileged ops
  - Post-create has numbered steps [1/8], [2/8], etc.
  - Volume naming: `claude-devcontainer-<purpose>`
  - JSONC comments allowed in devcontainer.json
test_patterns:
  - Unit tests with BATS (Bash Automated Testing System) + temp directory mocking
  - Fixture-based testing for search script with sample JSONL/history files
  - No automated DevPod CLI testing (not feasible in containers)
---

# Tech-Spec: DevPod Multi-Instance Isolation

**Created:** 2026-01-19

## Overview

### Problem Statement

Currently, spinning up multiple independent devcontainer instances requires VS Code-specific template variables (`${localWorkspaceFolderBasename}`). There's no clean way to use DevPod to create multiple isolated instances that share credentials but keep history (zsh, Claude conversations, Gemini) separate per instance.

### Solution

Create a DevPod-compatible devcontainer configuration with a unified `/shared-data` volume structure that:
- Shares credentials and settings across all instances
- Isolates history per-instance using `DEVPOD_WORKSPACE_ID`
- Provides tooling to search across all instance histories
- Integrates with existing Docker image and post-create flow

### Scope

**In Scope:**
- DevPod-specific `devcontainer.json` (no VS Code template variables)
- Unified `/shared-data` volume architecture
- Runtime instance isolation script (`setup-instance-isolation.sh`)
- Cross-instance history search tool (`search-history.sh`)
- Dockerfile updates (add new scripts)
- `post-create.sh` integration
- Basic documentation on credential bootstrap
- Unit tests for isolation scripts (mocked)

**Out of Scope:**
- Feature migration (firewall/hooks to devcontainer features) - separate work
- Backward compatibility with existing VS Code volume structure
- Automated E2E testing of DevPod CLI
- GUI/TUI for instance management (existing `bmad-dashboard` handles this)
- History rotation/cleanup (history.jsonl can grow unbounded - manual cleanup if needed)
- Gemini tmp/ cleanup (shared `~/.gemini/tmp/` will accumulate session data - manual cleanup if needed)
- Volume schema versioning/migration (if layout changes, users recreate volume - acceptable for v1)

## Context for Development

### Codebase Patterns

- Shell scripts in `image/scripts/` follow pattern: shebang, set -e, comments, functions
- devcontainer.json supports JSONC (comments allowed)
- Post-create runs as non-root `node` user, uses `sudo` for privileged operations
- Volume naming convention: `claude-devcontainer-<purpose>`

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `.devcontainer/devcontainer.json` | Current VS Code devcontainer config |
| `image/Dockerfile` | Docker image build (scripts, permissions) |
| `image/scripts/post-create.sh` | Container initialization flow |
| `_bmad-output/planning-artifacts/research/devpod-eval.md` | DevPod evaluation research |
| `_bmad-output/planning-artifacts/research/devpod-in-devcontainer-investigation.md` | DevPod CLI limitations |
| `docs/plans/2026-01-18-devcontainer-feature-migration.md` | Related feature migration design |

### Technical Decisions

- **Unified volume**: Single `/shared-data` volume instead of multiple separate volumes - simplifies management and enables cross-instance tooling
- **Runtime isolation**: Use `DEVPOD_WORKSPACE_ID` environment variable at runtime rather than trying to template volume names
- **No backward compat**: New structure replaces VS Code approach; migration will happen soon

### Critical Discovery: Claude Code File Layout

**Party Mode investigation revealed Claude Code uses TWO separate storage locations:**

| Location | Contains | Sharing Strategy |
|----------|----------|------------------|
| `~/.claude.json` | OAuth tokens, account info (accountUuid, emailAddress, organizationUuid) | **SHARED** - must share or re-auth every instance |
| `~/.claude/` | History, settings, projects, session data | **PER-INSTANCE** - isolate for conversation separation |

**`~/.claude/` internal structure:**
```
~/.claude/
├── history.jsonl          ← ALL conversations (single file, not per-project!)
├── projects/              ← Per-project data (path-encoded dirs)
├── todos/                 ← Todo lists
├── file-history/          ← File change history
├── shell-snapshots/       ← Shell state snapshots
├── session-env/           ← Session environment data
├── settings.json          ← User preferences
├── stats-cache.json       ← Usage statistics
├── statsig/               ← Feature flags (not auth)
├── plugins/               ← Installed plugins
├── cache/                 ← Temporary cache
└── debug/                 ← Debug logs
```

**Key insight:** Previous assumption that `~/.claude/projects/` contained conversations was WRONG. The main conversation log is `history.jsonl` at the root. Symlink strategy must target entire `~/.claude/` directory, not subdirectories.

### Gemini CLI File Layout (Step 2 Investigation)

**Gemini keeps everything in `~/.gemini/` - no separate auth file:**

```
~/.gemini/
├── oauth_creds.json      ← OAuth credentials
├── google_accounts.json  ← Account info
├── installation_id       ← Unique installation ID
├── settings.json         ← User preferences
└── tmp/<hash>/           ← Session/temp data
```

**Key differences from Claude:**
- No separate `~/.gemini.json` file outside the directory
- No obvious persistent conversation history file (unlike Claude's `history.jsonl`)
- Session data in `tmp/` with hash-based subdirectories

**Decision:** Share entire `~/.gemini/` directory. Since there's no persistent conversation history to isolate, sharing simplifies the architecture. Users authenticate once, all instances share credentials.

**Note on `installation_id` sharing:** All instances will share the same `installation_id`, meaning Gemini's telemetry will see them as a single installation. This is acceptable because:
- No indication that Gemini rate-limits by installation ID
- Multiple shell sessions from one machine already share installation ID
- Benefit (simpler architecture) outweighs theoretical risk
- If issues arise, can revisit with per-instance installation_id generation

### Revised Architecture (Final)

```
/shared-data/                              # Single Docker volume
├── auth/
│   └── claude.json                        # Claude OAuth (→ symlink to ~/.claude.json)
│
├── gemini/                                # SHARED - entire ~/.gemini directory
│   ├── oauth_creds.json
│   ├── google_accounts.json
│   ├── installation_id
│   ├── settings.json
│   └── tmp/
│
├── config/
│   └── claude-settings.json               # SHARED Claude preferences
│                                          # (symlinked INTO per-instance claude/settings.json)
│
└── history/                               # PER-INSTANCE isolation
    ├── <instance-id-1>/
    │   ├── claude/                        # → symlink target for ~/.claude
    │   │   ├── history.jsonl              # Per-instance conversations
    │   │   ├── settings.json → /shared-data/config/claude-settings.json  # SHARED
    │   │   └── ...                        # Other per-instance data
    │   └── zsh_history                    # Shell history
    ├── <instance-id-2>/
    │   └── ...
    └── <instance-id-N>/
        └── ...
```

**Runtime symlink setup:**
```bash
# Claude Auth - shared (separate file)
ln -sf /shared-data/auth/claude.json ~/.claude.json

# Claude History - isolated per instance (entire directory)
ln -sf /shared-data/history/$INSTANCE_ID/claude ~/.claude

# Claude Settings - shared (symlink INSIDE the per-instance claude dir)
ln -sf /shared-data/config/claude-settings.json ~/.claude/settings.json

# Gemini - shared entirely (no isolation needed)
ln -sf /shared-data/gemini ~/.gemini

# ZSH History - isolated per instance
export HISTFILE="/shared-data/history/$INSTANCE_ID/zsh_history"
```

**Summary of isolation strategy:**

| Tool | Auth | History/Data | Strategy |
|------|------|--------------|----------|
| Claude | `~/.claude.json` → shared | `~/.claude/` → per-instance | Split auth from history |
| Gemini | In `~/.gemini/` | In `~/.gemini/` | Share entire directory |
| ZSH | N/A | `$HISTFILE` → per-instance | Isolate history file |

## Implementation Plan

### Tasks

#### Task 1: Rewrite `setup-instance-isolation.sh` [COMPLETE]
- **File:** `image/scripts/setup-instance-isolation.sh`
- **Action:** Complete rewrite implementing the revised architecture
- **Details:**
  ```
  0. Early checks:
     - Verify /shared-data is writable: `touch /shared-data/.write-test && rm /shared-data/.write-test`
     - If read-only → exit 1 with: "ERROR: /shared-data is read-only. Check volume mount."
     - Timeout: wrap writability check in `timeout ${SHARED_DATA_TIMEOUT:-5}s`
     - SHARED_DATA_TIMEOUT env var allows override for slow network mounts (default: 5 seconds)

  1. Validate DEVPOD_WORKSPACE_ID:
     - Exit 1 if unset or empty (NO fallbacks)
     - Validate format: alphanumeric, hyphens, underscores only (no slashes, spaces, special chars)
     - Sanitize: INSTANCE_ID="${DEVPOD_WORKSPACE_ID//[^a-zA-Z0-9_-]/}"
     - Exit 1 if sanitized != original (reject invalid IDs)

  2. Create directory structure with verification:
     - /shared-data/auth/ (mode 755, owner node:node)
     - /shared-data/gemini/ (mode 755, owner node:node)
     - /shared-data/config/ (mode 755, owner node:node)
     - /shared-data/history/$INSTANCE_ID/claude/ (mode 755, owner node:node)
     - Write test file to each dir (with 5s timeout), verify, remove - confirms writability

  3. Handle existing symlinks/directories (BEFORE creating new ones):
     - If ~/.claude.json exists and is NOT a symlink:
       → If ~/.claude.json.bak exists → use timestamped: ~/.claude.json.bak.$(date +%s)
       → backup to ~/.claude.json.bak (or timestamped)
     - If ~/.claude exists and is NOT a symlink:
       → If ~/.claude.bak exists → use timestamped: ~/.claude.bak.$(date +%s)
       → backup to ~/.claude.bak (or timestamped)
     - If ~/.gemini exists and is NOT a symlink:
       → If ~/.gemini.bak exists → use timestamped: ~/.gemini.bak.$(date +%s)
       → backup to ~/.gemini.bak (or timestamped)
     - If target IS already a symlink → remove it (will be recreated)

  4. Handle Claude auth bootstrap:
     - If /shared-data/auth/claude.json exists → symlink ~/.claude.json
     - If not → print message: "INFO: Run 'setup-claude-auth-sharing' after first Claude auth"

  5. Symlink ~/.claude → /shared-data/history/$INSTANCE_ID/claude
     - VERIFY: `[ -L ~/.claude ] && [ -d ~/.claude ]` or exit 1

  6. Bootstrap and symlink Claude settings (SHARED):
     - If /shared-data/config/claude-settings.json does NOT exist:
       → Create empty JSON: `echo '{}' > /shared-data/config/claude-settings.json`
     - If file EXISTS, validate it's valid JSON:
       → `jq empty /shared-data/config/claude-settings.json 2>/dev/null || echo '{}' > /shared-data/config/claude-settings.json`
       → This auto-repairs corrupted settings files
     - Symlink: ln -sf /shared-data/config/claude-settings.json ~/.claude/settings.json
     - VERIFY: `[ -L ~/.claude/settings.json ]` or exit 1

  7. Symlink ~/.gemini → /shared-data/gemini
     - VERIFY: `[ -L ~/.gemini ]` or exit 1

  8. Configure ZSH HISTFILE:
     - First, comment out ANY existing HISTFILE exports in ~/.zshrc:
       `sed -i 's/^export HISTFILE=/#DISABLED_BY_ISOLATION# export HISTFILE=/' ~/.zshrc`
     - Use a single-line marker+value format that's self-contained:
       `# [setup-instance-isolation] export HISTFILE="/shared-data/history/$INSTANCE_ID/zsh_history"`
     - Use grep to check if our marker line exists
     - If exists → use sed to replace the entire line (marker + export together)
     - If missing → append the marker line to ~/.zshrc
     - Also export to current shell for immediate effect: `export HISTFILE=...`
     - This approach: (1) disables conflicting HISTFILE, (2) keeps marker+value atomic

  9. Verify all symlinks point to writable locations (final health check)
     - Test write to each symlink target
     - If any fails → trigger rollback

  10. Export CLAUDE_INSTANCE=$INSTANCE_ID (append to ~/.zshrc with marker)
  ```
- **Rollback behavior:** If script fails after partial execution:
  - Use `set -e` only AFTER trap is configured to avoid trap-before-set race
  - Use `trap cleanup EXIT` where cleanup() handles both success and failure
  - Track state in file, not array: `echo "$symlink" >> /tmp/isolation-$$.created`
  - Check exit code in trap: `if [ $? -ne 0 ]; then rollback; fi`
  - On rollback: remove symlinks listed in /tmp/isolation-$$.created
  - Restore .bak files: find most recent backup (highest timestamp suffix, or plain .bak if no timestamp)
  - Print clear error message with manual recovery steps
  - Cleanup temp file on exit (both success and failure)
- **Idempotency:** Script must be safe to run multiple times - check state before each operation
- **Symlink verification:** After EVERY `ln -sf`, verify with `[ -L $path ]` - some filesystems silently fail
- **Error messages (standardized):**
  ```
  E001: "ERROR: /shared-data is read-only. Check volume mount configuration."
  E002: "ERROR: /shared-data write test timed out. Network volume may be unresponsive."
  E003: "ERROR: DEVPOD_WORKSPACE_ID is not set. Cannot proceed with isolation."
  E004: "ERROR: DEVPOD_WORKSPACE_ID contains invalid characters: '$DEVPOD_WORKSPACE_ID'"
  E005: "ERROR: Failed to create directory: $DIR"
  E006: "ERROR: Failed to create symlink: $SOURCE → $TARGET"
  E007: "ERROR: Symlink verification failed for: $PATH"
  E008: "ERROR: Final health check failed. Rolling back..."
  I001: "INFO: Run 'setup-claude-auth-sharing' after first Claude auth"
  I002: "INFO: Instance isolation complete for: $INSTANCE_ID"
  ```

#### Task 2: Create `setup-claude-auth-sharing.sh` helper [COMPLETE]
- **File:** `image/scripts/setup-claude-auth-sharing.sh`
- **Action:** Create new script for post-auth credential sharing
- **Details:**
  ```
  1. Verify ~/.claude.json exists and is a regular file (not symlink)
     - If symlink already → print "Auth already shared" and exit 0
     - If missing → print "No auth found. Run 'claude' first to authenticate." and exit 1
  2. Verify /shared-data/auth/ exists (create if missing)
  3. Acquire lock to prevent concurrent execution:
     - LOCKFILE="/shared-data/auth/.claude-auth-sharing.lock"
     - Use flock: exec 200>"$LOCKFILE" && flock -n 200 || exit with "Another instance is sharing auth"
  4. Check if /shared-data/auth/claude.json already exists (another instance beat us):
     - If exists → print "Auth already shared by another instance" and exit 0
  5. Copy ~/.claude.json → /shared-data/auth/claude.json (atomic: write to .tmp, then mv)
  6. Remove ~/.claude.json
  7. Create symlink ~/.claude.json → /shared-data/auth/claude.json
  8. Verify symlink works (test read)
  9. Release lock (automatic on script exit)
  10. Print success: "Claude auth shared! New instances will skip authentication."
  ```
- **Trigger mechanism:** MANUAL ONLY
  - User must explicitly run `setup-claude-auth-sharing` after first authentication
  - `setup-instance-isolation.sh` prints reminder if shared auth not found
  - No automatic detection - keeps behavior predictable and auditable
- **Why manual:** Automatic copying of auth tokens is a security-sensitive operation. Explicit user action ensures informed consent and prevents accidental credential sharing.
- **Concurrency handling:** Uses `flock` to prevent race conditions when multiple users run simultaneously
- **Lock scope note:** The lock protects against concurrent `setup-claude-auth-sharing` executions. There's a theoretical race with `setup-instance-isolation.sh` checking for auth before this script creates it, but this is acceptable because:
  - User must MANUALLY run auth sharing AFTER authenticating
  - The isolation script only creates a symlink IF the shared auth already exists
  - If race occurs, user simply re-runs isolation script or restarts container
  - Adding cross-script locking would over-complicate for a rare manual operation

#### Task 3: Update `search-history.sh` for JSONL format [COMPLETE]
- **File:** `image/scripts/search-history.sh`
- **Action:** Fix Claude history search to use `history.jsonl`
- **Details:**
  ```
  1. Change search_claude() to grep history.jsonl files (not *.json)
  2. Update list_instances() to count lines in history.jsonl
  3. Parse JSONL format (one JSON object per line)
  4. Extract and display relevant fields (timestamp, display, project)
  5. Preserve existing --recent flag functionality:
     - For zsh: tail -n $count on zsh_history files
     - For claude: tail -n $count on history.jsonl, parse and display
  ```
- **Error handling for JSONL parsing:**
  ```
  - Use `jq -c` with error suppression: `jq -c '...' 2>/dev/null || echo "[parse error]"`
  - Malformed lines: skip with warning to stderr, continue processing
  - Empty files: handle gracefully (0 entries)
  - Partial/truncated JSON (last line): jq will fail, skip that line
  - Print count of skipped lines at end if any: "Warning: N lines skipped (parse errors)"
  ```
- **Zero instances behavior:**
  ```
  - --list with no instances: print "No instances found in /shared-data/history/" and exit 0
  - --claude/--zsh/--gemini with no instances: print "No instances found" and exit 0
  - Pattern search with no instances: print "No instances to search" and exit 0
  - All cases: exit code 0 (not an error, just empty result)
  ```
- **Orphaned instance detection (--list flag):**
  ```
  - When listing instances, check if history.jsonl was modified in last 30 days
  - If older than 30 days: append "(stale?)" to instance name
  - Example output: "agent-1  zsh: 50  claude: 10  (stale?)"
  - This hints that DevPod workspace may have been deleted
  - No auto-cleanup - just informational warning
  ```
- **--recent cross-instance ordering:**
  ```
  - For zsh: entries have no timestamp, show last N lines per instance, prefix with [instance]
  - For claude: history.jsonl entries have "timestamp" field (Unix epoch in ms)
    → Extract: jq -r '.timestamp'
    → Sort all entries by timestamp descending
    → Take first N entries
    → Display with [instance] prefix
  - Combined --recent (all types): show zsh entries first (no timestamp), then claude (sorted by timestamp)
  - Note: zsh and claude timestamps are NOT merged/interleaved - they're shown in separate sections
  ```
- **Claude JSONL format assumption:**
  ```
  Expected format per line: {"timestamp": 1234567890123, "type": "...", "message": {...}}
  - timestamp: Unix epoch in milliseconds
  - jq filter: '.timestamp, .type, .message.content' (adjust based on actual format)
  - Fixtures must include REAL sample from ~/.claude/history.jsonl to validate filter
  ```

#### Task 4: Update `post-create.sh` with isolation step [COMPLETE]
- **File:** `image/scripts/post-create.sh`
- **Action:** Add instance isolation as early step
- **Details:**
  ```
  1. Add new step after [1/8] (becomes [2/9], renumber others)
  2. DevPod mode detection (ALL conditions must be true):
     a. SHARED_DATA_DIR environment variable is set AND non-empty
     b. DEVPOD_WORKSPACE_ID environment variable is set AND non-empty
     c. Directory $SHARED_DATA_DIR exists and is writable
  3. If ALL conditions met: run /usr/local/bin/setup-instance-isolation.sh
  4. If ANY condition fails: skip isolation (VS Code mode or misconfigured DevPod)
     - Print which condition failed for debugging
  ```
- **Detection logic rationale:**
  - `SHARED_DATA_DIR` alone is insufficient - VS Code could theoretically set it
  - `DEVPOD_WORKSPACE_ID` is DevPod-specific and confirms DevPod context
  - Directory check prevents runtime failures if volume mount is missing

#### Task 5: Update `devcontainer.json` for DevPod [COMPLETE]
- **File:** `.devcontainer/devpod/devcontainer.json`
- **Action:** Minor updates to align with final architecture
- **Details:**
  ```
  1. Update comments to reflect final architecture
  2. Ensure SHARED_DATA_DIR=/shared-data in containerEnv
  3. Keep single shared-data volume mount
  ```

#### Task 6: Update Dockerfile with new scripts [COMPLETE]
- **File:** `image/Dockerfile`
- **Action:** Add new scripts and permissions
- **Details:**
  ```
  1. Verify jq is installed (required for search-history.sh JSONL parsing):
     - Check if already in base image: `which jq`
     - If not present: add `RUN apt-get update && apt-get install -y jq && rm -rf /var/lib/apt/lists/*`
  2. COPY image/scripts/setup-instance-isolation.sh /usr/local/bin/
  3. COPY image/scripts/setup-claude-auth-sharing.sh /usr/local/bin/
  4. COPY image/scripts/search-history.sh /usr/local/bin/
  5. chmod 755 for all three scripts
  6. NO sudoers entry needed - scripts run as 'node' user which owns home directory
  ```
- **Dependencies:**
  - `jq` - required for JSONL parsing in search-history.sh
  - `timeout` (from coreutils) - required for writability checks
  - `flock` (from util-linux) - required for auth sharing concurrency control
  - All three are standard in Debian/Ubuntu base images, verify presence
- **sudo resolution:** NOT REQUIRED for normal operation
  - `/shared-data` volume is mounted with default permissions
  - Docker volumes created by non-root container user are owned by that user
  - All operations (`mkdir`, `ln -sf`, `cp`) work without elevated privileges
- **Edge case - volume ownership wrong:**
  - If volume was created by root or different user, scripts will fail with permission errors
  - Fix from HOST machine: `docker run --rm -v claude-devcontainer-shared-data:/data alpine chown -R 1000:1000 /data`
  - This runs a temporary container to fix permissions (no sudo needed inside devcontainer)
  - Document this in troubleshooting section if users report permission errors

#### Task 7: Create unit tests for isolation script [COMPLETE]
- **File:** `image/scripts/__tests__/setup-instance-isolation.bats`
- **Action:** Create test suite with mocked filesystem using BATS
- **Testing framework:** BATS (Bash Automated Testing System)
  - Install: `npm install -g bats` or use Docker image `bats/bats`
  - Why BATS: simpler than shellspec, widely adopted, good CI integration
- **Mocking strategy:**
  ```
  - Create temp directory per test: TEMP_ROOT=$(mktemp -d)
  - Override paths: SHARED_DATA_DIR="$TEMP_ROOT/shared-data", HOME="$TEMP_ROOT/home"
  - Source script with overridden paths (script must support path injection)
  - Cleanup in teardown: rm -rf "$TEMP_ROOT"
  ```
- **Test cases:**
  ```
  1. Test: Fails if DEVPOD_WORKSPACE_ID unset (exit code 1, message E003)
  2. Test: Fails if DEVPOD_WORKSPACE_ID contains invalid chars (exit code 1, message E004)
  3. Test: Fails if /shared-data is read-only (exit code 1, message E001)
  4. Test: Creates correct directory structure with correct permissions
  5. Test: Symlinks Claude auth when shared auth exists
  6. Test: Prints reminder when no shared auth (message I001, does NOT fail)
  7. Test: Creates Gemini symlink to shared directory
  8. Test: Sets HISTFILE correctly in .zshrc with marker comment
  9. Test: Backs up existing non-symlink ~/.claude.json
  10. Test: Uses timestamped backup when .bak already exists
  11. Test: Rollback restores state on mid-script failure (see below)
  12. Test: Idempotent - safe to run twice
  13. Test: Bootstraps empty claude-settings.json if not exists
  ```
- **Rollback testing approach (Test 11):**
  ```
  - Script must support FAIL_AT_STEP environment variable for testing
  - FAIL_AT_STEP=5 causes script to exit 1 after step 5 completes
  - Test procedure:
    1. Set FAIL_AT_STEP=5 (after symlink creation, before settings)
    2. Run script, verify exit code 1
    3. Verify symlinks created in steps 1-5 were removed
    4. Verify .bak files were restored to originals
  - This is NOT production code - only activated when FAIL_AT_STEP is set
  ```

#### Task 8: Create fixture tests for search script [COMPLETE]
- **File:** `image/scripts/__tests__/search-history.bats`
- **Action:** Create test suite with fixture data using BATS
- **Fixtures:** `image/scripts/__tests__/fixtures/`
  ```
  fixtures/
  ├── instance-1/
  │   ├── claude/history.jsonl    # 5 sample conversation entries
  │   └── zsh_history             # 10 sample commands
  ├── instance-2/
  │   ├── claude/history.jsonl    # 3 entries, one with "fix the bug"
  │   └── zsh_history             # 5 commands, one with "npm install"
  └── malformed/
      └── claude/history.jsonl    # Contains 1 valid + 1 malformed line
  ```
- **Test cases:**
  ```
  1. Test: --list shows correct instance counts (instance-1: 5 convos, instance-2: 3)
  2. Test: --zsh finds commands in history ("npm install" → instance-2)
  3. Test: --claude finds entries in history.jsonl ("fix the bug" → instance-2)
  4. Test: --recent shows latest N entries across instances
  5. Test: --instance filters to single instance
  6. Test: Malformed JSONL lines are skipped with warning (not crash)
  7. Test: Empty pattern shows usage (exit 1)
  8. Test: --list with zero instances shows "No instances found" (exit 0)
  9. Test: Pattern search with zero instances shows "No instances to search" (exit 0)
  ```

### Acceptance Criteria

#### AC 1: Instance Isolation Works
- [ ] **Given** DevPod spins up two instances (agent-1, agent-2) from the same repo
- [ ] **When** user runs `claude` in agent-1 and has a conversation
- [ ] **Then** agent-2's `~/.claude/history.jsonl` does NOT contain agent-1's conversation

#### AC 2: Auth Sharing Works
- [ ] **Given** user authenticates Claude in agent-1 (first instance on fresh volume)
- [ ] **When** user runs `setup-claude-auth-sharing` and then spins up agent-2
- [ ] **Then** agent-2 does NOT prompt for Claude authentication

#### AC 2b: Auth Sharing Reminder (Failure Path)
- [ ] **Given** user authenticates Claude in agent-1 but does NOT run `setup-claude-auth-sharing`
- [ ] **When** user spins up agent-2
- [ ] **Then** `setup-instance-isolation.sh` on agent-2 printed message I001 (reminder to share auth)
- [ ] **And** `~/.claude.json` on agent-2 is NOT a symlink (no shared auth exists)
- [ ] **And** running `claude` on agent-2 will prompt for authentication (manual verification)
- [ ] **Testability (unit test):**
  - Test isolation script with no `/shared-data/auth/claude.json` present
  - Assert stdout contains "setup-claude-auth-sharing"
  - Assert `~/.claude.json` was NOT created as symlink
- [ ] **Testability (E2E):** Manual verification that `claude` prompts for auth (cannot automate OAuth flow)

#### AC 3: Gemini Sharing Works
- [ ] **Given** user authenticates Gemini in agent-1
- [ ] **When** user spins up agent-2
- [ ] **Then** agent-2 does NOT prompt for Gemini authentication (shared ~/.gemini)

#### AC 4: ZSH History Isolation
- [ ] **Given** two instances agent-1 and agent-2 are running
- [ ] **When** user runs `echo "secret-command-123"` in agent-1
- [ ] **Then** `history` in agent-2 does NOT show "secret-command-123"

#### AC 5: Cross-Instance Search Works
- [ ] **Given** agent-1 has Claude conversation containing "fix the bug"
- [ ] **When** user runs `search-history --claude "fix the bug"` from agent-2
- [ ] **Then** output shows the match with `[agent-1]` prefix

#### AC 6: Missing Instance ID Fails Hard
- [ ] **Given** container starts without DEVPOD_WORKSPACE_ID set
- [ ] **When** setup-instance-isolation.sh runs
- [ ] **Then** script exits with error code 1 and clear error message

#### AC 7: Fresh Volume Bootstrap
- [ ] **Given** fresh /shared-data volume with no existing data
- [ ] **When** first instance starts
- [ ] **Then** all required directories are created with correct permissions

#### AC 8: VS Code Mode Unaffected
- [ ] **Given** user opens project in VS Code (not DevPod)
- [ ] **When** container starts without SHARED_DATA_DIR
- [ ] **Then** isolation setup is skipped, existing behavior unchanged

## Additional Context

### Dependencies

- DevPod CLI installed on host machine
- Docker provider configured for DevPod
- Existing `ghcr.io/zookanalytics/claude-devcontainer:latest` image

### Testing Strategy

- Unit test `setup-instance-isolation.sh` with mocked filesystem
- Unit test `search-history.sh` with fixture data
- Manual E2E: spin up multiple DevPod instances, verify isolation (see checklist below)
- No automated DevPod CLI testing (not feasible inside containers)

### Manual E2E Test Checklist

**Prerequisites:**
- DevPod CLI installed on host
- Docker provider configured
- Fresh volume (delete `claude-devcontainer-shared-data` if exists)

**Test Procedure:**

```
□ 1. FRESH VOLUME BOOTSTRAP
  $ docker volume rm claude-devcontainer-shared-data 2>/dev/null || true
  $ devpod up <repo> --ide none --id agent-1
  □ Verify: No errors during setup
  □ Verify: Message I001 printed (no shared auth yet)
  □ Verify: /shared-data/history/agent-1/claude/ exists

□ 2. CLAUDE AUTH IN FIRST INSTANCE
  $ devpod ssh agent-1
  $ claude  # Complete authentication
  $ cat ~/.claude.json  # Should exist as regular file
  $ setup-claude-auth-sharing
  □ Verify: "Claude auth shared!" message
  □ Verify: ~/.claude.json is now a symlink
  □ Verify: /shared-data/auth/claude.json exists

□ 3. SECOND INSTANCE - AUTH SHARING
  $ devpod up <repo> --ide none --id agent-2
  $ devpod ssh agent-2
  $ claude --version  # Should NOT prompt for auth
  □ Verify: No authentication prompt
  □ Verify: ~/.claude.json is symlink to /shared-data/auth/claude.json

□ 4. HISTORY ISOLATION
  $ devpod ssh agent-1
  $ claude  # Have a conversation mentioning "agent-1-secret-phrase"
  $ exit
  $ devpod ssh agent-2
  $ cat ~/.claude/history.jsonl | grep "agent-1-secret-phrase"
  □ Verify: No match (histories are isolated)

□ 5. ZSH HISTORY ISOLATION
  $ devpod ssh agent-1
  $ echo "zsh-secret-from-agent-1"
  $ exit
  $ devpod ssh agent-2
  $ history | grep "zsh-secret-from-agent-1"
  □ Verify: No match

□ 6. CROSS-INSTANCE SEARCH
  $ devpod ssh agent-2
  $ search-history --claude "agent-1-secret-phrase"
  □ Verify: Shows match with [agent-1] prefix
  $ search-history --list
  □ Verify: Shows both agent-1 and agent-2

□ 7. GEMINI SHARING (if Gemini installed)
  $ devpod ssh agent-1
  $ gemini  # Complete authentication
  $ exit
  $ devpod ssh agent-2
  $ gemini --version  # Should NOT prompt for auth
  □ Verify: No authentication prompt

□ 8. VS CODE MODE (regression test)
  Open same repo in VS Code with standard devcontainer
  □ Verify: No isolation errors (SHARED_DATA_DIR not set)
  □ Verify: Normal VS Code devcontainer behavior

□ 9. CLEANUP
  $ devpod delete agent-1
  $ devpod delete agent-2
```

**Expected Results:** All checkboxes should pass. Document any failures with exact error messages.

### Risk Mitigation (Pre-mortem Analysis)

**Failure scenarios identified and prevention measures:**

| Risk | Failure Mode | Prevention | Priority |
|------|--------------|------------|----------|
| **Missing directories** | Symlink created but target dir doesn't exist → silent data loss | `mkdir -p` + verify writable before symlink creation | **HIGH** |
| **Auth race condition** | Symlink created AFTER Claude checks for auth → re-auth required | Bootstrap sequence: check shared auth first, copy after initial auth | **HIGH** |
| **Empty instance ID** | `DEVPOD_WORKSPACE_ID` unset → multiple instances share "default" | FAIL HARD if env var missing, no silent fallbacks | **HIGH** |
| **Concurrent startup** | Two instances start simultaneously on fresh volume, both create dirs | Acceptable: `mkdir -p` is idempotent, symlinks are atomic | **MEDIUM** |
| **Search script wrong format** | Script searches for `*.json` but history is in `history.jsonl` | Rewrite to grep JSONL format | **MEDIUM** |
| **Settings ambiguity** | Users expect shared settings but they're per-instance | Settings.json symlinked to shared config (resolved in Task 1) | **MEDIUM** |
| **Volume permissions** | `/shared-data` owned by root, container runs as `node` | Ownership check + `chown` in setup script | **MEDIUM** |
| **Disk space exhaustion** | history.jsonl grows unbounded | OUT OF SCOPE - document as known limitation | **LOW** |

**Concurrent startup analysis:** When two instances start simultaneously:
- `mkdir -p` is safe - creates directory if not exists, no error if exists
- `ln -sf` is atomic - overwrites existing symlink atomically
- Auth file copy uses atomic write (`.tmp` + `mv`)
- No file locking needed - operations are inherently safe
- Worst case: both instances create same directory (harmless)

**Implementation requirements from pre-mortem:**

1. **Directory creation**: Always `mkdir -p` + write test file + verify before creating symlinks
2. **Auth bootstrap flow**:
   - Check if `/shared-data/auth/claude.json` exists
   - If YES: symlink `~/.claude.json` → shared auth
   - If NO: let Claude auth normally, then copy `~/.claude.json` → `/shared-data/auth/claude.json`
3. **Instance ID validation**: Script must exit with error if `DEVPOD_WORKSPACE_ID` is empty/unset
4. **Startup health check**: Verify symlinks point to valid, writable locations before completing setup
5. **Settings decision**: `settings.json` will be **SHARED** (symlinked from `/shared-data/config/claude-settings.json`) to avoid user confusion

### Notes

- **Auth bootstrap**: First instance on a fresh volume requires Claude/Gemini authentication. After auth, `~/.claude.json` is copied to `/shared-data/auth/claude.json` and shared with all future instances.
- **Draft files exist but need revision**: Earlier conversation created draft files (`.devcontainer/devpod/devcontainer.json`, `setup-instance-isolation.sh`, `search-history.sh`) based on incorrect assumptions about Claude's file structure. These must be rewritten per the revised architecture.
- **Gemini investigation COMPLETE**: Gemini stores everything in `~/.gemini/` with no separate auth file. Decision: share entire directory (no conversation history to isolate).
- **VS Code devcontainer unchanged**: The existing `.devcontainer/devcontainer.json` for VS Code use remains unchanged; DevPod config is additive.

## Review Notes

- Adversarial review completed: 2026-01-19
- Findings: 13 total, 5 fixed, 7 dismissed (noise/not applicable), 1 verified not an issue
- Resolution approach: Auto-fix

### Fixes Applied
- F3: Fixed `$?` race condition in `search-history.sh` - explicitly capture jq exit status
- F6: Changed grep to use `-F` flag for literal string matching (security improvement)
- F8: Improved test assertion for malformed JSONL handling
- F9: Fixed misleading comment about HISTFILE export scope
- F12: Added directory tracking and cleanup to rollback function

### Verified Not An Issue
- F4: DevPod automatically injects `DEVPOD_WORKSPACE_ID` into containers - no manual configuration needed
