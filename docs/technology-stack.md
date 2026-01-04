# Technology Stack

## Overview

Claude DevContainer is built with a security-first approach, combining Docker containerization, Claude Code plugins, and firewall enforcement to create a safe AI-assisted development environment.

## Core Technologies

### Runtime & Package Management

| Technology | Version | Purpose |
|------------|---------|---------|
| **Node.js** | 22 | Primary runtime for JavaScript/TypeScript development |
| **pnpm** | Latest (via corepack) | Package manager with workspace support |
| **Python** | 3.10+ | BMAD orchestrator CLI and security hooks |

### Containerization

| Technology | Purpose |
|------------|---------|
| **Docker** | Container runtime |
| **Docker Buildx** | Multi-platform builds (amd64, arm64) |
| **GitHub Container Registry (GHCR)** | Image distribution |
| **VS Code Dev Containers** | IDE integration |

### AI Tooling

| Tool | Purpose |
|------|---------|
| **Claude Code** | AI coding assistant with hook integration |
| **Gemini CLI** | Alternative AI assistant with shared hooks |
| **BMAD Framework** | AI workflow orchestration system |

### Security & Networking

| Technology | Purpose |
|------------|---------|
| **iptables/ipset** | Firewall rules with domain allowlisting |
| **dnsmasq** | DNS server for domain resolution |
| **ulogd** | Firewall logging (blocked domain tracking) |

### Shell & Terminal

| Technology | Purpose |
|------------|---------|
| **ZSH** | Default shell |
| **Powerlevel10k** | ZSH theme |
| **tmux** | Terminal multiplexer for persistent sessions |
| **fzf** | Fuzzy finder for command-line |

### Version Control & CI/CD

| Technology | Purpose |
|------------|---------|
| **Git** | Version control |
| **git-delta** | Enhanced git diff viewer |
| **GitHub CLI (gh)** | GitHub operations from CLI |
| **GitHub Actions** | CI/CD pipeline |

---

## Part-Specific Technologies

### image/ (Docker Image - infra)

**Primary Language:** Shell (Bash)

| Component | Technology | Description |
|-----------|------------|-------------|
| Container base | `node:22` | Official Node.js Docker image |
| Configuration | YAML/JSON | Config files for various tools |
| Security hooks | Python 3, Bash | Pre-tool hooks for Claude/Gemini |
| Firewall | iptables, ipset, dnsmasq | Network security layer |
| Logging | ulogd2 | Firewall event logging |

**Key Files:**
- `Dockerfile` - Main container image definition
- `config/allowed-domains.txt` - Domain allowlist
- `hooks/managed-settings.base.json` - Claude Code hook config
- `scripts/init-firewall.sh` - Firewall initialization

---

### packages/git-workflow (Claude Code Plugin - library)

**Primary Language:** Markdown (declarative skills)

| Component | Technology | Description |
|-----------|------------|-------------|
| Skills | Markdown (SKILL.md) | Claude Code skill definitions |
| Commands | Markdown (.md) | Claude Code slash commands |
| Hooks | JSON + Shell | Pre/Post tool hooks |
| Plugin manifest | JSON (plugin.json) | Claude Code plugin configuration |

**Plugin Structure:**
```
git-workflow/
├── plugin.json          # Plugin manifest
├── skills/              # Reusable skill definitions
│   ├── creating-commits/SKILL.md
│   └── pull-request-conventions/SKILL.md
├── commands/            # Slash commands
│   ├── commit.md
│   ├── create-pull-request.md
│   └── ...
└── hooks/               # Enforcement hooks
    └── hooks.json
```

---

### packages/claude-instance (CLI + Plugin - cli)

**Primary Language:** Bash

| Component | Technology | Description |
|-----------|------------|-------------|
| CLI binary | Bash | `claude-instance` command |
| Hooks | JSON + Shell | Instance lifecycle hooks |
| Plugin manifest | JSON (plugin.json) | Claude Code plugin config |

**Features:**
- Multi-instance management
- tmux session integration
- Docker container orchestration
- Metadata tracking (`.claude-metadata.json`)
- OrbStack DNS integration

**Dependencies:**
- jq (JSON processing)
- Docker CLI
- tmux
- devcontainer CLI (optional)

---

### packages/bmad-orchestrator (CLI + Plugin - cli)

**Primary Language:** Python 3.10+

| Component | Technology | Description |
|-----------|------------|-------------|
| CLI binary | Python | `bmad-cli` command |
| Core modules | Python | `bmad/cli.py`, `bmad/executor.py`, `bmad/status.py` |
| Hooks | JSON + Shell | BMAD phase completion hooks |
| Plugin manifest | JSON (plugin.json) | Claude Code plugin config |

**Python Dependencies:**
- Standard library only (no external packages)
- Uses modern type hints (3.10+)
- YAML parsing via custom implementation

**Features:**
- Sprint status tracking
- Story execution automation
- Epic management
- Workflow orchestration

---

## Development Tools

### Editor/IDE

| Tool | Configuration |
|------|--------------|
| VS Code | `.devcontainer/devcontainer.json` |
| Extensions | See devcontainer.json extensions list |

**Key Extensions:**
- `Anthropic.claude-code` - Claude Code
- `google.gemini-cli-vscode-ide-companion` - Gemini CLI
- `ms-playwright.playwright` - Playwright testing
- `eamodio.gitlens` - Git integration
- `dbaeumer.vscode-eslint` - ESLint
- `esbenp.prettier-vscode` - Prettier

### Code Quality

| Tool | Purpose |
|------|---------|
| ESLint | JavaScript/TypeScript linting |
| Prettier | Code formatting |
| markdownlint | Markdown linting |
| Claude plugin validate | Plugin validation |

### Testing

| Tool | Purpose |
|------|---------|
| Playwright | E2E testing framework |
| pnpm test | Test runner (workspace-level) |

---

## Security Architecture

### Hook System

Claude Code and Gemini CLI share a common hook infrastructure:

```
/etc/claude-code/hooks/
├── managed-settings.json      # Hook configuration
├── prevent-main-push.sh       # Block pushes to main/master
├── prevent-no-verify.sh       # Block --no-verify flag
├── prevent-admin-flag.sh      # Block --admin flag
├── prevent-env-leakage.py     # Block sensitive env access
├── prevent-bash-sensitive-args.py  # Block sensitive CLI args
├── prevent-sensitive-files.py # Block access to secrets files
└── lib/
    └── patterns.py            # Shared pattern matching
```

**Hook Types:**
- PreToolUse - Before tool execution
- PostToolUse - After tool execution

**Exit Codes:**
- `0` - Allow command
- `2` - Block command (with feedback)

### Firewall

Domain allowlist firewall using iptables/ipset:

1. DNS queries intercepted by dnsmasq
2. Allowed domains resolved normally
3. Blocked domains logged via ulogd
4. iptables rules enforce allowlist

**Configuration:**
- `/etc/allowed-domains.txt` - Base allowlist (built into image)
- `.devcontainer/allowed-domains.txt` - Project-specific additions

---

## CI/CD Pipeline

### GitHub Actions Workflow

**Trigger Events:**
- Release published
- Push to main (when image/** or packages/** changed)
- Manual workflow dispatch

**Build Process:**
1. Checkout repository
2. Setup QEMU (multi-arch)
3. Setup Docker Buildx
4. Login to GHCR
5. Extract metadata (tags)
6. Build and push multi-platform image

**Platforms:** linux/amd64, linux/arm64

**Tags:**
- `latest` (main branch)
- SHA commit hash
- Semantic version (on release)

---

## Configuration Files

### Root Level

| File | Purpose |
|------|---------|
| `package.json` | Monorepo root config |
| `pnpm-workspace.yaml` | Workspace packages definition |
| `.devcontainer/devcontainer.json` | Dev container settings |
| `.claude/settings.json` | Claude Code project settings |

### Claude Code Configuration

```json
{
  "permissions": {
    "defaultMode": "bypassPermissions"
  },
  "enabledPlugins": {
    "superpowers@superpowers-dev": true,
    "git-workflow@claude-devcontainer": true
  },
  "extraKnownMarketplaces": {
    "superpowers-dev": { "source": "git", "url": "..." },
    "claude-devcontainer": { "source": "directory", "path": "/workspace" }
  }
}
```

---

## Language Distribution

| Language | Usage | Files |
|----------|-------|-------|
| **Bash** | CLI tools, scripts, hooks | ~40% |
| **Python** | BMAD CLI, security hooks | ~30% |
| **Markdown** | Skills, commands, docs | ~20% |
| **JSON/YAML** | Configuration | ~10% |
| **Dockerfile** | Container definition | 1 file |

---

*Generated: 2026-01-03*
*Scan Level: Exhaustive*
