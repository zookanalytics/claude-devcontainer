# Development Guide

## Overview

This guide covers development workflows, conventions, and operational procedures for the Claude DevContainer project.

---

## Getting Started

### Prerequisites

- Docker Desktop or compatible container runtime
- VS Code with Dev Containers extension
- Git

### Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/zookanalytics/claude-devcontainer.git
   cd claude-devcontainer
   ```

2. Open in VS Code and select "Reopen in Container"

3. The container will:
   - Install Claude Code and Gemini CLI
   - Initialize firewall with domain allowlist
   - Set up security hooks
   - Run project-specific setup (if configured)

---

## Repository Structure

```
/workspace/
├── image/              # Docker image source (infra)
├── packages/           # Distributable packages
│   ├── git-workflow/   # Git workflow plugin
│   ├── claude-instance/# Instance management
│   └── bmad-orchestrator/ # BMAD automation
├── _bmad/              # BMAD framework (installed)
├── .devcontainer/      # Dev container config
├── .claude/            # Claude Code settings
└── docs/               # Documentation
```

---

## Development Workflows

### Making Changes

1. **Create feature branch:**
   ```bash
   git checkout -b feat/my-feature
   ```

2. **Make changes** following the code style guidelines

3. **Run pre-commit checks:**
   ```bash
   pnpm pre-commit
   ```

4. **Create atomic commits** using the `/commit` command or skill

5. **Push and create PR:**
   ```bash
   git push -u origin feat/my-feature
   # Use /create-pull-request command
   ```

### Commit Conventions

This project uses [Conventional Commits](https://www.conventionalcommits.org/). See [commit_specification.md](commit_specification.md) for full details.

**Format:** `type(scope): description`

**Types:**
| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Code restructure (no behavior change) |
| `perf` | Performance improvement |
| `style` | Code style (formatting, whitespace) |
| `test` | Add or correct tests |
| `docs` | Documentation only |
| `build` | Build system, CI/CD, dependencies |
| `ops` | Operational (infra, deployment) |
| `security` | Security fixes |
| `chore` | Misc (dev environment, .gitignore) |

**Scopes:**
| Scope | Files/Directories |
|-------|------------------|
| `ai-tools` | `.claude/`, `.gemini/`, skills, commands |
| `app` | `src/app/` (if applicable) |
| `ci` | `.github/workflows/` |
| `deps` | `package.json`, `pnpm-lock.yaml` |
| `devcontainer` | `.devcontainer/`, `image/` |
| `docs` | `docs/`, `*.md` |
| `tests` | `**/__tests__/`, `*.test.ts` |

**Examples:**
```
feat(devcontainer): add DNS logging support
fix(ai-tools): correct commit skill checklist order
docs: update README with new features
build(deps): upgrade Node.js to v22
```

---

## Building the Docker Image

### Local Build

```bash
pnpm build:image
# or
docker build -f image/Dockerfile -t claude-devcontainer .
```

### Multi-Platform Build

The CI/CD pipeline builds for both amd64 and arm64:

```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -f image/Dockerfile \
  -t claude-devcontainer:local \
  .
```

### Testing Image Changes

1. Make changes to `image/` files
2. Rebuild locally: `pnpm build:image`
3. Update `.devcontainer/devcontainer.json` to use local image
4. Rebuild container: "Dev Containers: Rebuild Container"

---

## Package Development

### Working on packages/

Each package under `packages/` is a Claude Code plugin:

```bash
# Validate plugin manifest
pnpm -r lint

# Test package
pnpm -r test
```

### Plugin Structure

```
packages/<name>/
├── package.json      # npm package config
├── plugin.json       # Claude Code plugin manifest
├── skills/           # Reusable skills (optional)
├── commands/         # Slash commands (optional)
└── hooks/            # Pre/Post tool hooks (optional)
```

### Creating a New Command

1. Create `commands/<name>.md`:
   ```markdown
   ---
   description: Brief description
   ---

   # Command Name

   Instructions for Claude...
   ```

2. Reference in `plugin.json`:
   ```json
   {
     "commands": "./commands/"
   }
   ```

### Creating a New Skill

1. Create `skills/<name>/SKILL.md`:
   ```markdown
   ---
   name: skill-name
   description: When to use this skill
   ---

   # Skill Name

   Detailed instructions...
   ```

2. Reference in `plugin.json`:
   ```json
   {
     "skills": "./skills/"
   }
   ```

---

## Security Hooks

### Available Hooks

The container includes security hooks that block dangerous operations:

| Hook | Blocks |
|------|--------|
| `prevent-main-push.sh` | `git push` to main/master |
| `prevent-no-verify.sh` | `--no-verify` flag |
| `prevent-admin-flag.sh` | `--admin` bypass flag |
| `prevent-env-leakage.py` | Sensitive env var access |
| `prevent-bash-sensitive-args.py` | Sensitive CLI arguments |
| `prevent-sensitive-files.py` | Access to .env, credentials |

### Hook Configuration

Hooks are configured in `/etc/claude-code/managed-settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {"type": "command", "command": "/etc/claude-code/hooks/prevent-main-push.sh"}
        ]
      }
    ]
  }
}
```

### Extending Hooks

Project-specific hooks can be added via:
1. Add hook script to `image/hooks/`
2. Reference in `managed-settings.base.json` or `.bmad.json`
3. Run `assemble-managed-settings.sh` to merge

---

## Firewall Configuration

### Domain Allowlist

The container uses iptables to enforce a domain allowlist.

**Base domains** (built into image): `/etc/allowed-domains.txt`
**Project domains** (optional): `.devcontainer/allowed-domains.txt`

### Adding Allowed Domains

1. Create/edit `.devcontainer/allowed-domains.txt`:
   ```
   # Project-specific domains
   api.your-service.com
   cdn.your-app.com
   ```

2. Restart container to apply changes

### Debugging Blocked Connections

```bash
# View blocked connection logs
sudo /usr/local/bin/read-firewall-logs.sh

# Find which domain was blocked
sudo /usr/local/bin/find-blocked-domain.sh <ip-address>
```

---

## CI/CD Pipeline

### Automatic Builds

The Docker image is built and pushed automatically on:
- Release published
- Push to main (when `image/` or `packages/` changed)
- Manual workflow dispatch

### Image Tags

| Tag | Description |
|-----|-------------|
| `latest` | Latest main branch build |
| `<sha>` | Specific commit hash |
| `<version>` | Semantic version (from release) |

### Registry

Images are published to:
```
ghcr.io/zookanalytics/claude-devcontainer
```

---

## Testing

### Running Tests

```bash
# All packages
pnpm test

# Specific package
pnpm -r --filter @zookanalytics/git-workflow test
```

### Linting

```bash
# All packages
pnpm lint

# Validates Claude plugins
claude plugin validate .
```

### Pre-commit Checks

```bash
pnpm pre-commit
# Runs: lint + typecheck on all packages
```

---

## Multi-Instance Development

### Using claude-instance

```bash
# Create new instance
claude-instance create agent-1

# List instances
claude-instance list

# Set purpose
claude-instance purpose agent-1 "Feature development"

# Open in container
claude-instance open agent-1
```

### Dashboard Mode

```bash
# Interactive terminal dashboard
claude-instance dashboard

# Navigate: Ctrl-b w (select window), Ctrl-b d (detach)
```

---

## BMAD Integration

### Sprint Status

```bash
# View sprint status
./packages/bmad-orchestrator/scripts/bmad-cli status

# Stories by status
./packages/bmad-orchestrator/scripts/bmad-cli status -s
```

### Automated Story Execution

```bash
# Execute next action
./packages/bmad-orchestrator/scripts/bmad-cli next

# Run specific story
./packages/bmad-orchestrator/scripts/bmad-cli run-story 1-2-auth
```

---

## Troubleshooting

### Container Won't Start

1. Check Docker is running
2. Ensure NET_ADMIN capability is enabled
3. Check for port conflicts

### Firewall Blocking Required Domain

1. Check logs: `sudo /usr/local/bin/read-firewall-logs.sh`
2. Add domain to `.devcontainer/allowed-domains.txt`
3. Rebuild container

### Claude Code Not Working

1. Verify installation: `which claude`
2. Check version: `claude --version`
3. Restart terminal or container

### Hook Blocking Command

Hooks provide feedback when blocking. Check:
1. Read the error message
2. Verify you're following proper workflow
3. If intentional bypass needed, ask user explicitly

---

*Generated: 2026-01-03*
*Scan Level: Exhaustive*
