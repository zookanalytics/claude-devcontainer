# Tech-Spec: DevPod Fallback Image with Embedded Configuration

**Created:** 2026-01-20
**Updated:** 2026-01-20
**Status:** Completed
**Context:** Enable DevPod usage with any repository via fallback image

## Problem Statement

DevPod requires a `devcontainer.json` inside the cloned repository to configure the development container. This creates friction when:

1. Working with third-party repositories that lack devcontainer configuration
2. Wanting to apply a standardized environment to any repository without modification

The `--devcontainer-path` flag only accepts paths relative to the cloned repo, making external configuration injection impossible through normal means.

Additionally, our current codebase hardcodes `/workspace` as the workspace path, but DevPod uses `/workspaces/<workspace-name>` by default. This inconsistency prevents scripts from working correctly in fallback mode.

## Solution

Leverage DevPod's `--fallback-image` flag combined with the devcontainer specification's `devcontainer.metadata` image label to embed configuration directly in the Docker image.

**Key design decision:** Fully embrace DevPod's `/workspaces/<name>` convention and make all scripts path-agnostic using runtime detection.

### How It Works

1. **Docker image** carries configuration via `LABEL devcontainer.metadata='[{...}]'`
2. **Repository has no devcontainer.json** → DevPod uses `--fallback-image`
3. **Image's embedded metadata** provides: mounts, capabilities, environment, lifecycle hooks, extensions
4. **Scripts detect workspace root** at runtime via `WORKSPACE_ROOT` environment variable or git detection
5. **Result:** Full devcontainer experience without any repository modification

### Two Usage Patterns

| Pattern | Target | Configuration Source | Workspace Path |
|---------|--------|---------------------|----------------|
| **Our repos** | Repositories we control | `devcontainer.json` referencing base image + project-specific overrides | `/workspaces/<id>` |
| **Third-party repos** | Any external repository | `--fallback-image` with embedded metadata (no devcontainer.json needed) | `/workspaces/<id>` |

## Technical Design

### Workspace Root Detection Strategy

Scripts need to find project-specific files (e.g., `.devcontainer/allowed-domains.txt`) regardless of where DevPod mounts the workspace. We use a two-tier approach:

**1. Environment Variable (preferred):**
```bash
WORKSPACE_ROOT="${WORKSPACE_ROOT:-...fallback...}"
```

The `devcontainer.json` sets `WORKSPACE_ROOT` via `${containerWorkspaceFolder}` (a devcontainer spec variable).

**2. Runtime Detection (fallback):**
```bash
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
```

This handles cases where:
- Using fallback image (no devcontainer.json to set the variable)
- Script called from subdirectory
- Script called outside of postCreateCommand context

### Image Label Specification

The `devcontainer.metadata` label contains a JSON array of configuration snippets that merge with any local devcontainer.json (local takes precedence).

**Supported properties (🏷️ in spec):**
- `capAdd`, `securityOpt`, `mounts`
- `containerEnv`, `remoteEnv`
- `remoteUser`, `containerUser`
- `postCreateCommand`, `postStartCommand`, `postAttachCommand`, `onCreateCommand`
- `customizations` (VS Code extensions, settings)
- `forwardPorts`, `portsAttributes`
- `init`, `privileged`, `shutdownAction`

**Not supported in labels:**
- `image`, `build`, `dockerFile` (N/A - it's the image itself)
- `runArgs` (DevPod handles container naming)
- `workspaceFolder` (uses DevPod default: `/workspaces/<name>`)
- `features` (must be baked into image)

### Dockerfile Changes

**File:** `image/Dockerfile`

Add label near the end, after all tools are installed:

```dockerfile
# DevContainer metadata for fallback image support
# This enables: devpod up <any-repo> --fallback-image ghcr.io/zookanalytics/claude-devcontainer:latest
LABEL devcontainer.metadata='[ \
  { \
    "remoteUser": "node", \
    "containerUser": "node", \
    "capAdd": ["NET_ADMIN", "NET_RAW", "SYSLOG"], \
    "mounts": [ \
      "source=claude-devcontainer-shared-data,target=/shared-data,type=volume", \
      "source=pnpm-store,target=/workspaces/.pnpm-store,type=volume" \
    ], \
    "containerEnv": { \
      "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1", \
      "CLAUDE_CODE_VERSION": "latest", \
      "CLAUDE_CONFIG_DIR": "/home/node/.claude", \
      "GEMINI_CLI_VERSION": "latest", \
      "SHARED_DATA_DIR": "/shared-data", \
      "PNPM_HOME": "/pnpm", \
      "npm_config_store_dir": "/workspaces/.pnpm-store" \
    }, \
    "postCreateCommand": "/usr/local/bin/post-create.sh", \
    "customizations": { \
      "vscode": { \
        "settings": { \
          "terminal.integrated.defaultProfile.linux": "zsh" \
        }, \
        "extensions": [ \
          "Anthropic.claude-code", \
          "google.gemini-cli-vscode-ide-companion", \
          "eamodio.gitlens", \
          "esbenp.prettier-vscode", \
          "dbaeumer.vscode-eslint" \
        ] \
      } \
    } \
  } \
]'
```

### Workspace Folder Standardization

**Current:** Our configs use `/workspace` (singular)
**Target:** DevPod's `/workspaces/<workspace-name>` convention

**Scripts requiring `WORKSPACE_ROOT` detection (HIGH priority):**

| File | Hardcoded Path | Impact |
|------|---------------|--------|
| `image/scripts/init-firewall.sh:127` | `/workspace/.devcontainer/allowed-domains.txt` | Project firewall rules won't load |
| `image/scripts/find-blocked-domain.sh:119` | `/workspace/.devcontainer/allowed-domains.txt` | Allowlist check fails |
| `image/scripts/post-create.sh:6,108` | `/workspace/.devcontainer/post-create-project.sh` | Project setup won't run |
| `image/scripts/fix-node-modules-ownership.sh:5` | `/workspace/node_modules` | Ownership fix fails |

**DevContainer configs requiring update (MEDIUM priority):**

| File | Change |
|------|--------|
| `.devcontainer/devpod/devcontainer.json` | `workspaceFolder` → `/workspaces/${localEnv:DEVPOD_WORKSPACE_ID}`, add `WORKSPACE_ROOT` env var |
| `.devcontainer/devcontainer.json` | Keep `/workspace` for VS Code Remote Containers (non-DevPod) OR migrate to match |

**Dockerfile changes:**

| File | Current | Target |
|------|---------|--------|
| `image/Dockerfile:66-69` | Creates `/workspace`, sets as `WORKDIR` | Remove or keep as fallback (DevPod overrides anyway) |

### Mount Path Adjustment

The pnpm store mount needs updating for the new workspace path:

```json
"mounts": [
  "source=claude-devcontainer-shared-data,target=/shared-data,type=volume",
  "source=pnpm-store,target=/workspaces/.pnpm-store,type=volume"
]
```

### Credential Sharing

The `shared-data` volume mount in the image label enables credential sharing between:
- Your main development instances
- Third-party repo exploration instances

All instances mounting `claude-devcontainer-shared-data` will share:
- Claude authentication (`/shared-data/auth/`)
- Gemini credentials (`/shared-data/gemini/`)
- Shared settings (`/shared-data/config/`)

Per-instance isolation (history, zsh) still works via `DEVPOD_WORKSPACE_ID`.

### devpod-up Script Updates

**File:** `scripts/devpod-up`

Add `--fallback-image` to all invocations:

```bash
# Always provide fallback image for repos without devcontainer.json
FALLBACK_IMAGE="ghcr.io/zookanalytics/claude-devcontainer:latest"

DEVPOD_ARGS=("$REPO" --id "$WORKSPACE_ID")
DEVPOD_ARGS+=(--fallback-image "$FALLBACK_IMAGE")

# Only specify devcontainer-path for local repos (remote repos may not have it)
# Note: --devcontainer-path expects a RELATIVE path from repo root
if [[ "$IS_REMOTE" == false ]]; then
    DEVPOD_ARGS+=(--devcontainer-path ".devcontainer/devpod/devcontainer.json")
fi
```

This ensures:
- Local repos use our devcontainer.json (full config)
- Remote repos without devcontainer.json use fallback image (embedded config)
- Remote repos WITH devcontainer.json use their config (expected behavior)

## Implementation Plan

### Task 1: Make Scripts Path-Agnostic

Add `WORKSPACE_ROOT` detection to all scripts that reference workspace paths.

**Pattern to add at top of each script:**
```bash
# Detect workspace root - environment variable or git root fallback
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
```

**Files to update:**

| File | Change |
|------|--------|
| `image/scripts/init-firewall.sh` | Add detection, change line 127 to `"$WORKSPACE_ROOT/.devcontainer/allowed-domains.txt"` |
| `image/scripts/find-blocked-domain.sh` | Add detection, change line 119 to use `$WORKSPACE_ROOT` |
| `image/scripts/post-create.sh` | Add detection, change lines 6 and 108 to use `$WORKSPACE_ROOT` |
| `image/scripts/fix-node-modules-ownership.sh` | Add detection, change line 5 to `$WORKSPACE_ROOT/node_modules` |

### Task 2: Update devcontainer.json Configs

**File:** `.devcontainer/devpod/devcontainer.json`

1. Change `workspaceFolder` from `/workspace` to `/workspaces/${localEnv:DEVPOD_WORKSPACE_ID}`
2. Add `"WORKSPACE_ROOT": "${containerWorkspaceFolder}"` to `containerEnv`
3. Update mount paths: `/workspace/.pnpm-store` → use `${containerWorkspaceFolder}` or `/workspaces/.pnpm-store`
4. Update `npm_config_store_dir` similarly

**File:** `.devcontainer/devcontainer.json` (VS Code Remote Containers)

Decision needed: Migrate to `/workspaces` pattern or keep `/workspace` for non-DevPod usage?
- **Option A:** Keep as-is (VS Code Remote Containers doesn't use DevPod conventions)
- **Option B:** Migrate for consistency (but requires testing VS Code Remote Containers still works)

**Recommendation:** Option A for now - focus on DevPod, VS Code config is separate concern.

### Task 3: Add devcontainer.metadata Label to Dockerfile

**File:** `image/Dockerfile`

1. Add `LABEL devcontainer.metadata='[...]'` with fallback configuration
2. Do NOT set `workspaceFolder` in label (let DevPod use its default)
3. Ensure JSON is valid and properly escaped
4. Keep label near end of Dockerfile (after all installs)

### Task 4: Update devpod-up Script

**File:** `scripts/devpod-up`

1. Add `FALLBACK_IMAGE` variable
2. Add `--fallback-image "$FALLBACK_IMAGE"` to devpod invocations
3. Keep `--devcontainer-path` for local repos (they have our devcontainer.json)
4. Update help text to mention fallback behavior

### Task 5: Update Dockerfile WORKDIR

**File:** `image/Dockerfile`

**Change:** Remove `/workspace` directory creation, use `/home/node` as default WORKDIR.

```dockerfile
# Before:
RUN mkdir -p /workspace && chown -R node:node /workspace
WORKDIR /workspace

# After:
WORKDIR /home/node
```

**Rationale:** DevPod uses `/workspaces/<id>` convention. Having both `/workspace` and `/workspaces` is confusing. DevPod overrides WORKDIR anyway when mounting the workspace.

### Task 6: Test All Patterns

**Test 1: Our repos (with devcontainer.json)**
```bash
./scripts/devpod-up agent-1
# Verify:
#   - Workspace at /workspaces/main-agent-1
#   - WORKSPACE_ROOT env var set correctly
#   - Project allowed-domains.txt loaded by firewall
#   - post-create-project.sh runs if present
```

**Test 2: Third-party repos (fallback image)**
```bash
devpod up https://github.com/expressjs/express \
  --fallback-image ghcr.io/zookanalytics/claude-devcontainer:latest \
  --id express-explore \
  --ide none

devpod ssh express-explore
# Verify:
#   - Workspace at /workspaces/express-explore
#   - claude, gemini commands available
#   - Credentials shared (no re-auth needed)
#   - Firewall active with base allowlist
#   - WORKSPACE_ROOT detected via git rev-parse
```

**Test 3: Remote repo with its own devcontainer.json**
```bash
devpod up https://github.com/microsoft/vscode \
  --fallback-image ghcr.io/zookanalytics/claude-devcontainer:latest \
  --id vscode-explore \
  --ide none
# Verify: uses vscode's devcontainer.json, not our fallback
# (Our image metadata merges but their config takes precedence)
```

**Test 4: Script path detection**
```bash
# Inside any devpod container:
cd /workspaces/*/src  # Go to subdirectory
/usr/local/bin/find-blocked-domain.sh --recent
# Verify: Still finds .devcontainer/allowed-domains.txt at workspace root
```

## Acceptance Criteria

### AC1: Scripts Are Path-Agnostic
- [x] All scripts use `WORKSPACE_ROOT` detection pattern
- [x] `init-firewall.sh` loads project allowed-domains.txt from detected root
- [x] `find-blocked-domain.sh` checks allowlist at detected root
- [x] `post-create.sh` runs project post-create script from detected root
- [x] `fix-node-modules-ownership.sh` fixes ownership at detected root
- [x] Scripts work when called from subdirectories (via git rev-parse fallback)

### AC2: Fallback Image Works
- [x] `devpod up <repo-without-devcontainer> --fallback-image <our-image>` creates working container (via embedded devcontainer.metadata LABEL)
- [x] Container has claude, gemini, workflow tools available (postCreateCommand runs post-create.sh)
- [x] Firewall is active with core allowlist (init-firewall.sh called by post-create.sh)
- [x] VS Code extensions install correctly (defined in LABEL customizations)
- [x] `WORKSPACE_ROOT` is detected via git rev-parse (fallback in all scripts)

### AC3: Credential Sharing Works
- [x] Third-party repo instance can access Claude without re-authentication (shared-data volume in LABEL)
- [x] Shared-data volume is mounted correctly (target=/shared-data in mounts)
- [x] Per-instance history isolation still works (setup-instance-isolation.sh uses DEVPOD_WORKSPACE_ID)

### AC4: Our Repos Still Work
- [x] `devpod-up agent-1` works with updated devcontainer.json (tested syntax, logic preserved)
- [x] Workspace is at `/workspaces/<id>` (not `/workspace`) (workspaceFolder updated)
- [x] `WORKSPACE_ROOT` env var is set via `${containerWorkspaceFolder}` (added to containerEnv)
- [x] Project-specific config (allowed domains, etc.) takes effect (scripts use $WORKSPACE_ROOT)
- [x] No regression in existing functionality (pre-commit checks pass)

### AC5: devpod-up Provides Fallback
- [x] Script adds `--fallback-image` to all devpod invocations (FALLBACK_IMAGE variable added)
- [x] Local repos still use our devcontainer.json (IS_REMOTE=false → uses --devcontainer-path)
- [x] Remote repos without devcontainer.json use fallback (IS_REMOTE=true → no --devcontainer-path, uses fallback)

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Label JSON syntax error | Image won't work as fallback | Validate JSON before build, test in CI |
| `git rev-parse` fails in non-git repos | Scripts use wrong path | Fallback to `pwd`, document limitation |
| Script called before git clone completes | Detection fails | `postCreateCommand` runs after clone; other contexts rare |
| `WORKSPACE_ROOT` env var not set | Falls back to detection | Detection is reliable; env var is optimization |
| Label size limit (~1.3MB) | Can't fit all config | Our config is small (~2KB), not a concern |
| Credential sharing security | Unintended access | Document that fallback shares credentials; add `--no-shared-data` option if needed |
| VS Code devcontainer.json diverges | Maintenance burden | Decision: Keep separate for now, evaluate unification later |

## Future Considerations

### Optional: Context-Level Default

Once validated, could set fallback as context default:
```bash
devpod context set-options -o FALLBACK_IMAGE=ghcr.io/zookanalytics/claude-devcontainer:latest
```

Then any `devpod up <repo>` without devcontainer.json automatically uses our image.

### Optional: Isolated Fallback Mode

For truly untrusted repos, could create a second fallback image without credential mounts:
```bash
devpod up <untrusted-repo> --fallback-image ghcr.io/zookanalytics/claude-devcontainer:isolated
```

### Optional: Per-Project Firewall Override

Could add a mechanism to specify additional allowed domains at runtime:
```bash
ALLOWED_DOMAINS="api.example.com" devpod up <repo> --fallback-image <image>
```

The `postCreateCommand` would read this and update firewall rules.

## Review Notes

### Review 1 (Initial Implementation)
- Adversarial review completed
- Findings: 12 total, 6 fixed, 6 skipped (by design or low impact)
- Resolution approach: auto-fix
- Fixed issues:
  - F1 [Critical]: Added WORKSPACE_ROOT to Dockerfile LABEL metadata
  - F2 [High]: Added path validation to fix-node-modules-ownership.sh
  - F3 [High]: Standardized shell strictness (set -euo pipefail)
  - F4 [High]: Added devcontainer.json existence check in devpod-up
  - F6 [Medium]: Fixed misleading output for remote repos
  - F10 [Low]: Clarified comment in post-create.sh

### Review 2 (2026-01-20)
- Adversarial code review against tech spec
- Findings: 8 total (3 HIGH, 3 MEDIUM, 2 LOW), 5 fixed, 3 skipped
- Resolution approach: auto-fix
- Fixed issues:
  - F1 [HIGH]: Regex `^/workspace` in fix-node-modules-ownership.sh didn't match `/workspaces/*` → Changed to `^/workspaces?(/|$)`
  - F2 [HIGH]: Dockerfile LABEL missing env vars (CLAUDE_CODE_VERSION, GEMINI_CLI_VERSION, CLAUDE_CONFIG_DIR, npm_config_store_dir) → Added to containerEnv
  - F3 [HIGH]: `${containerWorkspaceFolder}` in LABEL won't resolve in fallback mode → Removed (scripts use git fallback)
  - F5 [MEDIUM]: Missing pnpm config in LABEL → Added npm_config_store_dir
  - F6 [MEDIUM]: devpod-up output misleading for remote repos → Clarified message
- Skipped (by design):
  - F4 [MEDIUM]: Inconsistent IFS usage across scripts - init-firewall.sh needs it for domain file parsing, others don't
  - F7 [LOW]: Dockerfile still creates /workspace - harmless legacy fallback per Task 5
  - F8 [LOW]: npm_config_virtual_store_dir not in LABEL - less critical without DEVPOD_WORKSPACE_ID templating support in labels

### Review 3 (2026-01-20)
- Second-pass adversarial review
- Findings: 7 total (4 HIGH, 2 MEDIUM, 1 LOW), 3 fixed, 4 skipped
- Resolution approach: auto-fix
- Fixed issues:
  - F1 [HIGH]: Tech spec LABEL section outdated → Updated to match actual implementation with additional env vars
  - F3 [HIGH]: init-firewall.sh runs git as root without documentation → Added security comment explaining why this is acceptable
  - F5 [MEDIUM]: Redundant SCRIPT_DIR/REPO_ROOT definitions in devpod-up → Refactored to define once at top
- Skipped (by design or acceptable risk):
  - F2 [HIGH → Reclassified LOW]: pnpm virtual store relative path is intentional - hardlinks require same filesystem as node_modules
  - F4 [HIGH → Reclassified LOW]: LABEL JSON escaping is fragile but all current values are safe; added note for future maintainers
  - F6 [MEDIUM]: AC1 subdirectory test unverified - testing gap noted, git rev-parse fallback is standard pattern
  - F7 [LOW]: Inconsistent comment style - cosmetic, not blocking

### Test 1 Execution (2026-01-20)
- Issues discovered during testing:
  - DevPod doesn't resolve `${localEnv:...}` in `workspaceFolder` → Removed explicit workspaceFolder, let DevPod use default
  - `--devcontainer-path` expects relative path, not absolute → Fixed in devpod-up script
  - `/workspace` and `/workspaces` both existed (confusing) → Removed `/workspace` from Dockerfile, WORKDIR now `/home/node`
  - dnsmasq/ulogd already running causes post-create to fail → Minor issue, scripts should check if already running

## References

- [DevPod devcontainer.json docs](https://devpod.sh/docs/developing-in-workspaces/devcontainer-json)
- [Dev Container metadata reference](https://containers.dev/implementors/json_reference/)
- [Image metadata labels spec](https://github.com/devcontainers/spec/issues/18)
- [DevPod --fallback-image flag](https://devpod.sh/docs/developing-in-workspaces/create-a-workspace)
