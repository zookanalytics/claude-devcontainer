# Story 1.2: Configure ESLint, Prettier, and Spell Checking

Status: done

## Story

As a **developer**,
I want **consistent code formatting and linting rules enforced**,
So that **code quality is maintained across all contributions**.

## Acceptance Criteria

### AC1: ESLint with Flat Config
**Given** the package is initialized
**When** I run `pnpm check:lint`
**Then** ESLint runs with the flat config format
**And** TypeScript strict type checking rules are enforced
**And** Unicorn, SonarJS, and Perfectionist plugins are configured
**And** React/Ink-specific rules are applied to component files
**And** Filename case conventions are enforced (PascalCase components, camelCase lib)

### AC2: Prettier Formatting
**Given** source files exist
**When** I run `pnpm check:format`
**Then** Prettier checks formatting with single quotes enabled
**And** the check passes for properly formatted files

### AC3: Auto-Fix Command
**Given** source files with code style issues exist
**When** I run `pnpm fix`
**Then** ESLint auto-fixes what it can
**And** Prettier reformats all files
**And** the codebase is consistent

### AC4: Spell Checking
**Given** source files with typos exist
**When** I run `pnpm check:spellcheck`
**Then** cspell identifies spelling errors
**And** project-specific terms are whitelisted in cspell.config.yaml

### AC5: Markdown Linting
**Given** markdown files exist
**When** I run `pnpm check:markdownlint`
**Then** markdownlint-cli2 validates markdown formatting
**And** the check passes for properly formatted markdown

## Tasks / Subtasks

- [x] Task 1: Install ESLint and plugins (AC: #1)
  - [x] Install `eslint@^9.0.0` (flat config support)
  - [x] Install `@eslint/js` for recommended rules
  - [x] Install `typescript-eslint` for TypeScript support
  - [x] Install `eslint-plugin-unicorn` for code quality
  - [x] Install `eslint-plugin-sonarjs` for bug detection
  - [x] Install `eslint-plugin-perfectionist` for import/member sorting
  - [x] Install `eslint-plugin-react` and `eslint-plugin-react-hooks` for React/Ink
  - [x] Install `eslint-config-prettier` (MUST be last in config)
  - [x] Install `globals` for browser/node global definitions

- [x] Task 2: Configure ESLint flat config (AC: #1)
  - [x] Create `eslint.config.mjs` with flat config format (NOT .js)
  - [x] Enable TypeScript strict type-checking rules with `projectService`
  - [x] Configure Unicorn recommended rules
  - [x] Configure SonarJS recommended rules with adjusted thresholds
  - [x] Configure Perfectionist for import sorting (React first, then externals)
  - [x] Configure React rules for .tsx files in components/
  - [x] Add `@typescript-eslint/naming-convention` rules (PascalCase types, camelCase default)
  - [x] Add filename case rules: PascalCase for `components/*.tsx`, camelCase for others
  - [x] Add `eslint-config-prettier` as LAST config to disable conflicting rules
  - [x] Ignore patterns: node_modules, dist, coverage

- [x] Task 3: Install and configure Prettier (AC: #2, #3)
  - [x] Install `prettier@^3.0.0`
  - [x] Install `prettier-plugin-packagejson` for package.json sorting
  - [x] Create `prettier.config.mjs` (NOT .prettierrc - use ESM config)
  - [x] Create `.prettierignore` for generated files
  - [x] Configure: singleQuote: true

- [x] Task 4: Install and configure cspell (AC: #4)
  - [x] Install `cspell@^9.0.0`
  - [x] Create `cspell.config.yaml`
  - [x] Add dictionaries: typescript, node, npm, bash
  - [x] Add project words: bmad, devpod, devpods, devcontainer, orchestrator, tmux, tsx, etc.
  - [x] Configure ignorePaths: node_modules, dist, pnpm-lock.yaml

- [x] Task 5: Install and configure markdownlint (AC: #5)
  - [x] Install `markdownlint-cli2`
  - [x] Create `.markdownlint-cli2.jsonc` configuration
  - [x] Configure rules appropriate for technical docs

- [x] Task 6: Create .editorconfig for editor consistency
  - [x] Create `.editorconfig` with standard settings
  - [x] Set indent_style, indent_size, charset, end_of_line

- [x] Task 7: Add npm scripts (AC: #1, #2, #3, #4, #5)
  - [x] Install `concurrently` for parallel script execution
  - [x] Add `check:lint` script: `eslint --cache src/`
  - [x] Add `check:format` script: `prettier --cache --check .`
  - [x] Add `check:spellcheck` script: `cspell --cache "src/**/*" "*.md"`
  - [x] Add `check:markdownlint` script: `markdownlint-cli2`
  - [x] Add `fix` script: `pnpm format && eslint --fix --cache src/`
  - [x] Add `fix:markdownlint` script: `markdownlint-cli2 --fix`
  - [x] Add `format` script: `prettier --cache --write .`
  - [x] Add `check` script using concurrently for parallel execution

- [x] Task 8: Fix existing code to pass all checks (AC: #1, #2, #3, #4, #5)
  - [x] Run `pnpm fix` on existing src/ files
  - [x] Update any code patterns flagged by linters
  - [x] Verify all checks pass: `pnpm check`

- [x] Task 9: Update package namespace
  - [x] Change package name from `@claude-devcontainer/bmad-dashboard` to `@zookanalytics/bmad-dashboard`

### Review Follow-ups (AI)
- [x] [AI-Review][High] Fix Git Pollution: Add `.eslintcache` and `.cspellcache` to `.gitignore` to prevent tracking build artifacts.
- [x] [AI-Review][High] Fix Lint Coverage: Update `check:lint` script to include root configuration files (`*.config.mjs`, etc.) not just `src/`.
- [x] [AI-Review][Medium] Fix Spellcheck Coverage: Update `check:spellcheck` to include root configuration files.
- [x] [AI-Review][Medium] Documentation: Update File List to reflect actual file status including cache files (or their removal).

## Dev Notes

### Reference: lint_example Directory

The `lint_example/` directory contains battle-tested configurations from ZookAnalytics. Use these as the primary reference:
- `lint_example/eslint.config.mjs` - Complete ESLint flat config with naming conventions
- `lint_example/prettier.config.mjs` - Prettier ESM config with packagejson plugin
- `lint_example/cspell.config.yaml` - Comprehensive cspell configuration
- `lint_example/.editorconfig` - Editor consistency settings
- `lint_example/.markdownlint-cli2.jsonc` - Markdown linting rules

### ESLint Flat Config Pattern (MUST USE)

ESLint 9.x uses flat config format. The configuration file MUST be `eslint.config.mjs`, NOT `.eslintrc.*` or `.js`.

```javascript
// eslint.config.mjs
import pluginJs from '@eslint/js';
import eslintConfigPrettier from 'eslint-config-prettier';
import perfectionist from 'eslint-plugin-perfectionist';
import sonarjs from 'eslint-plugin-sonarjs';
import eslintPluginUnicorn from 'eslint-plugin-unicorn';
import globals from 'globals';
import tseslint from 'typescript-eslint';

/** @type {import('eslint').Linter.Config[]} */
const eslintConfig = [
  pluginJs.configs.recommended,
  ...tseslint.configs.strictTypeChecked,
  ...tseslint.configs.stylisticTypeChecked,
  eslintPluginUnicorn.configs.recommended,
  {
    ...sonarjs.configs.recommended,
    rules: {
      ...sonarjs.configs.recommended.rules,
      'sonarjs/cognitive-complexity': ['error', 20],
      'sonarjs/todo-tag': 'error',
    },
  },
  {
    plugins: { perfectionist },
    rules: {
      ...perfectionist.configs['recommended-natural'].rules,
      'perfectionist/sort-objects': 'off', // Semantic grouping matters more
    },
  },
  {
    languageOptions: {
      ecmaVersion: 2025,
      globals: { ...globals.node },
      parserOptions: {
        projectService: {
          allowDefaultProject: ['*.mjs'],
          defaultProject: 'tsconfig.json',
        },
        tsconfigRootDir: import.meta.dirname,
      },
      sourceType: 'module',
    },
  },
  // Naming conventions - CRITICAL for consistency
  {
    rules: {
      '@typescript-eslint/naming-convention': [
        'error',
        { format: ['camelCase'], selector: 'default' },
        { format: ['camelCase', 'UPPER_CASE', 'PascalCase'], selector: 'variable' },
        { format: ['camelCase', 'PascalCase'], selector: 'function' },
        { format: ['PascalCase'], selector: 'typeLike' },
        { format: ['UPPER_CASE'], selector: 'enumMember' },
        { format: null, selector: 'objectLiteralProperty' },
        { format: null, selector: 'import' },
      ],
      'unicorn/no-null': 'off', // APIs use null semantically
    },
  },
  // React component files: PascalCase
  {
    files: ['src/components/**/*.tsx'],
    rules: {
      'unicorn/filename-case': ['error', { case: 'pascalCase' }],
    },
  },
  // Other files: camelCase
  {
    files: ['**/*.{ts,tsx,mjs}'],
    ignores: ['src/components/**/*.tsx'],
    rules: {
      'unicorn/filename-case': ['error', { case: 'camelCase' }],
    },
  },
  // Ignore patterns
  {
    ignores: ['dist/**', 'node_modules/**', 'coverage/**'],
  },
  // MUST be last - disables rules that conflict with Prettier
  eslintConfigPrettier,
];

export default eslintConfig;
```

### Required Dependencies

**Production Dependencies:** None (linting is dev-only)

**Dev Dependencies:**
```json
{
  "@eslint/js": "^9.39.0",
  "concurrently": "^9.0.0",
  "cspell": "^9.4.0",
  "eslint": "^9.39.0",
  "eslint-config-prettier": "^10.0.0",
  "eslint-plugin-perfectionist": "^5.0.0",
  "eslint-plugin-react": "^7.0.0",
  "eslint-plugin-react-hooks": "^5.0.0",
  "eslint-plugin-sonarjs": "^3.0.0",
  "eslint-plugin-unicorn": "^62.0.0",
  "globals": "^16.0.0",
  "markdownlint-cli2": "^0.20.0",
  "prettier": "^3.7.0",
  "prettier-plugin-packagejson": "^2.5.0",
  "typescript-eslint": "^8.51.0"
}
```

### Prettier Configuration (ESM format)

```javascript
// prettier.config.mjs
/**
 * @see https://prettier.io/docs/configuration
 * @type {import("prettier").Config}
 */
const config = {
  $schema: 'https://json.schemastore.org/prettierrc',
  plugins: ['prettier-plugin-packagejson'],
  singleQuote: true,
};

export default config;
```

### cspell Configuration

```yaml
# cspell.config.yaml
version: '0.2'
language: en
useGitignore: true

ignorePaths:
  - node_modules
  - dist
  - pnpm-lock.yaml
  - coverage

words:
  - bmad
  - devpod
  - devpods
  - devcontainer
  - zookanalytics
  - orchestrator
  - tmux
  - tsx
  - nocheck
  - typecheck
  - esmodule
  - sourcemap
  - outdir
  - rootdir
  - sonarjs
  - perfectionist
  - unicorn

dictionaries:
  - typescript
  - node
  - npm
  - bash
```

### .editorconfig

```ini
# .editorconfig
root = true

[*]
charset = utf-8
end_of_line = lf
indent_size = 2
indent_style = space
insert_final_newline = true
trim_trailing_whitespace = true

[*.md]
trim_trailing_whitespace = false
```

### npm Scripts Pattern

```json
{
  "scripts": {
    "type-check": "tsc --noEmit",
    "check": "concurrently --group --timings -c auto --prefix name --kill-others-on-fail 'pnpm:check:*' 'pnpm:type-check'",
    "check:lint": "eslint --cache src/",
    "check:format": "prettier --cache --check .",
    "check:spellcheck": "cspell --cache --quiet \"src/**/*\" \"*.md\"",
    "check:markdownlint": "markdownlint-cli2",
    "fix": "pnpm format && eslint --fix --cache src/",
    "fix:markdownlint": "markdownlint-cli2 --fix",
    "format": "prettier --cache --write --log-level warn .",
    "build": "tsc",
    "dev": "tsx src/cli.ts"
  }
}
```

### Project Structure Notes

Story 1-1 established the package structure at `packages/bmad-dashboard/`:
```
packages/bmad-dashboard/
├── bin/bmad-dashboard       # CLI entry point with tsx shebang
├── src/
│   ├── cli.ts              # Commander setup (exists from story 1-1)
│   ├── types.ts            # Empty placeholder (exists from story 1-1)
│   ├── commands/           # Empty directory
│   ├── components/         # Empty directory
│   └── lib/                # Empty directory
├── package.json            # ESM module config (UPDATE namespace to @zookanalytics)
└── tsconfig.json           # TypeScript strict mode
```

New files to create:
- `eslint.config.mjs` - ESLint flat config (ESM format)
- `prettier.config.mjs` - Prettier configuration (ESM format)
- `.prettierignore` - Files to skip formatting
- `cspell.config.yaml` - Spell checking configuration
- `.markdownlint-cli2.jsonc` - Markdown linting rules
- `.editorconfig` - Editor consistency settings

### Package Namespace Change

**IMPORTANT:** Update package.json name from:
```json
"name": "@claude-devcontainer/bmad-dashboard"
```
To:
```json
"name": "@zookanalytics/bmad-dashboard"
```

This aligns with the ZookAnalytics namespace used in the parent monorepo.

### Previous Story (1-1) Learnings

From the completed Story 1-1:
- React 19 is installed (required for Ink 6.x)
- TypeScript strict mode is already enabled
- ESM modules configured (`"type": "module"`)
- Node.js 22 target (ES2022)
- tsx is used for development execution
- Package uses `@claude-devcontainer/bmad-dashboard` namespace

### Technology Versions (Current as of Story 1-1)

| Package | Version | Status |
|---------|---------|--------|
| TypeScript | ^5.0.0 | Installed |
| React | ^19.0.0 | Installed |
| Ink | ^6.0.0 | Installed |
| Commander | ^14.0.0 | Installed |
| tsx | ^4.0.0 | Installed |

### Architecture Compliance

**From Architecture Document:**
- File naming: PascalCase for components, lowercase for utilities
- Interface naming: No "I" prefix (e.g., `DevPod` not `IDevPod`)
- Co-located tests: `discovery.test.ts` next to `discovery.ts`
- Function declarations for components (not arrow functions)

**ESLint Rules to Enforce:**
- No "I" prefix on interfaces: Configure typescript-eslint naming convention
- Prefer function declarations: Configure unicorn/prefer-function-declaration
- Import sorting: Configure perfectionist/sort-imports

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-1.2]
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation-Patterns-Consistency-Rules]
- [Source: docs/project-context.md#BMAD-Dashboard-Package]
- [Source: _bmad-output/implementation-artifacts/1-1-initialize-package-with-typescript-configuration.md]
- [Source: lint_example/] - ZookAnalytics battle-tested lint configs (COPY AND ADAPT)

### Anti-Patterns to Avoid

| Anti-Pattern | Correct Pattern |
|--------------|-----------------|
| `.eslintrc.json` | `eslint.config.mjs` (flat config, ESM) |
| `.prettierrc` | `prettier.config.mjs` (ESM config) |
| Running eslint --fix before prettier | Run `pnpm format` first, THEN `eslint --fix` |
| Checking dist/ folder | Ignore dist/ in all lint configs |
| Double quotes in JS/TS | Single quotes (per prettier config) |
| `@claude-devcontainer/` namespace | `@zookanalytics/` namespace |
| Missing `eslint-config-prettier` | MUST be last in eslint config chain |
| Check scripts without `--cache` | Always use `--cache` for performance |

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

None

### Completion Notes List

- Installed all ESLint plugins (eslint@9.39.2, typescript-eslint@8.51.0, unicorn, sonarjs, perfectionist, react, react-hooks, eslint-config-prettier, globals)
- Created ESLint flat config with TypeScript strict rules, naming conventions, and filename case enforcement
- Installed and configured Prettier with singleQuote and packagejson plugin
- Set up cspell with project-specific words dictionary
- Configured markdownlint-cli2 with Prettier-compatible settings
- Created .editorconfig for editor consistency
- Added comprehensive npm scripts with concurrently for parallel execution
- Fixed cli.ts: corrected import order, renamed `__dirname` to `currentDirectory`, updated encoding to `utf8`
- Fixed types.ts: added `DevPodStatus` type export to satisfy no-empty-file rule
- Added 'DevPod' and 'DevPodStatus' to unicorn/prevent-abbreviations allowlist (product name, not abbreviation)
- Updated package namespace from @claude-devcontainer to @zookanalytics
- All checks pass: lint, format, spellcheck, markdownlint, type-check

**Code Review Follow-ups Addressed:**
- Added .eslintcache, .cspellcache, .prettiercache to root .gitignore
- Updated check:lint and fix scripts to include *.config.mjs files
- Updated check:spellcheck to include *.config.mjs files
- Updated File List to include .gitignore modification

### File List

**New files created:**
- packages/bmad-dashboard/eslint.config.mjs
- packages/bmad-dashboard/prettier.config.mjs
- packages/bmad-dashboard/.prettierignore
- packages/bmad-dashboard/cspell.config.yaml
- packages/bmad-dashboard/.markdownlint-cli2.jsonc
- packages/bmad-dashboard/.editorconfig

**Modified files:**
- packages/bmad-dashboard/package.json (scripts, namespace change, new devDependencies)
- packages/bmad-dashboard/src/cli.ts (import order, variable naming, encoding)
- packages/bmad-dashboard/src/types.ts (added DevPodStatus type)
- .gitignore (added linting cache files: .eslintcache, .cspellcache, .prettiercache)
- pnpm-lock.yaml (updated dependencies)

## Change Log

- 2026-01-04: Story 1.2 implemented - ESLint, Prettier, cspell, markdownlint configured with all checks passing
- 2026-01-04: Addressed code review follow-ups - added cache files to .gitignore, expanded lint/spellcheck coverage to include config files
- 2026-01-04: Code review (2nd pass) - unstaged cache files from git, added trim_trailing_whitespace to .editorconfig, documented pnpm-lock.yaml in File List

