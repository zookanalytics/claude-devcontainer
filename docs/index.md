# Claude DevContainer - Project Documentation

A secure, AI-agent-ready development container base image for Claude Code and Gemini CLI.

**Repository:** [github.com/zookanalytics/claude-devcontainer](https://github.com/zookanalytics/claude-devcontainer)
**Registry:** `ghcr.io/zookanalytics/claude-devcontainer`
**License:** MIT

---

## Quick Links

| Document | Description |
|----------|-------------|
| [Architecture](architecture.md) | System design, component relationships, security model |
| [Development Guide](development-guide.md) | Workflows, conventions, troubleshooting |
| [Technology Stack](technology-stack.md) | Languages, frameworks, tools |
| [Source Tree](source-tree.md) | Complete file inventory with analysis |
| [Project Context](project-context.md) | Essential rules for AI agents |

---

## Project Overview

### What Is This?

Claude DevContainer provides a **sandboxed development environment** with:

- **Security hooks** - Block dangerous operations automatically
- **Domain allowlist firewall** - Control network access
- **Claude Code plugins** - Git workflow, instance management, BMAD automation
- **Multi-instance support** - Run parallel development environments

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Container                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Claude Code / Gemini CLI                           │    │
│  │            ↓                                        │    │
│  │  Security Hooks (prevent dangerous operations)      │    │
│  │            ↓                                        │    │
│  │  Firewall (domain allowlist with iptables)         │    │
│  └─────────────────────────────────────────────────────┘    │
│  Node.js 22 | Python 3.10+ | ZSH + tmux | pnpm             │
└─────────────────────────────────────────────────────────────┘
```

### Project Parts

| Part | Type | Description |
|------|------|-------------|
| **image/** | Infrastructure | Docker container with security layers |
| **git-workflow** | Plugin | Git commands, skills, enforcement |
| **claude-instance** | CLI + Plugin | Multi-instance management |
| **bmad-orchestrator** | CLI + Plugin | BMAD workflow automation |

---

## Generated Documentation

### Core Documentation

| File | Purpose |
|------|---------|
| [architecture.md](architecture.md) | System architecture, integration, security model |
| [development-guide.md](development-guide.md) | Development workflows and conventions |
| [technology-stack.md](technology-stack.md) | Technology inventory and analysis |
| [source-tree.md](source-tree.md) | Complete source file listing |
| [project-context.md](project-context.md) | AI agent context and rules |

### Reference Data

| File | Purpose |
|------|---------|
| [project-structure.md](project-structure.md) | Repository structure overview |
| [project-parts.json](project-parts.json) | Machine-readable part definitions |
| [existing-documentation.md](existing-documentation.md) | Pre-existing docs inventory |
| [project-scan-report.json](project-scan-report.json) | Scan metadata and state |

### Existing Documentation

| File | Description |
|------|-------------|
| [commit_specification.md](commit_specification.md) | Conventional commit guidelines |
| [plans/](plans/) | Planning and research documents |

---

## Getting Started

### For Consumers

1. Add to your project:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/zookanalytics/claude-devcontainer/main/scripts/init-project.sh | bash
   ```

2. Open in VS Code and "Reopen in Container"

3. Start developing with Claude Code or Gemini CLI

### For Contributors

1. Clone the repository
2. Open in VS Code Dev Container
3. Read [Development Guide](development-guide.md)
4. Follow [commit conventions](commit_specification.md)

---

## Security Features

### Defense Layers

1. **Network**: Domain allowlist firewall (iptables + ipset)
2. **Tools**: PreToolUse hooks block dangerous operations
3. **Git**: Protected branches, no bypass flags
4. **Files**: Credential file access blocked

### Security Hooks

| Hook | Protects Against |
|------|-----------------|
| prevent-main-push | Pushes to main/master |
| prevent-no-verify | Bypassing pre-commit hooks |
| prevent-env-leakage | Exposing environment secrets |
| prevent-sensitive-files | Accessing credential files |

---

## Packages

### @zookanalytics/git-workflow

Git workflow automation with skills and commands:
- `/commit` - Atomic commits with conventional format
- `/create-pull-request` - Full PR workflow
- `/orchestrate` - Complete PR lifecycle

### @zookanalytics/claude-instance

Multi-instance management:
- `claude-instance create <name>` - Create instance
- `claude-instance list` - List all instances
- `claude-instance dashboard` - Terminal dashboard

### @zookanalytics/bmad-orchestrator

BMAD workflow automation:
- `bmad-cli status` - Sprint status
- `bmad-cli run-story <id>` - Execute story
- `bmad-cli run-epic <id>` - Execute epic

---

## Related Resources

- [GitHub Repository](https://github.com/zookanalytics/claude-devcontainer)
- [Container Registry](https://ghcr.io/zookanalytics/claude-devcontainer)
- [BMAD Framework Documentation](_bmad/)

---

## Scan Information

| Property | Value |
|----------|-------|
| Scan Date | 2026-01-03 |
| Scan Level | Exhaustive |
| Workflow Version | 1.2.0 |
| Documents Generated | 9 |

---

*Generated by BMAD Document Project Workflow*
