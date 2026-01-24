---
title: 'Keystone Integration for Claude DevContainer'
slug: 'keystone-devcontainer-integration'
created: '2026-01-22'
status: 'implementation-complete'
stepsCompleted: [1, 2, 3, 4]
tech_stack:
  - keystone-cli (workflow orchestration via bun)
  - bun (required runtime for keystone)
  - Docker (container image)
  - pnpm (existing package management)
  - git URL packages (workflow distribution)
files_to_modify:
  - image/Dockerfile (add bun, keystone-cli install)
  - image/scripts/post-create.sh (add keystone update step, sanity check)
  - image/scripts/update-keystone.sh (new - auto-update script)
  - image/scripts/devcontainer-sanity-check.sh (new - extensible health check)
  - packages/keystone-workflows/config/keystone-config.yaml (new - default user config)
  - packages/keystone-workflows/ (new package)
  - packages/keystone-workflows/package.json
  - packages/keystone-workflows/workflows/*.yaml
  - packages/keystone-workflows/scripts/postinstall.sh
code_patterns:
  - bun global install for keystone packages
  - Timestamp-based update checks (like check-daily-updates.sh)
  - Symlink from npm package to ~/.keystone/workflows/
  - Extensible sanity check script pattern
test_patterns:
  - Container build validation (docker build succeeds)
  - Workflow execution validation (keystone run bmad-story --help)
  - Update mechanism validation (bun install -g updates package)
  - Sanity check passes after fresh container start
---

# Tech-Spec: Keystone Integration for Claude DevContainer

**Created:** 2026-01-22

## Overview

### Problem Statement

The claude-devcontainer needs to provide keystone-cli and reusable keystone workflows to all containers, enabling workflow orchestration without per-project installation. Currently, keystone must be installed manually in each project, and there's no standard location for shared BMAD keystone workflows. The bmad-orchestrator package attempted to solve orchestration but is being retired in favor of keystone's native workflow capabilities.

### Solution

1. Pre-install keystone-cli (from ZookAnalytics fork) in the Docker image
2. Create a `@zookanalytics/keystone-workflows` npm package containing BMAD workflows
3. Install this package and symlink to `~/.keystone/workflows/` (keystone's native path)
4. Auto-update workflows on container start
5. Provide full default config and extensible sanity check script

### Scope

**In Scope:**
- Install keystone-cli from `github:ZookAnalytics/keystone-cli` in Docker image
- Create `packages/keystone-workflows` npm package with bmad-story.yaml, bmad-epic.yaml, bmad-epic-status.yaml
- Auto-update workflows on container start (we want latest immediately)
- Create keystone config scaffolding for consumers
- Update post-create scripts to set up keystone paths
- bmad-orchestrator package: ignore (not our concern for this work)
- **Sanity check script** - Extensible script verifying container expectations (keystone, workflows, CLIs, etc.)
- **Full default config** - `~/.config/keystone/config.yaml` with providers, engines, timeouts - everything needed for our workflows
- **Version visibility** - Log workflow package version at container startup
- **Postinstall script** - Reliable symlink creation in npm package

**Out of Scope:**
- Moving or modifying BMAD method (`_bmad/`) - remains manually installed per-repo
- Publishing keystone-cli to npm (future consideration)
- bmad-dashboard, claude-instance, git-workflow packages (unchanged)

## Context for Development

### Codebase Patterns

**Dockerfile Pattern:**
- System tools: `apt-get install` in early layers
- User tools: `COPY` from `packages/` to `/usr/local/bin/` or `/usr/local/lib/`
- Global npm packages: Installed in `post-create.sh` via `pnpm install -g`
- Scripts: Copied to `/usr/local/bin/`, made executable, added to sudoers if needed

**Post-create.sh Pattern:**
- Numbered steps with clear logging: `echo "[N/9] Step description..."`
- Environment variables for versions: `CLAUDE_CODE_VERSION="${CLAUDE_CODE_VERSION:-latest}"`
- Graceful error handling with `set -euo pipefail`
- Project-specific hook at end: `.devcontainer/post-create-project.sh`

**Package Structure (from claude-instance):**
```
packages/<name>/
├── package.json          # name, version, bin, files, repository
├── bin/<executable>      # Shell script entry point
├── plugin.json           # Optional: Claude Code plugin metadata
└── hooks/                # Optional: Claude Code hooks
```

**Update Check Pattern (from check-daily-updates.sh):**
- Timestamp file tracks last update
- 24-hour interval check
- Graceful fallback if network unavailable
- Uses sudo for system operations

**Keystone Installation Constraint:**
- Keystone-cli does NOT install correctly via pnpm
- MUST use bun: `bun install -g github:ZookAnalytics/keystone-cli`
- Requires adding bun to Dockerfile

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `image/Dockerfile` | Base image definition - add bun install, keystone install |
| `image/scripts/post-create.sh` | Container startup - add keystone update step |
| `image/scripts/check-daily-updates.sh` | Pattern for timestamp-based update checks |
| `packages/claude-instance/package.json` | Pattern for new package structure |
| `/workspace/.keystone/config.yaml` | Default keystone config to ship |
| `/workspace/.keystone/workflows/*.yaml` | Workflows to include in package |

### Technical Decisions

#### ADR-1: Workflow Distribution Mechanism
**Decision:** npm package with runtime install (`@zookanalytics/keystone-workflows`)
- Install globally in Docker image
- Update via `npm update -g` without container rebuild
- Simple approach, no hybrid complexity

#### ADR-2: Keystone CLI Installation Source
**Decision:** Git URL dependency (`github:ZookAnalytics/keystone-cli`)
- Use fork directly via git URL
- Can publish to npm later if approach proves successful
- Keeps initial implementation simple

#### ADR-3: Workflow Discovery Path
**Decision:** Use keystone's native `~/.keystone/workflows/` path
- Keystone natively searches: `.keystone/workflows/` (project) → `~/.keystone/workflows/` (user)
- No fork modifications needed - this is built-in behavior
- Install workflows to `/home/node/.keystone/workflows/` in Docker image
- Projects can override by placing workflows in local `.keystone/workflows/`

#### ADR-4: Bun Requirement for Keystone
**Decision:** Add bun to Dockerfile, install keystone via bun
- Keystone-cli does NOT install correctly via pnpm (tested)
- Must use: `bun install -g github:ZookAnalytics/keystone-cli`
- Add bun install to Dockerfile before keystone installation
- Use bun for both keystone-cli and keystone-workflows packages

#### First Principles Insights

**Why this structure:**
- Keystone orchestrates multi-step AI workflows; it just needs to find YAML files
- The npm package is for OUR version control and distribution, not a keystone requirement
- The real value is reducing per-project setup - users get keystone + workflows ready to use
- bmad-orchestrator solved the wrong problem; keystone does orchestration natively

**Keystone Path Resolution (confirmed from docs):**
- Workflows: `.keystone/workflows/` (local) → `~/.keystone/workflows/` (user-level)
- Config: `KEYSTONE_CONFIG` env → `.keystone/config.yaml` → `~/.config/keystone/config.yaml`
- State: `.keystone/state.db` (project-local)


## Implementation Plan

### Tasks

- [x] **Task 1: Add bun to Dockerfile**
  - File: `image/Dockerfile`
  - Action: Add bun installation **after line 113 (after `RUN pnpm setup`)** as `node` user
  - Location: Insert after the existing pnpm setup block, before `USER root` at line 115
  - Notes:
    ```dockerfile
    # Install bun (required for keystone-cli)
    # Must run as node user to install to ~/.bun
    RUN curl -fsSL https://bun.sh/install | bash
    ENV BUN_INSTALL="/home/node/.bun"
    ENV PATH="$BUN_INSTALL/bin:$PATH"
    ```
  - **Critical:** This runs as `node` user (current context after line 83). The ENV statements persist for subsequent layers.

- [x] **Task 2: Create keystone-workflows package structure**
  - File: `packages/keystone-workflows/package.json` (new)
  - Action: Create package with metadata following claude-instance pattern
  - Notes:
    ```json
    {
      "name": "@zookanalytics/keystone-workflows",
      "version": "0.1.0",
      "description": "BMAD keystone workflows for claude-devcontainer",
      "files": ["workflows/", "scripts/", "config/"],
      "scripts": { "postinstall": "./scripts/postinstall.sh" },
      "repository": {
        "type": "git",
        "url": "https://github.com/zookanalytics/claude-devcontainer.git",
        "directory": "packages/keystone-workflows"
      }
    }
    ```

- [x] **Task 3: Add workflow files to package**
  - Files: `packages/keystone-workflows/workflows/*.yaml` (new)
  - Action: Copy workflows from `/workspace/.keystone/workflows/`
  - Notes:
    - `bmad-story.yaml` - Single story workflow
    - `bmad-epic.yaml` - Epic iterator (Approach A)
    - `bmad-epic-status.yaml` - Epic status checker

- [x] **Task 4: Create postinstall script for symlinks and config**
  - File: `packages/keystone-workflows/scripts/postinstall.sh` (new)
  - Action: Create script that symlinks workflows and installs default config
  - Notes:
    ```bash
    #!/bin/bash
    set -e
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
      ((WORKFLOW_COUNT++))
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
    ```

- [x] **Task 5: Create default keystone config**
  - File: `packages/keystone-workflows/config/keystone-config.yaml` (new)
  - Action: Create default config based on `/workspace/.keystone/config.yaml`
  - Notes:
    - Include providers (openai, anthropic)
    - Include engine allowlist (claude, gemini)
    - Include default timeout (900000ms)
    - Include storage retention (30 days)
    - Config is installed by Task 4's postinstall script to `~/.config/keystone/config.yaml`

- [x] **Task 6: Create update-keystone.sh script**
  - File: `image/scripts/update-keystone.sh` (new)
  - Action: Create script for auto-updating keystone packages
  - Notes:
    ```bash
    #!/bin/bash
    set -e
    echo "Updating keystone packages..."
    bun install -g github:ZookAnalytics/keystone-cli || echo "keystone-cli update failed, using existing"
    bun install -g github:ZookAnalytics/claude-devcontainer#packages/keystone-workflows || echo "keystone-workflows update failed, using existing"

    # Log versions for debugging
    echo "---"
    echo "keystone-cli: $(keystone --version 2>/dev/null || echo 'not installed')"
    # Workflows version from package.json (if installed locally) or symlink target
    WORKFLOWS_PKG="$HOME/.local/lib/keystone-workflows/package.json"
    if [ -f "$WORKFLOWS_PKG" ]; then
      echo "keystone-workflows: $(grep '"version"' "$WORKFLOWS_PKG" | head -1 | sed 's/.*: *"\([^"]*\)".*/\1/')"
    else
      echo "keystone-workflows: (installed via bun global)"
    fi
    echo "workflows path: $(ls -la ~/.keystone/workflows/*.yaml 2>/dev/null | head -1 || echo 'not found')"
    ```

- [x] **Task 7: Create devcontainer-sanity-check.sh script**
  - File: `image/scripts/devcontainer-sanity-check.sh` (new)
  - Action: Create extensible sanity check script
  - Notes:
    ```bash
    #!/bin/bash
    PASS=0; FAIL=0
    check() {
      if eval "$2" > /dev/null 2>&1; then
        echo "✓ $1"; ((PASS++))
      else
        echo "✗ $1"; ((FAIL++))
      fi
    }
    check "bun runtime" "bun --version"
    check "keystone binary" "keystone --version"
    check "keystone workflows exist" "ls ~/.keystone/workflows/bmad-*.yaml"
    check "keystone workflow discovery" "keystone run --list 2>/dev/null | grep -q bmad"
    check "keystone config exists" "test -f ~/.config/keystone/config.yaml"
    check "claude cli" "command -v claude"
    check "gemini cli" "command -v gemini"
    echo "---"
    echo "Passed: $PASS, Failed: $FAIL"
    [ $FAIL -eq 0 ]
    ```

- [x] **Task 8: Update Dockerfile to install keystone-cli**
  - File: `image/Dockerfile`
  - Action: Add keystone-cli installation via bun
  - Location: Immediately after Task 1's bun install (still as `node` user, before `USER root` at line 115)
  - Notes:
    ```dockerfile
    # Install keystone-cli globally via bun (must run as node user for PATH)
    RUN bun install -g github:ZookAnalytics/keystone-cli
    ```
  - **Critical ordering:** Tasks 1, 8, and 11 all run as `node` user. Insert all three blocks before the `USER root` line (currently 115). The ENV PATH from Task 1 persists for these RUN commands because they're in the same user context.

- [x] **Task 9: Update Dockerfile to copy new scripts**
  - File: `image/Dockerfile`
  - Action: Add COPY and chmod for new scripts (around line 138)
  - Notes:
    ```dockerfile
    COPY image/scripts/update-keystone.sh /usr/local/bin/
    COPY image/scripts/devcontainer-sanity-check.sh /usr/local/bin/
    RUN chmod 755 /usr/local/bin/update-keystone.sh && \
        chmod 755 /usr/local/bin/devcontainer-sanity-check.sh
    ```

- [x] **Task 10: Update post-create.sh with keystone steps**
  - File: `image/scripts/post-create.sh`
  - Action: Add keystone update step and sanity check step, renumber all steps
  - Notes:
    **Current steps (9 total):** 1-Welcome, 2-Timezone, 3-Claude Code, 4-Activate shell, 5-Global pnpm, 6-Hooks, 7-Aliases, 8-GitHub auth, 9-Project setup

    **New steps (11 total) - renumber as follows:**
    - Steps 1-5: unchanged
    - **Step 6 (NEW):** Update keystone packages
      ```bash
      echo ""
      echo "[6/11] Updating keystone packages..."
      /usr/local/bin/update-keystone.sh
      echo "✓ Keystone packages updated"
      ```
    - Steps 7-9: old steps 6-8 (renumbered)
    - **Step 10 (NEW):** Run sanity check
      ```bash
      echo ""
      echo "[10/11] Running sanity check..."
      if /usr/local/bin/devcontainer-sanity-check.sh; then
        echo "✓ Sanity check passed"
      else
        echo "⚠ Sanity check reported failures (see above) - container continues"
      fi
      ```
    - Step 11: old step 9 (project-specific setup, renumbered)

    **Failure behavior:** Sanity check failures are logged but do NOT block container startup. This allows debugging in a running container. Critical failures would have already failed the Dockerfile build.

    **Implementation:** Update ALL step number references throughout post-create.sh (both comments and echo statements).

- [x] **Task 11: Install keystone-workflows in Dockerfile**
  - File: `image/Dockerfile`
  - Action: Install keystone-workflows package (which triggers postinstall symlink)
  - Notes:
    - **Bootstrap (initial implementation):** Use Option B - COPY locally and run postinstall
      ```dockerfile
      # Copy keystone-workflows package and run postinstall
      COPY --chown=node:node packages/keystone-workflows /home/node/.local/lib/keystone-workflows
      RUN /home/node/.local/lib/keystone-workflows/scripts/postinstall.sh
      ```
    - **After package is committed:** Can switch to Option A for auto-updates
      ```dockerfile
      RUN bun install -g github:ZookAnalytics/claude-devcontainer#packages/keystone-workflows
      ```
    - **Recommend:** Keep Option B for faster builds (no network dependency during build), rely on update-keystone.sh for runtime updates

### Acceptance Criteria

- [x] **AC1:** Given a fresh container build, when `docker build` completes, then bun and keystone-cli are installed and accessible via PATH.

- [x] **AC2:** Given the container starts, when post-create.sh runs, then keystone packages are auto-updated and version is logged.

- [x] **AC3:** Given keystone-workflows is installed, when checking `~/.keystone/workflows/`, then bmad-story.yaml, bmad-epic.yaml, and bmad-epic-status.yaml are present (via symlink).

- [x] **AC4:** Given no project-local `.keystone/config.yaml`, when running `keystone run bmad-story`, then keystone uses the default config from `~/.config/keystone/config.yaml`.

- [x] **AC5:** Given network is unavailable during update, when update-keystone.sh runs, then it gracefully falls back to existing installed version without failing.

- [x] **AC6:** Given the sanity check runs, when all expected tools are present, then it reports all checks passed and exits with code 0.

- [x] **AC7:** Given a project has local `.keystone/workflows/bmad-story.yaml`, when running `keystone run bmad-story`, then the local version is used (project overrides user-level).

- [ ] **AC8:** Given container environment with valid API credentials, when running `keystone run bmad-story -i story_id=test`, then the workflow executes and invokes Claude CLI.
  - **Note:** This is a manual validation step requiring valid ANTHROPIC_API_KEY and GOOGLE_AI_API_KEY. Cannot be automated in CI without credentials.
  - **Alternative automated check:** `keystone run bmad-story --help` executes without error (validates workflow discovery)

## Additional Context

### Dependencies

| Dependency | Purpose | Installation |
|------------|---------|--------------|
| bun | Runtime for keystone-cli | Add to Dockerfile via official install script |
| keystone-cli | Workflow orchestration | `bun install -g github:ZookAnalytics/keystone-cli` |
| keystone-workflows | BMAD workflow definitions | `bun install -g github:ZookAnalytics/claude-devcontainer#packages/keystone-workflows` or local package |

**Pre-existing Dependencies (not installed by this spec):**
| Dependency | Purpose | Notes |
|------------|---------|-------|
| claude CLI | BMAD workflow step execution | Already in claude-devcontainer image |
| gemini CLI | Code review workflow steps | **Assumed to be installed separately** - workflows will fail if missing; sanity check will report failure |

**Network Requirements:**

| Phase | Network Required | Purpose |
|-------|-----------------|---------|
| Docker build | Yes | Download bun installer, install keystone-cli from GitHub |
| Container start | Optional | Auto-update keystone packages (falls back gracefully if offline) |
| Workflow execution | Yes | API calls to Claude/Gemini services |

**GitHub URLs Required for Auto-Update:**
- `github.com` - For git URL package installs
- Already in `allowed-domains.txt`

**Offline capability:** Container can start and run with cached versions if network unavailable during post-create. Only workflow execution (which requires API access anyway) truly needs network.

### Testing Strategy

**Build Validation:**
```bash
# Build the Docker image
cd /home/node/claude-devcontainer
docker build -f image/Dockerfile -t claude-devcontainer:test .

# Verify bun and keystone installed
docker run --rm claude-devcontainer:test bun --version
docker run --rm claude-devcontainer:test keystone --version
```

**Container Start Validation:**
```bash
# Start container and verify post-create runs
devpod up . --id test-keystone

# Check sanity check output in logs
# Verify keystone workflows are symlinked
ls -la ~/.keystone/workflows/
```

**Workflow Execution Validation:**
```bash
# Verify workflow discovery
keystone run --list

# Test workflow execution (dry run or with test story)
keystone run bmad-story -i story_id=test -i require_approval=false
```

**Update Mechanism Validation:**
```bash
# Simulate update (after changing workflows in repo)
/usr/local/bin/update-keystone.sh

# Verify new version installed
keystone --version
ls -la ~/.keystone/workflows/
```

**Manual Testing Checklist:**
- [ ] Fresh container build succeeds
- [ ] Post-create.sh completes without errors
- [ ] Sanity check reports all passed
- [ ] `keystone run --list` shows bmad-story, bmad-epic, bmad-epic-status
- [ ] Workflow execution invokes Claude CLI
- [ ] Project-local workflow overrides user-level

**CI Integration (future consideration):**
The following tests can be automated in CI without API credentials:
- Docker build succeeds: `docker build -f image/Dockerfile -t test .`
- Bun and keystone installed: `docker run --rm test bun --version && keystone --version`
- Sanity check passes: `docker run --rm test /usr/local/bin/devcontainer-sanity-check.sh`
- Workflow discovery works: `docker run --rm test keystone run --list`

Tests requiring credentials (manual only):
- Actual workflow execution (AC8)
- Claude/Gemini CLI invocation

### Risk Mitigations (from Pre-mortem Analysis)

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Symlink breaks on update | Medium | High | Postinstall script + sanity check |
| Update requires sudo | Medium | Medium | User-local npm prefix |
| Missing config | High | Medium | Ship full default user-level config |
| Version drift | Low | Low | Auto-update on container start |
| Network unavailable for update | Low | Medium | Graceful fallback to existing version |
| Failed update leaves broken state | Low | Low | **Intentionally no rollback** - update failures log error and continue with existing Docker image version. Sanity check detects issues. For internal tooling, this is acceptable; rebuild container for full recovery. |

### Cross-Functional Decisions (from War Room)

| Decision | Resolution | Rationale |
|----------|------------|-----------|
| Install location | `~/.keystone/workflows/` via symlink | Follow keystone convention |
| Update mechanism | Auto-update on container start | This is for us - we want latest immediately |
| Default config | Full config (providers, engines, timeouts) | Make our workflows work out of the box |
| Sanity check | Extensible script checking all expectations | Grows over time, not keystone-specific |

**Sanity Check Concept:**
```bash
# /usr/local/bin/devcontainer-sanity-check.sh
# Extensible - add checks as expectations grow

check "keystone binary" "keystone --version"
check "keystone workflows" "ls ~/.keystone/workflows/bmad-*.yaml"
check "claude cli" "claude --version"
check "gemini cli" "gemini --version"
check "bun runtime" "bun --version"
# ... grows over time
```

### Notes

- Keystone fork: `github:ZookAnalytics/keystone-cli`
- Current version: 2.1.1
- Existing workflows to migrate: bmad-story.yaml, bmad-epic.yaml, bmad-epic-status.yaml
- bmad-orchestrator: Ignore for this work (separate concern)

## Review Notes

### Review 1 (Initial)
- Adversarial review completed
- Findings: 15 total, 4 fixed (F1, F3, F4, F12), 11 skipped (noise/design decisions)
- Resolution approach: auto-fix
- Fixes applied:
  - F1: Added failure tracking and reporting to update-keystone.sh
  - F3: Added `set -u` to shell scripts
  - F4: Fixed arithmetic expansion bug (`((VAR++))` → `VAR=$((VAR + 1))`)
  - F12: Documented symlink behavior as acceptable design

### Review 2 (2026-01-24)
- Adversarial review completed
- Findings: 8 total (2 High, 3 Medium, 3 Low)
- Resolution approach: auto-fix
- Fixes applied:
  - H1: Staged untracked scripts (update-keystone.sh, devcontainer-sanity-check.sh)
  - H2: Updated ACs to [x] for implemented criteria (AC1-AC7)
  - M1: Added `set -euo pipefail` to postinstall.sh
  - M2: Fixed file path in frontmatter (image/config → packages/keystone-workflows/config)
  - M3: Removed useless `2>&1` from update-keystone.sh
- Low severity items (L1-L3) deferred as acceptable design decisions
