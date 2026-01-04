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
│   ├── bmad-orchestrator/ # BMAD workflow automation
│   └── bmad-dashboard/ # TUI dashboard for DevPod orchestration
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
- `bmad-dashboard` - TUI dashboard package
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

## BMAD Dashboard Package

**Location:** `packages/bmad-dashboard/`
**Type:** CLI + TUI Developer Tool
**Stack:** Ink (React for CLIs) + Commander + TypeScript

### Technology Versions

| Technology | Version | Notes |
|------------|---------|-------|
| Ink | 6.x | TUI framework (React for CLIs) |
| Commander | 14.x | CLI argument parsing |
| React | 19.x | Component framework (required by Ink 6) |
| TypeScript | 5.x | Strict mode required |

### File Naming Rules

| Type | Pattern | Example |
|------|---------|---------|
| React Components | PascalCase matching export | `WorkerList.tsx` |
| Utilities/Lib | lowercase | `discovery.ts` |
| Test files | `.test.ts` suffix, co-located | `discovery.test.ts` |

### TypeScript Naming Rules

- **NO prefixes** on interfaces: `DevPod`, not `IDevPod`
- **NO prefixes** on types: `Status`, not `TStatus`
- **Constants**: `SCREAMING_SNAKE_CASE`

### Component Patterns

```typescript
// CORRECT: Function declaration, not arrow
function WorkerList({ devpods }: WorkerListProps) {
  const [selected, setSelected] = useState(0);
  return <Box>...</Box>;
}

// WRONG: Arrow function for top-level components
const WorkerList: FC<Props> = ({ devpods }) => { ... }
```

### JSON Output Format

All `--json` CLI output MUST use this wrapper:

```json
{
  "version": "1",
  "devpods": [...],
  "errors": [...]
}
```

### Error Message Format

All user-facing errors MUST include suggestions:

```
✗ devpod-3: Connection timed out after 5s
  Suggestion: Check if DevPod is running with `devpod list`
```

### Status Indicators

| Symbol | Meaning |
|--------|---------|
| `✓` | Success/Complete |
| `●` | In progress/Running |
| `○` | Pending/Idle |
| `✗` | Error/Failed |
| `⚠` | Warning/Needs attention |

### Anti-Patterns to Avoid

| Anti-Pattern | Correct Pattern |
|--------------|-----------------|
| `interface IDevPod` | `interface DevPod` |
| `workerList.tsx` | `WorkerList.tsx` |
| `__tests__/discovery.test.ts` | `lib/discovery.test.ts` |
| `Error: something failed` | `✗ context: message\n  Suggestion: ...` |
| Arrow function components | Function declaration components |
| Class components | Function components with hooks |

### Error Handling Pattern

Use `Promise.allSettled` for graceful degradation:

```typescript
const results = await Promise.allSettled(
  devpods.map(pod => readDevPodState(pod))
);
// Both fulfilled and rejected results passed to UI
```

---

*This file is optimized for AI agent context windows.*
*Updated: 2026-01-04 with BMAD Dashboard patterns*
