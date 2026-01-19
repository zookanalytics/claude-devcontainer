# Devcontainer Feature Migration Design

## Overview

Migrate from a monolithic Docker image to a modular devcontainer feature architecture. This enables:
- Using the existing `w3cj/firewall` feature instead of maintaining our own firewall code
- Publishing `ai-code-hooks` as a standalone feature others can use
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
│  w3cj/firewall feature (external)                  │
│  ─────────────────────────────────────────────────  │
│  • iptables whitelist                              │
│  • Pre-configured service options                  │
│  • Verbose blocked connection notifications        │
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
│       ├── post-create.sh      # Simplified
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
        ├── publish-feature.yml
        └── publish-image.yml
```

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
    "ghcr.io/w3cj/devcontainer-features/firewall:1": {
      "verbose": true,
      "githubDomains": true,
      "githubIps": true,
      "npmRegistry": true,
      "anthropicApi": true,
      "googleAiApi": true
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

## Migration: Files to Delete

Firewall-related (replaced by w3cj/firewall):
- `image/scripts/init-firewall.sh`
- `image/scripts/start-dnsmasq.sh`
- `image/scripts/start-ulogd.sh`
- `image/scripts/read-firewall-logs.sh`
- `image/scripts/test-firewall-logging.sh`
- `image/scripts/find-blocked-domain.sh`
- `image/config/dnsmasq.conf`
- `image/config/ulogd.conf`
- `image/config/allowed-domains.txt`

Firewall packages to remove from Dockerfile:
- `iptables`
- `ipset`
- `iproute2`
- `dnsutils`
- `dnsmasq`
- `aggregate`
- `ulogd2`

## Migration: Files to Move

Hooks move from `image/hooks/` to `features/ai-code-hooks/hooks/`:
- `prevent-main-push.sh`
- `prevent-no-verify.sh`
- `prevent-admin-flag.sh`
- `prevent-env-leakage.py`
- `prevent-bash-sensitive-args.py`
- `prevent-sensitive-files.py`
- `lib/patterns.py`
- `managed-settings.base.json` → template for feature's install.sh

## Migration: Files to Update

- `image/Dockerfile` - Remove firewall packages, remove hook copying
- `image/scripts/post-create.sh` - Remove firewall init steps
- `.devcontainer/devcontainer.json` - Use features instead of image-baked security
- `.github/workflows/` - Add feature publishing workflow

## What Stays the Same

- Dev tooling in Docker image (zsh, powerlevel10k, delta, tmux, vim, gh, uv, pnpm)
- All hook logic (6 Python/bash scripts)
- BMAD-related hooks and settings assembly
- CLI tools (claude-instance, bmad-cli)
