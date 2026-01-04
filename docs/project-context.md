# Project Context for AI Agents

This document provides essential context for AI assistants (Claude, Gemini, etc.) working in this codebase.

## Project Identity

**Name:** Claude DevContainer
**Type:** Monorepo (pnpm workspace)
**Purpose:** Secure AI-agent-ready development container

## Critical Rules

### NEVER Do

1. **Push to main/master** - Use feature branches and PRs
2. **Use --no-verify** - Pre-commit hooks exist for a reason
3. **Access .env files content** - Environment variables may contain secrets
4. **Bypass security hooks** - They protect against common mistakes
5. **Skip pre-commit checks** - Run `pnpm pre-commit` before committing

### ALWAYS Do

1. **Use `/commit` command** - Follows creating-commits skill
2. **Create atomic commits** - One logical change per commit
3. **Follow conventional commits** - `type(scope): description`
4. **Run checks before committing** - `pnpm pre-commit`
5. **Use feature branches** - `feat/`, `fix/`, `docs/` prefixes

## Repository Structure

```
/workspace/
├── image/              # Docker image (infra) - DO NOT modify without understanding
├── packages/           # Claude Code plugins
│   ├── git-workflow/   # Git commands and skills
│   ├── claude-instance/# Instance management CLI
│   └── bmad-orchestrator/ # BMAD workflow automation
├── _bmad/              # BMAD framework - DO NOT modify directly
├── .devcontainer/      # Container configuration
├── .claude/            # Claude Code settings
└── docs/               # Documentation (this folder)
```

## Key Files

| File | Purpose | Modify With Care |
|------|---------|------------------|
| `image/Dockerfile` | Container build | Yes |
| `image/hooks/*.py` | Security hooks | Yes |
| `image/config/allowed-domains.txt` | Firewall allowlist | Yes |
| `packages/*/plugin.json` | Plugin manifests | No |
| `.devcontainer/devcontainer.json` | Dev container config | No |

## Commit Types & Scopes

**Types:** feat, fix, refactor, perf, style, test, docs, build, ops, security, chore

**Scopes:**
- `ai-tools` - Skills, commands, prompts
- `devcontainer` - Container, image, security
- `ci` - GitHub Actions
- `deps` - Dependencies
- `docs` - Documentation
- `tests` - Test files

## Package Patterns

### Adding Skills

```
packages/<name>/skills/<skill-name>/SKILL.md
```

### Adding Commands

```
packages/<name>/commands/<command>.md
```

### Adding Hooks

```
packages/<name>/hooks/scripts/<hook>.sh
packages/<name>/hooks/hooks.json  # Register here
```

## Security Considerations

1. **Firewall is active** - Only allowed domains can be accessed
2. **Hooks intercept tool calls** - Dangerous operations are blocked
3. **Sensitive files protected** - .env, credentials, keys
4. **Git branches protected** - main/master can't be pushed directly

## Development Workflow

1. Create feature branch
2. Make changes
3. Run `pnpm pre-commit`
4. Use `/commit` command
5. Push and create PR

## Common Commands

```bash
# Build Docker image
pnpm build:image

# Run all tests
pnpm test

# Validate plugins
pnpm lint

# Pre-commit checks
pnpm pre-commit
```

## When Unsure

- Read the relevant documentation in `/docs/`
- Check existing patterns in similar files
- Ask the user for clarification
- Don't assume - verify

---

*This file is optimized for AI agent context windows.*
