# Source Tree Analysis

## Overview

This document provides a detailed breakdown of all source files in the Claude DevContainer project.

**Total Parts:** 4
**Scan Level:** Exhaustive

---

## image/ (Docker Image - infra)

The container image source files. All files are copied into the Docker image during build.

```
image/
├── Dockerfile                        # Main container image definition
├── config/
│   ├── allowed-domains.txt          # Base domain allowlist for firewall
│   ├── dnsmasq.conf                 # DNS forwarder configuration
│   ├── tmux.conf                    # Terminal multiplexer config
│   └── ulogd.conf                   # Firewall logging config
├── gemini/
│   └── settings.json                # Gemini CLI template settings
├── hooks/
│   ├── managed-settings.base.json   # Claude Code base hook config
│   ├── managed-settings.bmad.json   # BMAD-specific hook additions
│   ├── bmad-phase-complete.sh       # BMAD phase completion hook
│   ├── prevent-main-push.sh         # Block pushes to main/master
│   ├── prevent-no-verify.sh         # Block --no-verify flag
│   ├── prevent-admin-flag.sh        # Block --admin flag bypass
│   ├── prevent-env-leakage.py       # Block sensitive env access
│   ├── prevent-bash-sensitive-args.py  # Block sensitive CLI args
│   ├── prevent-sensitive-files.py   # Block access to secret files
│   └── lib/
│       └── patterns.py              # Shared pattern matching utils
└── scripts/
    ├── post-create.sh               # Container initialization (8-step)
    ├── init-firewall.sh             # iptables/ipset setup
    ├── start-dnsmasq.sh             # Start DNS forwarder
    ├── start-ulogd.sh               # Start firewall logger
    ├── assemble-managed-settings.sh # Merge hook configs
    ├── check-daily-updates.sh       # Package update checker
    ├── fix-node-modules-ownership.sh # Volume permission fix
    ├── update-packages.sh           # Update Claude/Gemini
    ├── derive-project-name.sh       # Extract project name
    ├── find-blocked-domain.sh       # Debug blocked domains
    ├── read-firewall-logs.sh        # View blocked connections
    ├── test-firewall-logging.sh     # Test logging setup
    ├── tmux-session.sh              # tmux session manager
    └── init-project.sh              # Consumer project init
```

### Key Files Explained

| File | Purpose | Lines |
|------|---------|-------|
| `Dockerfile` | Multi-stage container build with Node.js 22, security tools | ~190 |
| `init-firewall.sh` | Domain allowlist firewall using iptables + ipset | ~180 |
| `post-create.sh` | 8-step container initialization sequence | ~85 |
| `prevent-env-leakage.py` | Block env var leakage through command output | ~260 |
| `prevent-main-push.sh` | Guard against pushes to protected branches | ~95 |

---

## packages/git-workflow (Claude Code Plugin - library)

Git workflow skills, commands, and enforcement hooks for Claude Code.

```
packages/git-workflow/
├── package.json                     # npm package config
├── plugin.json                      # Claude Code plugin manifest
├── skills/
│   ├── creating-commits/
│   │   └── SKILL.md                # Commit workflow skill (~116 lines)
│   └── pull-request-conventions/
│       └── SKILL.md                # PR conventions skill
├── commands/
│   ├── commit.md                   # /commit command (delegates to skill)
│   ├── create-pull-request.md     # /create-pull-request command (~7000 chars)
│   ├── merge-pull-request.md      # /merge-pull-request command (~7400 chars)
│   ├── cleanup.md                  # /cleanup command (~10700 chars)
│   ├── orchestrate.md              # /orchestrate full PR workflow (~16600 chars)
│   └── receiving-code-review.md   # /receiving-code-review command (~7000 chars)
└── hooks/
    ├── hooks.json                  # Hook configuration
    └── scripts/
        └── enforce-commit-skill.sh # Enforce skill usage for commits
```

### Skill Details

**creating-commits (SKILL.md)**
- Mandatory 6-step checklist for every commit
- Pre-commit quality checks (`pnpm pre-commit`)
- Atomic commit enforcement
- Conventional commit format validation
- `.claude/.commit-state.json` workflow tracking

**Commands Summary**
| Command | Description |
|---------|-------------|
| `/commit` | Create atomic commits using skill |
| `/create-pull-request` | Full PR creation workflow |
| `/merge-pull-request` | Squash merge with validation |
| `/cleanup` | Sync with remote, clean merged branches |
| `/orchestrate` | Full PR lifecycle automation |
| `/receiving-code-review` | Process review comments |

---

## packages/claude-instance (CLI + Plugin - cli)

Multi-instance management for Claude Code development containers.

```
packages/claude-instance/
├── package.json                     # npm package config
├── plugin.json                      # Claude Code plugin manifest
├── bin/
│   └── claude-instance             # CLI binary (Bash, ~1670 lines)
└── hooks/
    ├── hooks.json                  # Hook configuration
    └── scripts/
        └── session-focus-reminder.sh # Session focus tracking
```

### CLI Commands

| Command | Description |
|---------|-------------|
| `create [--open] <name>` | Create new instance from current repo |
| `list` | List all instances with status |
| `show <name>` | Show detailed instance info |
| `purpose <name> [text]` | Get/set instance purpose |
| `browse <name>` | Open instance URL in browser |
| `open <name>` | Open in dev container |
| `remove [--force] <name>` | Delete instance (safety checks) |
| `menu` | Interactive instance picker |
| `dashboard` | tmux terminal dashboard |
| `attach <name>` | Attach to instance terminal |
| `run <name> <cmd>` | Run command in instance tmux |

### Features

- **Multi-instance management**: Manage parallel Claude dev environments
- **tmux integration**: Persistent terminal sessions
- **Docker orchestration**: Container lifecycle management
- **Metadata tracking**: `.claude-metadata.json` for purpose/status
- **OrbStack DNS**: Automatic `*.claude-dev.local` domains
- **Safety checks**: Uncommitted changes, unpushed branches, stashed work

---

## packages/bmad-orchestrator (CLI + Plugin - cli)

BMAD workflow orchestration for AI-driven development.

```
packages/bmad-orchestrator/
├── package.json                     # npm package config
├── plugin.json                      # Claude Code plugin manifest
├── README.md                        # Package documentation
├── AI-README.md                     # AI assistant context
├── docs/
│   ├── implementation/
│   │   └── tech-spec-bmad-orchestrator.md  # Technical specification
│   └── research/
│       ├── bmad-automation-proposal.md
│       ├── bmad-completion-detection-research.md
│       └── bmad-orchestration-implementation-brief.md
├── scripts/
│   ├── bmad-cli                    # CLI entry point (Python)
│   └── bmad/
│       ├── __init__.py             # Package init
│       ├── cli.py                  # Main CLI module (~58000 chars)
│       ├── executor.py             # Story/epic execution (~17000 chars)
│       └── status.py               # Sprint status reader (~7800 chars)
└── hooks/
    ├── hooks.json                  # Hook configuration
    └── scripts/
        └── bmad-phase-complete.sh  # Phase completion hook
```

### CLI Commands

| Command | Description |
|---------|-------------|
| `status` | Show sprint status summary |
| `status -s` | Show stories grouped by status |
| `next` | Show and execute next action |
| `run-story <id>` | Execute a single story to completion |
| `run-epic <id>` | Execute entire epic to completion |

### Python Modules

**status.py**
- Parse `sprint-status.yaml` (custom YAML parser, stdlib only)
- Compute next action using BMAD priority logic
- Support story filtering (skip already-dispatched)

**executor.py**
- Story execution automation
- Multi-instance dispatch
- Claude Code subprocess management

**cli.py**
- CLI argument parsing
- Command dispatch
- Output formatting

---

## Root Configuration Files

```
/workspace/
├── package.json                     # Monorepo root
├── pnpm-workspace.yaml             # Workspace packages
├── pnpm-lock.yaml                  # Lock file
├── README.md                        # Project README
├── LICENSE                          # MIT License
├── .devcontainer/
│   ├── devcontainer.json           # Dev container config
│   └── ...
├── .claude/
│   ├── settings.json               # Claude Code project settings
│   └── commands/bmad/              # BMAD slash commands (symlinks)
├── .claude-plugin/
│   └── ...                         # Plugin configuration
├── .github/
│   └── workflows/
│       └── publish.yml             # Docker image CI/CD
├── examples/
│   ├── devcontainer.json           # Consumer example
│   └── allowed-domains.txt         # Example domain list
└── docs/
    └── ...                         # Generated documentation
```

---

## File Statistics

### By Language

| Language | Files | Lines (approx) |
|----------|-------|----------------|
| Bash | 20 | ~3,500 |
| Python | 6 | ~2,000 |
| Markdown | 25 | ~4,000 |
| JSON | 15 | ~500 |
| YAML | 5 | ~100 |
| Dockerfile | 1 | ~190 |

### By Part

| Part | Files | Primary Language |
|------|-------|-----------------|
| image | 30 | Bash, Python |
| git-workflow | 12 | Markdown |
| claude-instance | 5 | Bash |
| bmad-orchestrator | 12 | Python |

---

*Generated: 2026-01-03*
*Scan Level: Exhaustive*
