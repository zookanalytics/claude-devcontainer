# Devcontainer Feature Migration Design

## Overview

Migrate from a monolithic Docker image to a modular devcontainer feature architecture. This enables:
- Publishing `secure-network` as a standalone firewall feature we control
- Publishing `ai-code-hooks` as a standalone feature for AI guardrails
- Keeping a slimmed-down Docker image for dev tooling only
- Central devcontainer config via DevPod's `--devcontainer-path` flag

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  Docker Image (ghcr.io/zookanalytics/claude-devcontainer)
│  ─────────────────────────────────────────────────  │
│  • Developer tooling only                           │
│  • zsh, powerlevel10k, git-delta, tmux, vim        │
│  • gh CLI, uv, pnpm                                │
│  • Playwright system deps                          │
│  • Non-root user setup                             │
└─────────────────────────────────────────────────────┘
                         +
┌─────────────────────────────────────────────────────┐
│  secure-network feature (published by us)          │
│  ─────────────────────────────────────────────────  │
│  • iptables/ipset whitelist firewall               │
│  • Domain-based allowlist configuration            │
│  • Multi-distro support (apt/apk/dnf)              │
│  • Runtime reload without container restart        │
└─────────────────────────────────────────────────────┘
                         +
┌─────────────────────────────────────────────────────┐
│  ai-code-hooks feature (published by us)           │
│  ─────────────────────────────────────────────────  │
│  • Claude Code security hooks                      │
│  • Gemini CLI support (optional)                   │
│  • Prevents credential leaks, unsafe git ops       │
└─────────────────────────────────────────────────────┘
```

## Repository Structure

```
claude-devcontainer/
├── features/
│   ├── secure-network/
│   │   ├── devcontainer-feature.json
│   │   ├── install.sh
│   │   ├── config/
│   │   │   └── allowed-domains.txt      # Base domains
│   │   └── scripts/
│   │       ├── init-firewall.sh
│   │       └── secure-network-reload    # Runtime reload command
│   │
│   └── ai-code-hooks/
│       ├── devcontainer-feature.json
│       ├── install.sh
│       └── hooks/
│           ├── prevent-main-push.sh
│           ├── prevent-no-verify.sh
│           ├── prevent-admin-flag.sh
│           ├── prevent-env-leakage.py
│           ├── prevent-bash-sensitive-args.py
│           ├── prevent-sensitive-files.py
│           └── lib/
│               └── patterns.py
│
├── image/
│   ├── Dockerfile              # Dev tooling only
│   ├── config/
│   │   └── tmux.conf
│   └── scripts/
│       ├── tmux-session.sh
│       ├── post-create.sh      # Simplified - no firewall/hooks init
│       ├── check-daily-updates.sh
│       ├── fix-node-modules-ownership.sh
│       ├── derive-project-name.sh
│       ├── update-packages.sh
│       └── assemble-managed-settings.sh
│
├── devcontainer/
│   ├── devcontainer.json       # Canonical config for DevPod
│   └── Dockerfile              # References image/ tooling
│
└── .github/
    └── workflows/
        ├── publish-features.yml
        └── publish-image.yml
```

## secure-network Feature Specification

### devcontainer-feature.json

```json
{
  "id": "secure-network",
  "version": "1.0.0",
  "name": "Secure Network Firewall",
  "description": "Whitelist-based iptables firewall for development containers",
  "options": {
    "additionalDomains": {
      "type": "string",
      "default": "",
      "description": "Comma-separated list of additional domains to allow"
    },
    "github": {
      "type": "boolean",
      "default": true,
      "description": "Allow GitHub domains and IPs"
    },
    "npm": {
      "type": "boolean",
      "default": true,
      "description": "Allow npm registry"
    },
    "anthropic": {
      "type": "boolean",
      "default": true,
      "description": "Allow Anthropic API"
    },
    "google": {
      "type": "boolean",
      "default": false,
      "description": "Allow Google AI APIs"
    },
    "pypi": {
      "type": "boolean",
      "default": false,
      "description": "Allow PyPI"
    }
  },
  "containerEnv": {
    "SECURE_NETWORK_ENABLED": "true"
  },
  "privileged": false,
  "capAdd": ["NET_ADMIN", "NET_RAW"]
}
```

### install.sh Behavior

1. Detect package manager (apt/apk/dnf/yum)
2. Install packages: `iptables`, `ipset`, `curl`, `jq`
3. Copy scripts to `/usr/local/bin/`
4. Copy base allowed-domains.txt to `/etc/secure-network/`
5. Process feature options → append to allowed-domains.txt
6. Configure sudoers for non-root firewall management
7. Create `secure-network-reload` command for runtime updates

### Runtime Reload

Users can update allowed domains without restarting:

```bash
# Edit project-specific domains
echo "newdomain.com" >> .devcontainer/allowed-domains.txt

# Reload firewall rules
secure-network-reload
```

The reload script:
1. Reads `/etc/secure-network/allowed-domains.txt` (feature defaults)
2. Reads `.devcontainer/allowed-domains.txt` (project-specific, if exists)
3. Rebuilds ipset and iptables rules

### File Paths

| Purpose | Path |
|---------|------|
| Feature config | `/etc/secure-network/allowed-domains.txt` |
| Project config | `.devcontainer/allowed-domains.txt` |
| Init script | `/usr/local/bin/init-firewall.sh` |
| Reload command | `/usr/local/bin/secure-network-reload` |

## ai-code-hooks Feature Specification

### devcontainer-feature.json

```json
{
  "id": "ai-code-hooks",
  "version": "1.0.0",
  "name": "AI Code Security Hooks",
  "description": "Security guardrails for Claude Code and Gemini CLI - prevents credential leaks, unsafe git operations, and sensitive file access",
  "options": {
    "gemini": {
      "type": "boolean",
      "default": false,
      "description": "Also configure hooks for Gemini CLI"
    }
  },
  "installsAfter": ["ghcr.io/devcontainers/features/common-utils"]
}
```

### install.sh Behavior

1. Ensure Python 3 is available (required for `.py` hooks)
2. Create `/etc/ai-code-hooks/` directory
3. Copy all hook scripts to `/etc/ai-code-hooks/`
4. Create `/etc/claude-code/managed-settings.json` pointing to hooks
5. If `gemini=true`: Create `/etc/gemini-cli/settings.json` pointing to hooks
6. Set permissions (755 for scripts, 644 for configs)

### File Paths

| Purpose | Path |
|---------|------|
| Hook scripts | `/etc/ai-code-hooks/*.sh`, `*.py` |
| Hook library | `/etc/ai-code-hooks/lib/patterns.py` |
| Claude Code config | `/etc/claude-code/managed-settings.json` |
| Gemini CLI config | `/etc/gemini-cli/settings.json` |

Both configs reference the shared `/etc/ai-code-hooks/` path.

## Canonical devcontainer.json

```json
{
  "name": "Secure Dev Container",
  "build": {
    "dockerfile": "Dockerfile"
  },
  "features": {
    "ghcr.io/zookanalytics/devcontainer-features/secure-network:1": {
      "github": true,
      "npm": true,
      "anthropic": true,
      "google": true
    },
    "ghcr.io/zookanalytics/devcontainer-features/ai-code-hooks:1": {
      "gemini": true
    }
  },
  "capAdd": ["NET_ADMIN", "NET_RAW"],
  "mounts": [
    "source=claude-config,target=/home/node/.claude,type=volume",
    "source=gemini-config,target=/home/node/.gemini,type=volume"
  ],
  "customizations": {
    "vscode": {
      "extensions": [
        "anthropic.claude-code"
      ]
    }
  }
}
```

## DevPod Workflow

Central config stored at `~/.devcontainer/`:

```bash
# One-time setup
cp -r devcontainer/ ~/.devcontainer/

# Usage with any repo
devpod up github.com/my-org/any-repo --devcontainer-path ~/.devcontainer/devcontainer.json

# Optional alias
alias devpod-secure='devpod up --devcontainer-path ~/.devcontainer/devcontainer.json'
```

Updates: Change `~/.devcontainer/` once, all new workspaces get the update.

## Migration: Files to Move

### To features/secure-network/

From `image/`:
- `scripts/init-firewall.sh` → `scripts/init-firewall.sh`
- `config/allowed-domains.txt` → `config/allowed-domains.txt`

New files:
- `devcontainer-feature.json`
- `install.sh`
- `scripts/secure-network-reload`

### To features/ai-code-hooks/

From `image/hooks/`:
- `prevent-main-push.sh`
- `prevent-no-verify.sh`
- `prevent-admin-flag.sh`
- `prevent-env-leakage.py`
- `prevent-bash-sensitive-args.py`
- `prevent-sensitive-files.py`
- `lib/patterns.py`
- `managed-settings.base.json` → template for install.sh

New files:
- `devcontainer-feature.json`
- `install.sh`

## Migration: Files to Delete from image/

Firewall-related (moved to secure-network feature):
- `image/scripts/init-firewall.sh`
- `image/scripts/start-dnsmasq.sh` (not needed - no DNS logging)
- `image/scripts/start-ulogd.sh` (not needed - no firewall logging)
- `image/scripts/read-firewall-logs.sh`
- `image/scripts/test-firewall-logging.sh`
- `image/scripts/find-blocked-domain.sh`
- `image/config/dnsmasq.conf`
- `image/config/ulogd.conf`
- `image/config/allowed-domains.txt`

Hooks (moved to ai-code-hooks feature):
- `image/hooks/` (entire directory)
- `image/gemini/` (entire directory)

## Migration: Files to Update

### image/Dockerfile

Remove:
- Firewall packages: `iptables`, `ipset`, `iproute2`, `dnsutils`, `dnsmasq`, `aggregate`, `ulogd2`
- Hook copying: `COPY image/hooks/...`
- Gemini config copying: `COPY image/gemini/...`
- Firewall-related sudoers entries
- Log file creation for dnsmasq/ulogd

### image/scripts/post-create.sh

Remove:
- Firewall initialization steps
- dnsmasq/ulogd startup
- Hook assembly (handled by feature)

Keep:
- Package update checks
- Node modules ownership fix
- Project-specific post-create script execution

### .devcontainer/devcontainer.json

- Replace image-baked security with features
- Add feature declarations

### .github/workflows/

- Add `publish-features.yml` for feature releases

## What Stays the Same

- Dev tooling in Docker image (zsh, powerlevel10k, delta, tmux, vim, gh, uv, pnpm)
- All hook logic (6 Python/bash scripts) - just moved to feature
- All firewall logic - just moved to feature
- BMAD-related hooks and settings assembly
- CLI tools (claude-instance, bmad-cli)

## Multi-Distro Support (secure-network feature)

The `install.sh` must detect and handle multiple package managers:

```bash
install_packages() {
  if command -v apt-get &> /dev/null; then
    apt-get update && apt-get install -y iptables ipset curl jq
  elif command -v apk &> /dev/null; then
    apk add --no-cache iptables ipset curl jq
  elif command -v dnf &> /dev/null; then
    dnf install -y iptables ipset curl jq
  elif command -v yum &> /dev/null; then
    yum install -y iptables ipset curl jq
  else
    echo "Unsupported package manager" >&2
    exit 1
  fi
}
```

Package name mapping (mostly consistent):

| Package | Debian/Ubuntu | Alpine | RHEL/Fedora |
|---------|---------------|--------|-------------|
| iptables | `iptables` | `iptables` | `iptables` |
| ipset | `ipset` | `ipset` | `ipset` |
| curl | `curl` | `curl` | `curl` |
| jq | `jq` | `jq` | `jq` |
