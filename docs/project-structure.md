# Project Structure

## Overview

**Project Name:** Claude DevContainer
**Repository Type:** Monorepo (pnpm workspace)
**Primary Purpose:** Secure, AI-agent-ready development container base image for Claude Code and Gemini CLI

## Repository Structure

This is a **monorepo** containing a Docker base image and multiple Claude Code plugins distributed as npm packages.

## Project Parts

### 1. image (Infrastructure)

**Path:** `/image/`
**Type:** `infra`
**Description:** Docker container image with security hooks, firewall, and development tooling

**Key Components:**
- `Dockerfile` - Main container image definition
- `config/` - Configuration files (allowed-domains.txt, dnsmasq.conf, tmux.conf, ulogd.conf)
- `hooks/` - Security hooks for Claude Code and Gemini CLI (Python and Bash)
- `scripts/` - Container lifecycle and utility scripts
- `gemini/` - Gemini CLI configuration

**Features:**
- Node.js 22 with pnpm
- Domain allowlist firewall (iptables/ipset)
- Security hooks preventing common mistakes
- ZSH with Powerlevel10k theme
- tmux for persistent sessions
- Pre-installed: Claude Code, Gemini CLI, GitHub CLI

---

### 2. git-workflow (Library/Plugin)

**Path:** `/packages/git-workflow/`
**Type:** `library`
**npm Package:** `@zookanalytics/git-workflow`
**Description:** Claude Code plugin for git workflow skills and enforcement hooks

**Key Components:**
- `skills/` - Git workflow skills (commit, PR creation, etc.)
- `commands/` - CLI commands
- `hooks/` - Enforcement hooks
- `plugin.json` - Claude Code plugin manifest

---

### 3. claude-instance (CLI/Plugin)

**Path:** `/packages/claude-instance/`
**Type:** `cli`
**npm Package:** `@zookanalytics/claude-instance`
**Description:** Multi-instance management for Claude Code with session purpose tracking

**Key Components:**
- `bin/claude-instance` - CLI executable
- `hooks/` - Instance management hooks
- `plugin.json` - Claude Code plugin manifest

---

### 4. bmad-orchestrator (CLI/Plugin)

**Path:** `/packages/bmad-orchestrator/`
**Type:** `cli`
**npm Package:** `@zookanalytics/bmad-orchestrator`
**Description:** BMAD workflow orchestration for AI-driven development

**Key Components:**
- `scripts/bmad-cli` - CLI executable
- `hooks/` - BMAD orchestration hooks
- `docs/` - BMAD integration documentation
- `plugin.json` - Claude Code plugin manifest

---

## Additional Directories

| Directory | Purpose |
|-----------|---------|
| `_bmad/` | Installed BMAD framework (AI workflow orchestration system) |
| `.devcontainer/` | VS Code Dev Container configuration for this repo |
| `.claude/` | Claude Code project-level configuration |
| `.claude-plugin/` | Claude Code plugin configuration |
| `.github/` | GitHub Actions workflows |
| `examples/` | Example configurations for consumers |
| `docs/` | Project documentation |

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Image (image/)                     │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Node.js 22 + pnpm + ZSH + tmux                         ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  ││
│  │  │ Claude Code │  │ Gemini CLI  │  │   GitHub CLI    │  ││
│  │  └──────┬──────┘  └──────┬──────┘  └─────────────────┘  ││
│  │         │                │                               ││
│  │  ┌──────▼────────────────▼──────┐                       ││
│  │  │     Security Hooks (shared)   │                       ││
│  │  │  - prevent-main-push.sh       │                       ││
│  │  │  - prevent-no-verify.sh       │                       ││
│  │  │  - prevent-env-leakage.py     │                       ││
│  │  │  - prevent-sensitive-files.py │                       ││
│  │  └───────────────────────────────┘                       ││
│  │                                                          ││
│  │  ┌──────────────────────────────────────────────────┐   ││
│  │  │  Embedded CLIs from packages/                     │   ││
│  │  │  - /usr/local/bin/claude-instance                 │   ││
│  │  │  - /usr/local/bin/bmad-cli                        │   ││
│  │  └──────────────────────────────────────────────────┘   ││
│  │                                                          ││
│  │  ┌──────────────────────────────────────────────────┐   ││
│  │  │  Firewall (iptables + ipset + dnsmasq)           │   ││
│  │  │  - Domain allowlist enforcement                   │   ││
│  │  │  - Blocked domain logging (ulogd)                 │   ││
│  │  └──────────────────────────────────────────────────┘   ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│               npm Packages (packages/)                       │
│  ┌─────────────────┐ ┌─────────────────┐ ┌────────────────┐ │
│  │  git-workflow   │ │ claude-instance │ │bmad-orchestrator││
│  │  (plugin)       │ │ (plugin + CLI)  │ │ (plugin + CLI) │ │
│  └─────────────────┘ └─────────────────┘ └────────────────┘ │
│           │                   │                   │          │
│           └───────────────────┼───────────────────┘          │
│                               ▼                              │
│                     Published to npm                         │
│                  @zookanalytics/* scope                      │
└─────────────────────────────────────────────────────────────┘
```
