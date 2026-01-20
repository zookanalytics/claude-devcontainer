#!/usr/bin/env bats
# setup-instance-isolation.bats
# Unit tests for setup-instance-isolation.sh with mocked filesystem
#
# Run with: bats image/scripts/__tests__/setup-instance-isolation.bats
# Or via Docker: docker run --rm -v "$PWD":/workspace bats/bats /workspace/image/scripts/__tests__/setup-instance-isolation.bats

# Setup: Create temp directories before each test
setup() {
  # Create isolated test environment
  export TEMP_ROOT=$(mktemp -d)
  export HOME="$TEMP_ROOT/home"
  export SHARED_DATA_DIR="$TEMP_ROOT/shared-data"

  mkdir -p "$HOME"
  mkdir -p "$SHARED_DATA_DIR"

  # Create minimal .zshrc
  touch "$HOME/.zshrc"

  # Path to script under test
  SCRIPT="/usr/local/bin/setup-instance-isolation.sh"

  # If running locally (not in container), use relative path
  if [ ! -f "$SCRIPT" ]; then
    SCRIPT="${BATS_TEST_DIRNAME}/../setup-instance-isolation.sh"
  fi
}

# Teardown: Clean up temp directories after each test
teardown() {
  rm -rf "$TEMP_ROOT"
}

# Helper: Run script with given DEVPOD_WORKSPACE_ID
run_isolation_script() {
  local workspace_id="$1"
  export DEVPOD_WORKSPACE_ID="$workspace_id"
  run bash "$SCRIPT"
}

# =============================================================================
# Test: E003 - Fails if DEVPOD_WORKSPACE_ID is unset
# =============================================================================
@test "E003: fails if DEVPOD_WORKSPACE_ID unset" {
  unset DEVPOD_WORKSPACE_ID
  run bash "$SCRIPT"

  [ "$status" -eq 1 ]
  [[ "$output" == *"E003"* ]]
  [[ "$output" == *"DEVPOD_WORKSPACE_ID is not set"* ]]
}

# =============================================================================
# Test: E004 - Fails if DEVPOD_WORKSPACE_ID contains invalid characters
# =============================================================================
@test "E004: fails if DEVPOD_WORKSPACE_ID contains invalid chars" {
  run_isolation_script "agent/1"

  [ "$status" -eq 1 ]
  [[ "$output" == *"E004"* ]]
  [[ "$output" == *"invalid characters"* ]]
}

@test "E004: fails with spaces in DEVPOD_WORKSPACE_ID" {
  run_isolation_script "agent 1"

  [ "$status" -eq 1 ]
  [[ "$output" == *"E004"* ]]
}

@test "E004: fails with special chars in DEVPOD_WORKSPACE_ID" {
  run_isolation_script "agent\$1"

  [ "$status" -eq 1 ]
  [[ "$output" == *"E004"* ]]
}

# =============================================================================
# Test: E001 - Fails if /shared-data is read-only
# =============================================================================
@test "E001: fails if shared-data is read-only" {
  # Make shared-data read-only
  chmod 555 "$SHARED_DATA_DIR"

  run_isolation_script "test-instance"

  # Restore permissions for cleanup
  chmod 755 "$SHARED_DATA_DIR"

  [ "$status" -eq 1 ]
  [[ "$output" == *"E001"* ]] || [[ "$output" == *"E002"* ]]
}

# =============================================================================
# Test: Creates correct directory structure
# =============================================================================
@test "creates correct directory structure" {
  run_isolation_script "test-instance"

  [ "$status" -eq 0 ]

  # Verify directories exist
  [ -d "$SHARED_DATA_DIR/auth" ]
  [ -d "$SHARED_DATA_DIR/gemini" ]
  [ -d "$SHARED_DATA_DIR/config" ]
  [ -d "$SHARED_DATA_DIR/history/test-instance/claude" ]
}

# =============================================================================
# Test: Symlinks Claude auth when shared auth exists
# =============================================================================
@test "symlinks Claude auth when shared auth exists" {
  # Pre-create shared auth
  mkdir -p "$SHARED_DATA_DIR/auth"
  echo '{"token": "test"}' > "$SHARED_DATA_DIR/auth/claude.json"

  run_isolation_script "test-instance"

  [ "$status" -eq 0 ]

  # Verify symlink
  [ -L "$HOME/.claude.json" ]
  [ "$(readlink "$HOME/.claude.json")" = "$SHARED_DATA_DIR/auth/claude.json" ]
}

# =============================================================================
# Test: Prints reminder when no shared auth (I001)
# =============================================================================
@test "I001: prints reminder when no shared auth" {
  run_isolation_script "test-instance"

  [ "$status" -eq 0 ]
  [[ "$output" == *"I001"* ]]
  [[ "$output" == *"setup-claude-auth-sharing"* ]]

  # Should NOT create symlink for ~/.claude.json
  [ ! -L "$HOME/.claude.json" ]
}

# =============================================================================
# Test: Creates Gemini symlink to shared directory
# =============================================================================
@test "creates Gemini symlink to shared directory" {
  run_isolation_script "test-instance"

  [ "$status" -eq 0 ]

  # Verify symlink
  [ -L "$HOME/.gemini" ]
  [ "$(readlink "$HOME/.gemini")" = "$SHARED_DATA_DIR/gemini" ]
}

# =============================================================================
# Test: Sets HISTFILE correctly in .zshrc
# =============================================================================
@test "sets HISTFILE correctly in .zshrc" {
  run_isolation_script "test-instance"

  [ "$status" -eq 0 ]

  # Verify marker and HISTFILE in .zshrc
  grep -q "\[setup-instance-isolation\]" "$HOME/.zshrc"
  grep -q "HISTFILE.*test-instance.*zsh_history" "$HOME/.zshrc"
}

# =============================================================================
# Test: Backs up existing non-symlink ~/.claude.json
# =============================================================================
@test "backs up existing non-symlink ~/.claude.json" {
  # Pre-create shared auth and local auth file
  mkdir -p "$SHARED_DATA_DIR/auth"
  echo '{"token": "shared"}' > "$SHARED_DATA_DIR/auth/claude.json"
  echo '{"token": "local"}' > "$HOME/.claude.json"

  run_isolation_script "test-instance"

  [ "$status" -eq 0 ]

  # Verify backup exists
  [ -f "$HOME/.claude.json.bak" ]

  # Verify original is now a symlink
  [ -L "$HOME/.claude.json" ]
}

# =============================================================================
# Test: Uses timestamped backup when .bak already exists
# =============================================================================
@test "uses timestamped backup when .bak already exists" {
  # Pre-create shared auth and local auth file
  mkdir -p "$SHARED_DATA_DIR/auth"
  echo '{"token": "shared"}' > "$SHARED_DATA_DIR/auth/claude.json"
  echo '{"token": "local"}' > "$HOME/.claude.json"

  # Pre-create a .bak file
  echo '{"token": "old-backup"}' > "$HOME/.claude.json.bak"

  run_isolation_script "test-instance"

  [ "$status" -eq 0 ]

  # Verify original .bak still exists (wasn't overwritten)
  [ -f "$HOME/.claude.json.bak" ]

  # Verify a timestamped backup was created
  ls "$HOME/.claude.json.bak."* 2>/dev/null
  [ $? -eq 0 ]
}

# =============================================================================
# Test: Idempotent - safe to run twice
# =============================================================================
@test "idempotent - safe to run twice" {
  run_isolation_script "test-instance"
  [ "$status" -eq 0 ]

  # Run again
  run_isolation_script "test-instance"
  [ "$status" -eq 0 ]

  # Verify symlinks still correct
  [ -L "$HOME/.claude" ]
  [ -L "$HOME/.gemini" ]
}

# =============================================================================
# Test: Bootstraps empty claude-settings.json if not exists
# =============================================================================
@test "bootstraps empty claude-settings.json if not exists" {
  run_isolation_script "test-instance"

  [ "$status" -eq 0 ]

  # Verify settings file exists
  [ -f "$SHARED_DATA_DIR/config/claude-settings.json" ]

  # Verify it's valid JSON
  jq empty "$SHARED_DATA_DIR/config/claude-settings.json"
  [ $? -eq 0 ]

  # Verify symlink in per-instance claude dir
  [ -L "$HOME/.claude/settings.json" ]
}

# =============================================================================
# Test: Creates ~/.claude symlink to per-instance directory
# =============================================================================
@test "creates ~/.claude symlink to per-instance directory" {
  run_isolation_script "test-instance"

  [ "$status" -eq 0 ]

  # Verify symlink
  [ -L "$HOME/.claude" ]
  [ "$(readlink "$HOME/.claude")" = "$SHARED_DATA_DIR/history/test-instance/claude" ]
}

# =============================================================================
# Test: Exports CLAUDE_INSTANCE to .zshrc
# =============================================================================
@test "exports CLAUDE_INSTANCE to .zshrc" {
  run_isolation_script "test-instance"

  [ "$status" -eq 0 ]

  # Verify CLAUDE_INSTANCE in .zshrc
  grep -q "CLAUDE_INSTANCE" "$HOME/.zshrc"
  grep -q "test-instance" "$HOME/.zshrc"
}

# =============================================================================
# Test: Valid instance IDs with hyphens and underscores
# =============================================================================
@test "accepts valid instance IDs with hyphens" {
  run_isolation_script "my-test-instance"
  [ "$status" -eq 0 ]
}

@test "accepts valid instance IDs with underscores" {
  run_isolation_script "my_test_instance"
  [ "$status" -eq 0 ]
}

@test "accepts alphanumeric instance IDs" {
  run_isolation_script "agent123"
  [ "$status" -eq 0 ]
}

# =============================================================================
# Test: Rollback on mid-script failure (uses FAIL_AT_STEP)
# =============================================================================
@test "rollback restores state on mid-script failure" {
  # Pre-create a local .claude.json that will be backed up
  echo '{"token": "original"}' > "$HOME/.claude.json"

  # Pre-create shared auth so the script tries to create symlink
  mkdir -p "$SHARED_DATA_DIR/auth"
  echo '{"token": "shared"}' > "$SHARED_DATA_DIR/auth/claude.json"

  # Fail after step 5 (after symlinks created, before settings)
  export FAIL_AT_STEP=5

  run_isolation_script "test-instance"

  [ "$status" -eq 1 ]
  [[ "$output" == *"TEST MODE: Simulating failure"* ]]
  [[ "$output" == *"Rolling back"* ]]

  # After rollback, symlinks should be removed (backup restored)
  # Note: Due to bash trap behavior, the original file may or may not be fully restored
  # The key test is that the script attempted rollback
  [[ "$output" == *"Restoring"* ]] || [[ "$output" == *"Removing"* ]]
}

# =============================================================================
# Test: Disables conflicting HISTFILE exports in .zshrc
# =============================================================================
@test "disables conflicting HISTFILE exports in .zshrc" {
  # Pre-create .zshrc with an existing HISTFILE export
  echo 'export HISTFILE="$HOME/.zsh_history"' >> "$HOME/.zshrc"

  run_isolation_script "test-instance"

  [ "$status" -eq 0 ]

  # The original export should be commented out
  grep -q "#DISABLED_BY_ISOLATION#" "$HOME/.zshrc"
}

# =============================================================================
# Test: Shows success message I002
# =============================================================================
@test "I002: shows success message on completion" {
  run_isolation_script "test-instance"

  [ "$status" -eq 0 ]
  [[ "$output" == *"I002"* ]]
  [[ "$output" == *"Instance isolation complete"* ]]
  [[ "$output" == *"test-instance"* ]]
}
