# Story 1.1: Initialize Package with TypeScript Configuration

Status: done

## Story

As a **developer**,
I want **a properly configured npm package with TypeScript strict mode**,
So that **I can start building the dashboard with type safety from the start**.

## Acceptance Criteria

### AC1: Package Installation
**Given** the monorepo root exists at `/workspace`
**When** I run `pnpm install` from the monorepo root
**Then** the `packages/bmad-dashboard` package is installed with all dependencies
**And** the package has the directory structure defined below

### AC2: TypeScript Compilation
**Given** the package is initialized
**When** I run `pnpm type-check` from the package directory
**Then** TypeScript compiles successfully with strict mode enabled
**And** the tsconfig.json targets Node.js 22 with ESM modules

### AC3: CLI Version Command
**Given** the bin script exists
**When** I run `bmad-dashboard --version` from the host
**Then** the version from package.json is displayed

## Tasks / Subtasks

- [x] Task 1: Create package directory structure (AC: #1)
  - [x] Create `packages/bmad-dashboard/` directory
  - [x] Create `src/` subdirectory
  - [x] Create placeholder files: `cli.ts`, `types.ts`
  - [x] Create empty subdirectories: `commands/`, `components/`, `lib/`

- [x] Task 2: Initialize package.json (AC: #1, #3)
  - [x] Run `pnpm init` in package directory
  - [x] Set package name: `@claude-devcontainer/bmad-dashboard`
  - [x] Set version: `0.1.0`
  - [x] Set license: `MIT`
  - [x] Set type: `module` (ESM)
  - [x] Add bin entry: `"bmad-dashboard": "./bin/bmad-dashboard"`
  - [x] Add dependencies: `ink@^6.0.0`, `react@^19.0.0`, `commander@^14.0.0`
  - [x] Add devDependencies: `typescript@^5.0.0`, `@types/react@^19.0.0`, `@types/node`, `tsx`
  - [x] Add scripts: `type-check`, `build`, `dev`

- [x] Task 3: Configure TypeScript (AC: #2)
  - [x] Create `tsconfig.json` with strict mode
  - [x] Target: ES2022
  - [x] Module: NodeNext (required when moduleResolution is NodeNext)
  - [x] ModuleResolution: NodeNext
  - [x] Enable all strict options
  - [x] Set outDir: `./dist`
  - [x] Set rootDir: `./src`

- [x] Task 4: Create bin script (AC: #3)
  - [x] Create `bin/bmad-dashboard` executable script
  - [x] Add shebang for Node.js with tsx (`#!/usr/bin/env -S npx tsx`)
  - [x] Import and run CLI entry point

- [x] Task 5: Create minimal CLI entry point (AC: #3)
  - [x] Create `src/cli.ts` with Commander setup
  - [x] Add version command from package.json
  - [x] Export program for bin script

- [x] Task 6: Verify installation (AC: #1, #2, #3)
  - [x] Run `pnpm install` from monorepo root
  - [x] Run `pnpm type-check` from package directory
  - [x] Run `bmad-dashboard --version` and verify output (returns "0.1.0")

### Review Follow-ups (AI)
- [x] [AI-Review][Medium] File .gitignore was modified but not listed in the story's File List. → Not part of this story (lint_example for story 1-2)
- [x] [AI-Review][Medium] File _bmad-output/implementation-artifacts/sprint-status.yaml was modified but not listed in the story's File List.
- [x] [AI-Review][Medium] File pnpm-lock.yaml is listed as modified in the story, but is untracked in git.


## Dev Notes

### Required Directory Structure

```
packages/bmad-dashboard/
├── src/
│   ├── cli.ts           # Commander setup, entry point
│   ├── commands/        # CLI subcommand handlers (empty for now)
│   ├── components/      # Ink React components (empty for now)
│   ├── lib/             # Business logic (empty for now)
│   └── types.ts         # TypeScript interfaces (empty for now)
├── bin/bmad-dashboard   # Executable entry script with shebang
├── package.json
└── tsconfig.json
```

### Technology Stack (MUST USE THESE VERSIONS)

| Package | Version | Notes |
|---------|---------|-------|
| Ink | ^6.0.0 | React for CLI TUI (latest: 6.6.0) |
| Commander | ^14.0.0 | CLI argument parsing (latest: 14.0.2) |
| React | ^19.0.0 | Component framework (required by Ink 6) |
| TypeScript | ^5.0.0 | Strict mode required |
| Node.js | 22 | Target runtime |

### package.json Structure

```json
{
  "name": "@claude-devcontainer/bmad-dashboard",
  "version": "0.1.0",
  "license": "MIT",
  "type": "module",
  "description": "TUI dashboard for multi-DevPod BMAD orchestration",
  "bin": {
    "bmad-dashboard": "./bin/bmad-dashboard"
  },
  "scripts": {
    "type-check": "tsc --noEmit",
    "build": "tsc",
    "dev": "tsx src/cli.ts"
  },
  "dependencies": {
    "commander": "^14.0.0",
    "ink": "^6.0.0",
    "react": "^19.0.0"
  },
  "devDependencies": {
    "@types/node": "^25.0.3",
    "@types/react": "^19.0.0",
    "tsx": "^4.0.0",
    "typescript": "^5.0.0"
  }
}
```

### tsconfig.json Configuration

```json
{
  "$schema": "https://json.schemastore.org/tsconfig",
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "strict": true,
    "esModuleInterop": true,
    "forceConsistentCasingInFileNames": true,
    "skipLibCheck": true,
    "isolatedModules": true,
    "resolveJsonModule": true,
    "outDir": "./dist",
    "rootDir": "./src",
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "jsx": "react-jsx",
    "jsxImportSource": "react"
  },
  "include": ["src/**/*.ts", "src/**/*.tsx"],
  "exclude": ["node_modules", "dist"]
}
```

### bin/bmad-dashboard Script

```bash
#!/usr/bin/env node
import '../dist/cli.js';
```

**Alternative (for development with tsx):**
```bash
#!/usr/bin/env npx tsx
import '../src/cli.ts';
```

### Minimal CLI Entry Point (src/cli.ts)

```typescript
import { Command } from 'commander';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const packageJson = JSON.parse(
  readFileSync(join(__dirname, '..', 'package.json'), 'utf-8')
);

const program = new Command();

program
  .name('bmad-dashboard')
  .description('TUI dashboard for multi-DevPod BMAD orchestration')
  .version(packageJson.version);

program.parse();
```

### Project Structure Notes

- Package lives in `packages/bmad-dashboard/` within the monorepo
- Uses pnpm workspace (monorepo root has pnpm-workspace.yaml)
- ESM modules throughout (type: "module" in package.json)
- TypeScript strict mode is mandatory per architecture

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Starter-Template-Evaluation]
- [Source: _bmad-output/planning-artifacts/architecture.md#Project-Structure-Boundaries]
- [Source: _bmad-output/planning-artifacts/epics.md#Story-1.1]
- [Source: docs/project-context.md#BMAD-Dashboard-Package]

### Anti-Patterns to Avoid

| Anti-Pattern | Correct Pattern |
|--------------|-----------------|
| Using CJS (require) | Use ESM (import) |
| `tsconfig` without strict | Always enable strict: true |
| Arrow functions for components | Use function declarations |
| `interface IDevPod` | `interface DevPod` (no prefix) |
| Separate `__tests__` folder | Co-locate tests with source |

### Verification Commands

```bash
# From monorepo root
pnpm install

# From packages/bmad-dashboard
pnpm type-check

# Test CLI
./bin/bmad-dashboard --version
# OR
pnpm dev --version
```

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

None

### Completion Notes List

- Created package directory structure with all required subdirectories (src/commands, src/components, src/lib)
- Configured package.json with ESM modules, proper bin entry, and all scripts
- Updated React to v19 to satisfy Ink 6.x peer dependencies (Ink 6 requires React ≥19)
- Removed ink-spinner from dependencies as not needed for this story (can be added when TUI components are built)
- Fixed tsconfig.json module setting: "ESNext" → "NodeNext" (required when moduleResolution is NodeNext)
- Added @types/node dev dependency for Node.js built-in module types
- Fixed bin script shebang: `#!/usr/bin/env -S npx tsx` (the -S flag is required for space-separated args)
- All acceptance criteria verified: pnpm install ✓, type-check ✓, --version returns 0.1.0 ✓

### File List

- _bmad-output/implementation-artifacts/sprint-status.yaml (modified)
- docs/project-context.md (modified - version updates from code review)
- packages/bmad-dashboard/package.json (created)
- packages/bmad-dashboard/tsconfig.json (created)
- packages/bmad-dashboard/bin/bmad-dashboard (created)
- packages/bmad-dashboard/src/cli.ts (created)
- packages/bmad-dashboard/src/types.ts (created)
- packages/bmad-dashboard/src/commands/ (created, empty)
- packages/bmad-dashboard/src/components/ (created, empty)
- packages/bmad-dashboard/src/lib/ (created, empty)
- pnpm-lock.yaml (created)

## Change Log

- 2026-01-04: Story 1.1 implemented - package structure, TypeScript config, and CLI entry point created
- 2026-01-04: Addressed code review findings - corrected File List to include all modified files
- 2026-01-04: Code review pass - fixed 4 documentation issues (React 19 versions, tsconfig module setting, package.json example)

