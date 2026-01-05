# Story 1.3: Configure Pre-commit Hooks and CI Workflow

Status: done

## Story

As a **developer**,
I want **automated quality gates on commit and PR**,
So that **code quality issues are caught before merge**.

## Acceptance Criteria

### AC1: Husky Pre-commit Hook
**Given** Husky is installed
**When** I make a git commit
**Then** lint-staged runs ESLint, Prettier, and type-check on staged files
**And** the commit is blocked if checks fail

### AC2: Commitlint Enforcement
**Given** Commitlint is configured
**When** I make a commit with message "added feature"
**Then** the commit is rejected with an error about conventional commit format
**And** a commit with "feat(bmad-dashboard): add worker list component" succeeds

### AC3: CI Workflow on PR
**Given** the CI workflow exists at `.github/workflows/code-quality.yml`
**When** a PR is opened
**Then** the workflow runs `pnpm check` (lint, format, spellcheck, type-check)
**And** the PR title is validated against conventional commit format
**And** the workflow fails if any check fails

### AC4: Parallel Check Script
**Given** pnpm scripts are configured
**When** I run `pnpm check`
**Then** all quality checks run in parallel (lint, format, spellcheck, type-check)
**And** the command exits with failure if any check fails

## Tasks / Subtasks

- [x] Task 1: Install Husky for git hooks (AC: #1)
  - [x] Install `husky@^9.0.0` as devDependency
  - [x] Add `prepare` script: `husky` (sets up git hooks on install)
  - [x] Run `pnpm prepare` to initialize .husky directory

- [x] Task 2: Configure Husky pre-commit hook (AC: #1)
  - [x] Create `.husky/pre-commit` hook file
  - [x] Hook runs: `cd packages/bmad-dashboard && pnpm pre-commit`
  - [x] Make hook executable (chmod +x)

- [x] Task 3: Install and configure lint-staged (AC: #1)
  - [x] Install `lint-staged@^16.0.0` as devDependency
  - [x] Add lint-staged config to package.json
  - [x] Configure for TypeScript files: eslint --fix, prettier --write, cspell
  - [x] Configure for markdown files: prettier, markdownlint-cli2 --fix, cspell
  - [x] Configure for config files (*.config.mjs, *.json, *.yaml)

- [x] Task 4: Install and configure Commitlint (AC: #2)
  - [x] Install `@commitlint/cli@^20.0.0` as devDependency
  - [x] Install `@commitlint/config-conventional@^20.0.0` as devDependency
  - [x] Create `commitlint.config.mjs` in package directory
  - [x] Configure allowed types: feat, fix, refactor, perf, style, test, docs, build, ops, security, chore, revert
  - [x] Configure allowed scopes: ai-tools, bmad-dashboard, ci, deps, devcontainer, docs, tests
  - [x] Scope required as warning only (not error)

- [x] Task 5: Configure Husky commit-msg hook (AC: #2)
  - [x] Create `.husky/commit-msg` hook file
  - [x] Hook runs: `pnpm commitlint --edit "$1"` (from monorepo root)
  - [x] Add `commitlint` script to package.json: `commitlint --edit`
  - [x] Make hook executable (chmod +x)

- [x] Task 6: Create CI workflow for code quality (AC: #3)
  - [x] Create `.github/workflows/code-quality.yml`
  - [x] Trigger on push to main and pull_request events
  - [x] Skip CI on draft PRs (conserve GH Action minutes)
  - [x] Use pnpm/action-setup for pnpm installation
  - [x] Use actions/setup-node with node-version-file and pnpm cache
  - [x] Run `pnpm install --frozen-lockfile`
  - [x] Run `pnpm --filter bmad-dashboard check`

- [x] Task 7: Add PR title validation to CI (AC: #3)
  - [x] Use `amannn/action-semantic-pull-request@v6` action
  - [x] Configure allowed types matching commitlint.config.mjs
  - [x] Configure allowed scopes matching commitlint.config.mjs
  - [x] Require scope: false (warning only)
  - [x] Validate subject starts with lowercase
  - [x] Limit header length to 72 characters

- [x] Task 8: Add pre-commit script shortcut (AC: #4)
  - [x] Add `pre-commit` script to package.json: `pnpm lint-staged && pnpm type-check`
  - [x] This allows manual `pnpm pre-commit` for verification before commit
  - [x] Verify `pnpm check` runs all checks in parallel (already configured)

- [x] Task 9: Verify all hooks work end-to-end (AC: #1, #2, #3, #4)
  - [x] Test pre-commit hook catches lint errors
  - [x] Test commit-msg hook rejects non-conventional commits
  - [x] Test `pnpm check` runs all checks in parallel
  - [x] Verify CI workflow syntax is valid

- [x] Review Follow-ups (AI) - Round 1
  - [x] [AI-Review][Medium] Update story File List to include modified documentation files
  - [x] [AI-Review][Low] Correct Dev Notes regarding location of commitlint.config.mjs

- [x] Review Follow-ups (AI) - Round 2
  - [x] [AI-Review][High] Fixed pre-commit hook to run `pnpm pre-commit` (includes type-check)
  - [x] [AI-Review][High] Deleted stale review findings file
  - [x] [AI-Review][Medium] Updated task descriptions to match actual hook implementations
  - [x] [AI-Review][Medium] Validated CI workflow YAML syntax

## Dev Notes

### Monorepo Context

This is a pnpm workspace monorepo. The bmad-dashboard package is at `packages/bmad-dashboard/`. When configuring hooks:
- Husky hooks are at the **monorepo root** (`.husky/`)
- lint-staged config is in the **package** (`packages/bmad-dashboard/package.json`)
- Commitlint config is at the **monorepo root** (`commitlint.config.mjs`) - applies to all packages
- CI workflow runs filtered to bmad-dashboard: `pnpm --filter bmad-dashboard check`

### Reference Configurations (lint_example/)

The `lint_example/` directory contains battle-tested configurations from ZookAnalytics:

**commitlint.config.mjs:**
```javascript
const commitlintConfig = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [
      2, 'always',
      ['build', 'chore', 'docs', 'feat', 'fix', 'ops', 'perf', 'refactor', 'revert', 'security', 'style', 'test'],
    ],
    'scope-enum': [
      2, 'always',
      ['ai-tools', 'bmad-dashboard', 'ci', 'deps', 'devcontainer', 'docs', 'tests'],
    ],
    'scope-empty': [1, 'never'], // Warning only
  },
};
export default commitlintConfig;
```

**lint-staged config (in package.json):**
```json
{
  "lint-staged": {
    "src/**/*.{ts,tsx}": [
      "eslint --fix --cache",
      "prettier --write",
      "cspell --no-must-find-files"
    ],
    "*.config.mjs": [
      "eslint --fix --cache",
      "prettier --write",
      "cspell --no-must-find-files"
    ],
    "*.md": [
      "prettier --write",
      "markdownlint-cli2 --no-globs --fix",
      "cspell --no-must-find-files"
    ],
    "*.{json,yaml,yml}": [
      "prettier --write"
    ]
  }
}
```

**Code Quality CI Workflow Pattern:**
```yaml
name: Code Quality

on:
  push:
    branches: [main]
  pull_request:
    types: [opened, edited, synchronize, reopened, ready_for_review]

jobs:
  code-quality:
    runs-on: ubuntu-latest
    if: github.event.pull_request.draft == false || github.event_name == 'push'
    steps:
      - name: Check PR title
        if: github.event_name == 'pull_request' && (github.event.action == 'opened' || github.event.action == 'edited')
        uses: amannn/action-semantic-pull-request@v6
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          types: |
            build
            chore
            docs
            feat
            fix
            ops
            perf
            refactor
            revert
            security
            style
            test
          scopes: |
            ai-tools
            bmad-dashboard
            ci
            deps
            devcontainer
            docs
            tests
          requireScope: false
          subjectPattern: ^(?![A-Z]).+$
          subjectPatternError: Subject must start with lowercase letter.

      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v5
        with:
          node-version-file: package.json
          cache: 'pnpm'
      - run: pnpm install --frozen-lockfile
      - run: pnpm --filter bmad-dashboard check
```

### Husky Setup Pattern

**Root package.json:**
```json
{
  "scripts": {
    "prepare": "husky"
  },
  "devDependencies": {
    "husky": "^9.1.7"
  }
}
```

**Note:** Husky is installed at the **monorepo root** because git hooks are repository-wide. The hooks then `cd` into the specific package.

**.husky/pre-commit:**
```bash
cd packages/bmad-dashboard && pnpm pre-commit
```

**.husky/commit-msg:** (runs from monorepo root since commitlint config is at root)
```bash
pnpm commitlint --edit "$1"
```

### Required Dependencies

**At Monorepo Root (workspace root package.json):**
```json
{
  "devDependencies": {
    "@commitlint/cli": "^20.3.0",
    "@commitlint/config-conventional": "^20.3.0",
    "husky": "^9.1.7"
  }
}
```

**In packages/bmad-dashboard/package.json:**
```json
{
  "devDependencies": {
    "lint-staged": "^16.2.7"
  }
}
```

### Project Structure After Story 1.3

```
/workspace/
├── .github/
│   └── workflows/
│       ├── code-quality.yml   # NEW - Code quality checks on PR
│       └── publish.yml        # Existing Docker publish
├── .husky/
│   ├── pre-commit             # NEW - Runs pre-commit (lint-staged + type-check)
│   └── commit-msg             # NEW - Runs commitlint
├── commitlint.config.mjs      # NEW - Commitlint configuration (monorepo root)
├── package.json               # MODIFY - Add prepare script, husky + commitlint deps
└── packages/
    └── bmad-dashboard/
        └── package.json       # MODIFY - Add lint-staged config, pre-commit script
```

### Previous Story (1-2) Learnings

From Story 1-2 completion notes:
- ESLint flat config (`eslint.config.mjs`) is already configured with all plugins
- Prettier configured with singleQuote and packagejson plugin
- cspell configured with project words dictionary
- markdownlint-cli2 configured
- All `pnpm check` subscripts use `--cache` for performance
- Package namespace is `@zookanalytics/bmad-dashboard`
- Cache files (.eslintcache, .cspellcache) are in .gitignore

**Scripts already configured in package.json:**
- `check` - Parallel execution with concurrently
- `check:lint` - ESLint with cache
- `check:format` - Prettier with cache
- `check:spellcheck` - cspell with cache
- `check:markdownlint` - markdownlint-cli2
- `fix` - Format then lint fix
- `type-check` - TypeScript --noEmit

### Architecture Compliance

**From Architecture Document:**
- Co-located tests: Pattern established but not in scope for this story
- Conventional commits: This story enforces them via commitlint
- CI workflow must not block on draft PRs to conserve GH Action minutes

**From project-context.md:**
- Use `/commit` command which follows creating-commits skill
- Follow conventional commits: `type(scope): description`
- Run checks before committing: `pnpm pre-commit`
- Commit types: feat, fix, refactor, perf, style, test, docs, build, ops, security, chore
- Scopes: ai-tools, devcontainer, bmad-dashboard, ci, deps, docs, tests

### Anti-Patterns to Avoid

| Anti-Pattern | Correct Pattern |
|--------------|-----------------|
| Husky hooks in package subdirectory | Husky hooks at monorepo root (.husky/) |
| `--no-verify` flag | Let hooks run, fix issues |
| lint-staged without --fix | Use `eslint --fix`, `prettier --write` |
| CI running on draft PRs | Skip with `if: github.event.pull_request.draft == false` |
| Commitlint error on missing scope | Warning only (`scope-empty: [1, 'never']`) |
| Running lint-staged globally | Run in package directory with `cd packages/bmad-dashboard` |
| Hardcoded Node version in CI | Use `node-version-file: package.json` |

### Testing the Implementation

**Test Pre-commit Hook:**
```bash
# Create a file with lint errors
echo "const x=1" >> packages/bmad-dashboard/src/test.ts
git add packages/bmad-dashboard/src/test.ts
git commit -m "test commit"
# Should fail with lint errors, then auto-fix and require re-staging
```

**Test Commitlint:**
```bash
# Invalid commit message
git commit -m "added feature"
# Should fail: "added feature" is not conventional

# Valid commit message
git commit -m "feat(bmad-dashboard): add test file"
# Should pass
```

**Test CI Workflow Locally (optional):**
```bash
# Validate workflow syntax
# GitHub CLI: gh workflow view code-quality.yml
# Or use act: act -l
```

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-1.3]
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation-Patterns-Consistency-Rules]
- [Source: docs/project-context.md#BMAD-Dashboard-Package]
- [Source: _bmad-output/implementation-artifacts/1-2-configure-eslint-prettier-and-spell-checking.md]
- [Source: lint_example/commitlint.config.mjs]
- [Source: lint_example/package.json#lint-staged]
- [Source: lint_example/workflows/code-quality.yml]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

None required - implementation completed successfully.

### Completion Notes List

- Installed husky@^9.1.7 at monorepo root with `prepare` script
- Created `.husky/pre-commit` hook that runs `pnpm pre-commit` (lint-staged + type-check) in bmad-dashboard package
- Created `.husky/commit-msg` hook that runs commitlint from monorepo root
- Installed lint-staged@^16.2.7 in bmad-dashboard package with configuration for TS, config, markdown, and JSON/YAML files
- Installed @commitlint/cli@^20.3.0 and @commitlint/config-conventional@^20.3.0 at monorepo root (repo-wide tool)
- Created commitlint.config.mjs at monorepo root with conventional commit types and project-specific scopes
- Scope is configured as warning-only (level 1) per story requirements
- Created CI workflow at `.github/workflows/code-quality.yml` with PR title validation
- CI workflow skips draft PRs to conserve GitHub Actions minutes
- Added `pre-commit` script for manual verification before committing
- All quality checks pass: lint, format, spellcheck, markdownlint, type-check
- Verified commitlint rejects "added feature" and accepts "feat(bmad-dashboard): add worker list component"

### File List

**New files:**
- .husky/pre-commit
- .husky/commit-msg
- .github/workflows/code-quality.yml
- commitlint.config.mjs (at monorepo root - applies to all packages)

**Modified files:**
- package.json (added husky, commitlint devDependencies, prepare and commitlint scripts)
- packages/bmad-dashboard/package.json (added lint-staged config and pre-commit script)
- pnpm-lock.yaml (updated with new dependencies)
- docs/commit_specification.md (updated scopes to match monorepo packages)
- docs/project-context.md (updated scopes list)

### Change Log

- 2026-01-05: Story 1.3 implemented - Pre-commit hooks (Husky + lint-staged), commit message validation (commitlint at root), and CI workflow (code-quality.yml with PR title validation)
- 2026-01-05: Code review round 2 - Fixed pre-commit hook to include type-check, updated documentation to match actual implementations, validated CI workflow syntax
