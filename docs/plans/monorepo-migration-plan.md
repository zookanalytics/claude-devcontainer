# Dev Infrastructure Monorepo Migration Plan

**Created:** 2026-01-01
**Status:** Draft - Pending Review

## Overview

Consolidate development infrastructure tools into a monorepo to enable:

- Reuse across multiple repositories
- Updates that roll out without commits to consuming repos
- A robust environment for improving dev tools

## Current State

| Component | Location | Description |
|-----------|----------|-------------|
| **claude-devcontainer** | `_repos/claude-devcontainer/` | Base Docker image, firewall, security hooks |
| **claude-instance** | `claude-devcontainer/scripts/claude-instance` | Multi-instance management (~500 lines bash) |
| **bmad-orchestrator** | `_repos/bmad_orchestrator/` | BMAD workflow orchestration (Python CLI + hooks) |
| **project hooks** | `claude-devcontainer/.claude/hooks/` | Commit enforcement, session focus, etc. |

## Hook Categories

Hooks fall into distinct categories based on their coupling:

| Category | Examples | Coupling | Distribution |
|----------|----------|----------|--------------|
| **Image security hooks** | `prevent-main-push.sh`, `prevent-env-leakage.py` | Standalone - always active | Baked into Docker image |
| **Skill-coupled hooks** | `enforce-commit-skill.sh` ↔ `git:commit` skill | Must be installed together as a bundle | Claude Code plugin |
| **Tool-coupled hooks** | `bmad-phase-complete.sh` ↔ `bmad-cli` | Hook enables tool functionality | Bundled with the tool |

**Key insight:** A skill-coupled hook without its skill is useless (or worse, blocks work). These must be distributed as bundles.

### Current Skill-Hook Bundles in claude-devcontainer

| Skill | Coupled Hook | Purpose |
|-------|--------------|---------|
| `git:commit` | `enforce-commit-skill.sh` | Blocks commits unless skill workflow followed |
| `creating-commits` | (same as above) | Skill that the hook enforces |
| BMAD workflows | `bmad-phase-complete.sh` | Detects phase completion for orchestrator |

## Proposed Structure

```
claude-devcontainer/
├── .github/
│   └── workflows/
│       ├── build-image.yml            # Build & push Docker image
│       ├── test.yml                   # Test all packages
│       └── release.yml                # Version & publish packages
│
├── image/                             # Docker image (currently at root level)
│   ├── Dockerfile
│   ├── config/
│   │   ├── allowed-domains.txt
│   │   ├── dnsmasq.conf
│   │   ├── tmux.conf
│   │   └── ulogd.conf
│   ├── scripts/                       # Image-level scripts
│   │   ├── post-create.sh
│   │   ├── init-firewall.sh
│   │   ├── start-dnsmasq.sh
│   │   └── ...
│   └── hooks/                         # IMAGE SECURITY HOOKS (standalone)
│       ├── prevent-main-push.sh
│       ├── prevent-env-leakage.py
│       ├── prevent-no-verify.sh
│       ├── prevent-admin-flag.sh
│       ├── prevent-sensitive-files.py
│       ├── prevent-bash-sensitive-args.py
│       ├── lib/
│       │   └── patterns.py
│       └── managed-settings.json      # Registers security hooks
│
├── packages/
│   ├── claude-instance/               # Standalone tool (no coupled hooks)
│   │   ├── package.json
│   │   ├── bin/
│   │   │   └── claude-instance
│   │   └── lib/
│   │       └── ...
│   │
│   ├── bmad-orchestrator/             # TOOL + COUPLED HOOK BUNDLE
│   │   ├── package.json               # npm wrapper
│   │   ├── plugin.json                # Claude Code plugin manifest
│   │   ├── bin/
│   │   │   └── bmad-cli               # CLI tool
│   │   ├── src/
│   │   │   └── bmad/
│   │   │       ├── __init__.py
│   │   │       ├── cli.py
│   │   │       ├── status.py
│   │   │       └── executor.py
│   │   ├── hooks/                     # Tool-coupled hooks
│   │   │   └── bmad-phase-complete.sh
│   │   └── skills/                    # Optional BMAD-specific skills
│   │       └── ...
│   │
│   └── git-workflow/                  # SKILL + COUPLED HOOK BUNDLE
│       ├── package.json
│       ├── plugin.json                # Claude Code plugin manifest
│       ├── skills/
│       │   ├── creating-commits/
│       │   │   └── SKILL.md
│       │   ├── git:commit/
│       │   │   └── SKILL.md
│       │   ├── git:create-pull-request/
│       │   │   └── SKILL.md
│       │   └── ...
│       └── hooks/                     # Skill-coupled hooks
│           └── enforce-commit-skill.sh
│
├── examples/
│   ├── devcontainer.json
│   └── consumer-project/
│
├── docs/
│   ├── plans/
│   └── ...
│
├── package.json                       # pnpm workspace root
├── pnpm-workspace.yaml
└── README.md
```

### Bundle Principles

1. **Image security hooks** → Always present, no skills needed, baked into image
2. **Skill bundles** → Skill + its enforcement hook = one Claude Code plugin
3. **Tool bundles** → CLI tool + its enabling hook = one package with plugin.json
4. **Standalone tools** → No hooks needed (e.g., `claude-instance`)

## Package Distribution Strategy

| Package | Type | Distribution | Install/Use |
|---------|------|--------------|-------------|
| **Docker image** | Base environment | GitHub Container Registry | `image: ghcr.io/zookanalytics/claude-devcontainer:latest` |
| **Security hooks** | Image hooks | Baked into image | Automatic via `managed-settings.json` |
| **claude-instance** | Standalone tool | npm + image PATH | `npx @zookanalytics/claude-instance create foo` |
| **git-workflow** | Skill+hook bundle | Claude Code plugin | `enabledPlugins: {"git-workflow@...": true}` |
| **bmad-orchestrator** | Tool+hook bundle | npm + Claude Code plugin | `npx @zookanalytics/bmad-cli status` + plugin for hook |

## Update Flow (No Commits Required)

```
┌─────────────────────────────────────────────────────────────────┐
│  claude-devcontainer repo                                        │
│                                                                  │
│  Push to main → GitHub Actions                                   │
│       │                                                          │
│       ├── Build Docker image → Push to ghcr.io                  │
│       ├── Publish npm packages → npm registry                    │
│       └── Update plugin marketplace → GitHub releases            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  claude-devcontainer (consumer repo)                                     │
│                                                                  │
│  .devcontainer/devcontainer.json:                               │
│    "image": "ghcr.io/zookanalytics/claude-devcontainer:latest"  │
│                                                                  │
│  On "Rebuild Container":                                         │
│    → Pulls latest image (includes claude-instance, bmad-cli)    │
│    → Hooks auto-applied via managed-settings                    │
│    → No commits needed in claude-devcontainer!                          │
└─────────────────────────────────────────────────────────────────┘
```

## Migration Phases

### Phase 1: Restructure claude-devcontainer (image + security hooks)

1. Create `image/` directory
2. Move Dockerfile and related files into `image/`
3. Move `config/` into `image/config/`
4. Move `scripts/` into `image/scripts/`
5. Move security hooks into `image/hooks/` (these stay with the image)
6. Create `packages/` directory
7. Set up pnpm workspace root (`pnpm-workspace.yaml`, `package.json`)

**Files to move:**
- `Dockerfile` → `image/Dockerfile`
- `config/*` → `image/config/*`
- `scripts/*` → `image/scripts/*`
- `claude/hooks/*` → `image/hooks/*` (security hooks stay with image)
- `claude/managed-settings.json` → `image/hooks/managed-settings.json`

### Phase 2: Migrate claude-instance (standalone tool)

1. Create `packages/claude-instance/` structure
2. Copy `claude-devcontainer/scripts/claude-instance` to `packages/claude-instance/bin/`
3. Create `package.json` with bin entry
4. Test standalone execution with `npx`
5. Update Dockerfile to install from packages

**package.json example:**
```json
{
  "name": "@zookanalytics/claude-instance",
  "version": "0.1.0",
  "bin": {
    "claude-instance": "./bin/claude-instance"
  },
  "files": ["bin/", "lib/"]
}
```

### Phase 3: Create git-workflow package (skill + hook bundle)

1. Create `packages/git-workflow/` structure
2. Move git-related skills from claude-devcontainer:
   - `.claude/skills/creating-commits/`
   - `.claude/skills/git:commit/`
   - `.claude/skills/git:create-pull-request/`
   - `.claude/skills/pull-request-conventions/`
   - etc.
3. Move `enforce-commit-skill.sh` hook (coupled to these skills)
4. Create `plugin.json` that registers both skills and hooks
5. Test as Claude Code plugin

**plugin.json example:**
```json
{
  "name": "git-workflow",
  "version": "0.1.0",
  "description": "Git workflow skills with enforcement hooks",
  "skills": "skills/",
  "hooks": "hooks/hooks.json"
}
```

### Phase 4: Migrate bmad-orchestrator (tool + hook bundle)

1. Move `_repos/bmad_orchestrator/` contents to `packages/bmad-orchestrator/`
2. Keep `bmad-phase-complete.sh` hook WITH the tool (not separate)
3. Create npm `package.json` wrapper for Python CLI
4. Create `plugin.json` for the coupled hook
5. Delete standalone `_repos/bmad_orchestrator/` repo

**Structure:**
```
packages/bmad-orchestrator/
├── package.json          # npm package
├── plugin.json           # Claude Code plugin (for hook)
├── bin/bmad-cli
├── src/bmad/...
├── hooks/
│   ├── hooks.json
│   └── scripts/
│       └── bmad-phase-complete.sh
└── skills/               # Optional BMAD skills
```

### Phase 5: Update Docker image

1. Update `image/Dockerfile` to:
   - Copy packages from monorepo
   - Install `claude-instance` to PATH
   - Install `bmad-cli` to PATH
   - Apply image-level `managed-settings.json` (security hooks only)
2. Packages with plugins (`git-workflow`, `bmad-orchestrator`) are NOT baked into image
   - They are installed as Claude Code plugins by consuming projects
3. Test image build locally
4. Update GitHub Actions for image publishing

### Phase 6: Update claude-devcontainer (consumer)

1. Remove `scripts/claude-instance` (now provided by image)
2. Remove git-related skills (now from `git-workflow` plugin)
3. Remove `enforce-commit-skill.sh` hook (now from `git-workflow` plugin)
4. Remove security hooks (now from image `managed-settings`)
5. Add plugins to `.claude/settings.json`:
   ```json
   {
     "enabledPlugins": {
       "git-workflow@claude-devcontainer": true,
       "bmad-orchestrator@claude-devcontainer": true
     }
   }
   ```
6. Keep project-specific skills that don't belong in shared packages
7. Test full workflow

## Configuration Files

### pnpm-workspace.yaml

```yaml
packages:
  - 'packages/*'
```

### Root package.json

```json
{
  "name": "claude-devcontainer",
  "private": true,
  "scripts": {
    "build:image": "docker build -t claude-devcontainer ./image",
    "test": "pnpm -r test",
    "lint": "pnpm -r lint",
    "publish:packages": "pnpm -r publish --access public"
  },
  "devDependencies": {
    "turbo": "^2.0.0"
  }
}
```

## Decisions Made

1. **Hook organization:** Hooks are organized by coupling:
   - Security hooks → baked into image
   - Skill-coupled hooks → bundled with their skills as plugins
   - Tool-coupled hooks → bundled with their tools as plugins

2. **Repo naming:** Keep `claude-devcontainer` (no rename)

3. **npm scope:** `@zookanalytics`

4. **Versioning strategy:** SemVer with independent versioning per package

5. **Image tagging:** Start with `latest` only, add version tags in future

## Open Questions

1. **Python distribution for bmad-cli:** (requires separate conversation)
   - npm wrapper only (requires Python 3.10+ pre-installed in image)?
   - Bundle with pyinstaller (larger, but no Python dependency)?
   - Publish to PyPI separately (parallel distribution)?

2. **Which skills go in git-workflow vs stay project-specific?**
   - Clear candidates for git-workflow: `creating-commits`, `git:commit`, `git:create-pull-request`, `pull-request-conventions`
   - Unclear: `reviewing-documentation`, `writing-documentation`, `verifying-claims`
   - Should stay project-specific: BMAD workflow skills (already in bmad-method npm package)

## Success Criteria

- [ ] All tools installable from single monorepo
- [ ] Docker image includes all tools in PATH
- [ ] Updating monorepo automatically updates all consumers on next container rebuild
- [ ] No tool-related code in claude-devcontainer (only config)
- [ ] CI/CD pipeline builds and publishes all artifacts
- [ ] Documentation covers consumer setup

## Related Documents

- [BMAD Orchestrator Tech Spec](../../packages/bmad-orchestrator/docs/implementation/tech-spec-bmad-orchestrator.md) (after migration)
- [Claude DevContainer README](../../README.md)
