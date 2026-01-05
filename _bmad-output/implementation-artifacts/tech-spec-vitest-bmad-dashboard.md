---
title: 'Vitest Test Infrastructure for BMAD Dashboard'
slug: 'vitest-bmad-dashboard'
created: '2026-01-05'
status: 'completed'
stepsCompleted: [1, 2, 3, 4]
tech_stack:
  - vitest-4.x
  - '@vitest/coverage-v8'
  - typescript-5.x
  - esm
  - node-22.x
files_to_modify:
  - packages/bmad-dashboard/package.json
  - packages/bmad-dashboard/vitest.config.ts
  - packages/bmad-dashboard/tsconfig.json
  - packages/bmad-dashboard/.gitignore
  - packages/bmad-dashboard/src/lib/example.ts
  - packages/bmad-dashboard/src/lib/example.test.ts
  - .github/workflows/tests.yml
code_patterns:
  - esm-package-type-module
  - typescript-nodenext-modules
  - co-located-tests
  - lowercase-lib-files
test_patterns:
  - vitest-node-environment
  - globals-enabled
  - v8-coverage-provider
  - 90-percent-thresholds
---

# Tech-Spec: Vitest Test Infrastructure for BMAD Dashboard

**Created:** 2026-01-05

## Overview

### Problem Statement

The `packages/bmad-dashboard` package has no test infrastructure. Without tests, we can't verify functionality, prevent regressions, or enforce code quality standards before merging PRs.

### Solution

Set up Vitest with TypeScript/ESM support, coverage reporting with 90% thresholds enforced, and CI integration with coverage comparison against base branch.

### Scope

**In Scope:**

- Install Vitest + coverage dependencies
- Create `vitest.config.ts` (node environment, ESM, TypeScript)
- Add test scripts to package.json (`test`, `test:watch`, `test:coverage`)
- Create sample testable code + test file to verify setup and meet 90% thresholds
- Create new CI workflow job for tests with coverage comparison
- Enforce 90% coverage thresholds from the start
- Enable test globals (`describe`, `it`, `expect`)

**Out of Scope:**

- React/Ink component testing with jsdom (deferred to Story 2.1)
- Storybook integration
- Browser-based testing (no Playwright needed - we use node environment)
- E2E tests

## Context for Development

### Technical Preferences

- **Test Environment:** Node (not jsdom) - simpler for now, Story 2.1 can add React/Ink testing later
- **Coverage Thresholds:** 90% enforced from day one
- **Test Globals:** Enabled (`describe`, `it`, `expect` without imports)
- **CI Strategy:** Separate test job with coverage comparison against base branch
- **Node.js Version:** 22.x (read from root `package.json` engines field by CI)

### Codebase Patterns

- **Package Type:** ESM (`"type": "module"` in package.json)
- **Module Resolution:** TypeScript NodeNext
- **File Naming:** Lowercase for lib files (`discovery.ts`), PascalCase for React components
- **Test Location:** Co-located with source (`lib/example.test.ts` next to `lib/example.ts`)
- **Root Test Script:** `pnpm -r test` already exists in root package.json
- **ESM Imports:** All config and test files must use ESM `import`/`export` syntax (not CommonJS `require`)

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `test_example/vitest.config.ts` | Reference Vitest config (complex, need simpler version) |
| `test_example/package.json` | Reference test scripts and dependencies (uses vitest v4.0.16) |
| `test_example/workflows/tests.yml` | Reference CI workflow with coverage comparison |
| `packages/bmad-dashboard/tsconfig.json` | Current TypeScript config (NodeNext, JSX) |
| `docs/project-context.md` | Project patterns and naming conventions |

### Technical Decisions

1. **Node Environment Only:** Use `environment: 'node'` - no jsdom needed for utility/lib code. React/Ink component testing deferred to Story 2.1. **Note:** Reference workflow installs Playwright for browser-based Storybook tests; we skip this entirely since we're using node environment.

2. **Simplified Config:** Unlike reference (multi-project for Convex/React/Storybook), we need single-project config targeting `src/**/*.test.ts`.

3. **Coverage Exclusions:** Exclude entry points and type-only files using full glob paths:
   - `src/cli.ts` - CLI entry point
   - `src/types.ts` - Type definitions only
   - `**/*.d.ts` - Declaration files

4. **Sample Code Strategy:** Create `src/lib/example.ts` with simple testable utility function to demonstrate patterns and meet 90% threshold.
   - **Why `src/lib/`?** Establishes directory structure for future utility modules. Current files (`cli.ts`, `types.ts`) are at root level because they're entry/config files. Business logic belongs in `lib/`.

5. **CI Workflow:** New `tests.yml` workflow with 3 jobs:
   - `test` - Run tests with coverage, upload artifact
   - `test-base` - Get base branch coverage (SHA-based caching to avoid re-running)
   - `report` - Compare coverage and post PR comment

6. **Test Globals Configuration:** Requires TWO settings to work:
   - `vitest.config.ts`: `globals: true` - Makes globals available at runtime
   - `tsconfig.json`: `"types": ["vitest/globals"]` - Makes TypeScript recognize the types

### GitHub Action Workflow Details

**Reference:** `test_example/workflows/tests.yml`

**3-Job Architecture:**

1. **`test` job:**
   - Runs on PRs (non-draft) and push to main
   - Skips draft PRs (`github.event.pull_request.draft == false`)
   - Runs `pnpm --filter bmad-dashboard test:coverage`
   - Uploads coverage artifact (`coverage-current`)

2. **`test-base` job:**
   - Gets coverage from base branch for comparison
   - Uses SHA-based caching (`coverage-${{ BASE_SHA }}`) to avoid re-running tests
   - `continue-on-error: true` for graceful degradation (handles missing base coverage)
   - Only runs full test suite on cache miss

3. **`report` job:**
   - Requires `test` success, tolerates `test-base` failure
   - Downloads both coverage artifacts
   - Uses `davelosert/vitest-coverage-report-action@v2` to post PR comment
   - Threshold icons config (YAML string, not object): `"{0: '🔴', 90: '🟡', 95: '🟢'}"`

**Key Patterns from Reference:**

- Pinned action versions with SHA hashes (security) - see Task 7 for exact SHAs
- paths-ignore for docs, config, _bmad-output
- `pull-requests: write` permission for PR comments
- `node-version-file: package.json` reads Node.js version from engines field

**Adaptations for Our Setup:**

- Filter to bmad-dashboard package: `pnpm --filter bmad-dashboard test:coverage`
- Coverage artifacts from: `packages/bmad-dashboard/coverage/`
- Vitest config path: `packages/bmad-dashboard/vitest.config.ts`
- **No Playwright installation** - reference uses it for Storybook browser tests; we use node environment only

**Workflow Relationship:**

- `tests.yml` is intentionally separate from `code-quality.yml`
- Both will run on PRs; this is expected and desired
- `code-quality.yml` runs linting/formatting; `tests.yml` runs tests with coverage

## Implementation Plan

### Tasks

- [x] **Task 1: Install Vitest dependencies**
  - File: `packages/bmad-dashboard/package.json`
  - Action: Add devDependencies (matching reference versions):
    ```json
    "vitest": "^4.0.0",
    "@vitest/coverage-v8": "^4.0.0"
    ```
  - Run: `pnpm install` from `packages/bmad-dashboard/` directory
  - Verify: `pnpm ls vitest` shows installed version

- [x] **Task 2: Create .gitignore for coverage directory**
  - File: `packages/bmad-dashboard/.gitignore` (new file)
  - Action: Create with content:
    ```
    # Test coverage output
    coverage/
    ```
  - Note: Done early to prevent accidental commits of coverage data

- [x] **Task 3: Create Vitest configuration**
  - File: `packages/bmad-dashboard/vitest.config.ts` (new)
  - Action: Create config using ESM imports:
    ```typescript
    import { defineConfig } from 'vitest/config';

    export default defineConfig({
      test: {
        environment: 'node',
        globals: true,
        include: ['src/**/*.test.ts'],
        coverage: {
          provider: 'v8',
          reporter: ['text', 'json', 'json-summary'],
          reportsDirectory: 'coverage',
          include: ['src/**/*.ts'],
          exclude: [
            'src/cli.ts',
            'src/types.ts',
            '**/*.d.ts',
            '**/*.test.ts',
          ],
          thresholds: {
            lines: 90,
            functions: 90,
            branches: 90,
            statements: 90,
          },
        },
      },
    });
    ```

- [x] **Task 4: Update tsconfig.json for Vitest types**
  - File: `packages/bmad-dashboard/tsconfig.json`
  - Action: Add `types` array to compilerOptions. The current tsconfig has no `types` field, so add it:
    ```json
    "types": ["node", "vitest/globals"]
    ```
  - Note: Include "node" for Node.js types, "vitest/globals" for test globals
  - Verify: No TypeScript errors after change

- [x] **Task 5: Create sample library code**
  - File: `packages/bmad-dashboard/src/lib/example.ts` (new, creates `lib/` directory)
  - Action: Create utility function using existing DevPodStatus type:
    ```typescript
    import type { DevPodStatus } from '../types.js';

    /**
     * Format a DevPod status for display.
     */
    export function formatDevPodStatus(status: DevPodStatus): string {
      const statusMap: Record<DevPodStatus, string> = {
        idle: 'Idle',
        running: 'Running',
        stale: 'Stale',
        unknown: 'Unknown',
      };
      return statusMap[status];
    }

    /**
     * Check if a DevPod status indicates activity.
     */
    export function isActiveStatus(status: DevPodStatus): boolean {
      return status === 'running';
    }
    ```

- [x] **Task 6: Create sample test file**
  - File: `packages/bmad-dashboard/src/lib/example.test.ts` (new)
  - Action: Create comprehensive tests using ESM imports:
    ```typescript
    import { formatDevPodStatus, isActiveStatus } from './example.js';

    describe('formatDevPodStatus', () => {
      it('formats idle status', () => {
        expect(formatDevPodStatus('idle')).toBe('Idle');
      });

      it('formats running status', () => {
        expect(formatDevPodStatus('running')).toBe('Running');
      });

      it('formats stale status', () => {
        expect(formatDevPodStatus('stale')).toBe('Stale');
      });

      it('formats unknown status', () => {
        expect(formatDevPodStatus('unknown')).toBe('Unknown');
      });
    });

    describe('isActiveStatus', () => {
      it('returns true for running status', () => {
        expect(isActiveStatus('running')).toBe(true);
      });

      it('returns false for idle status', () => {
        expect(isActiveStatus('idle')).toBe(false);
      });

      it('returns false for stale status', () => {
        expect(isActiveStatus('stale')).toBe(false);
      });

      it('returns false for unknown status', () => {
        expect(isActiveStatus('unknown')).toBe(false);
      });
    });
    ```

- [x] **Task 7: Add test scripts to package.json**
  - File: `packages/bmad-dashboard/package.json`
  - Action: Add scripts section entries:
    ```json
    "test": "vitest run",
    "test:watch": "vitest",
    "test:coverage": "vitest run --coverage"
    ```
  - Run: `pnpm install` from package directory to update lockfile

- [x] **Task 8: Create CI workflow for tests**
  - File: `.github/workflows/tests.yml` (new)
  - Action: Create 3-job workflow with SHA-pinned actions:
    ```yaml
    name: Tests

    on:
      push:
        branches: [main]
        paths-ignore:
          - '_bmad-output/**'
          - 'docs/**'
          - '.claude/**'
          - '*.md'
      pull_request:
        types: [opened, synchronize, reopened, ready_for_review]
        paths-ignore:
          - '_bmad-output/**'
          - 'docs/**'
          - '.claude/**'
          - '*.md'

    jobs:
      test:
        runs-on: ubuntu-latest
        timeout-minutes: 15
        if: github.event.pull_request.draft == false || github.event_name == 'push'
        permissions:
          contents: read
        steps:
          - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4
          - uses: pnpm/action-setup@fe02b34f77f8bc703788d5817da081398fad5dd2 # v4
          - uses: actions/setup-node@39370e3970a6d050c480ffad4ff0ed4d3fdee5af # v4
            with:
              node-version-file: package.json
              cache: 'pnpm'
          - name: Install dependencies
            run: pnpm install --frozen-lockfile
          - name: Run tests with coverage
            run: pnpm --filter bmad-dashboard test:coverage
          - name: Upload coverage
            uses: actions/upload-artifact@b4b15b8c7c6ac21ea08fcf65892d2ee8f75cf882 # v4
            with:
              name: coverage-current
              path: packages/bmad-dashboard/coverage/
              retention-days: 1

      test-base:
        if: (github.event_name == 'pull_request' && github.event.pull_request.draft == false) || (github.event_name == 'push' && github.event.before != '0000000000000000000000000000000000000000')
        runs-on: ubuntu-latest
        timeout-minutes: 15
        continue-on-error: true
        permissions:
          contents: read
        outputs:
          cache-hit: ${{ steps.cache-coverage.outputs.cache-hit }}
        env:
          BASE_SHA: ${{ github.event.pull_request.base.sha || github.event.before }}
        steps:
          - name: Restore cached base coverage
            id: cache-coverage
            uses: actions/cache@6849a6489940f00c2f30c0fb92c6274307ccb58a # v4
            with:
              path: coverage-cached/
              key: coverage-${{ env.BASE_SHA }}
          - name: Upload cached coverage as artifact
            if: steps.cache-coverage.outputs.cache-hit == 'true'
            uses: actions/upload-artifact@b4b15b8c7c6ac21ea08fcf65892d2ee8f75cf882 # v4
            with:
              name: coverage-base
              path: coverage-cached/
              retention-days: 1
          - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4
            if: steps.cache-coverage.outputs.cache-hit != 'true'
            with:
              ref: ${{ env.BASE_SHA }}
          - uses: pnpm/action-setup@fe02b34f77f8bc703788d5817da081398fad5dd2 # v4
            if: steps.cache-coverage.outputs.cache-hit != 'true'
          - uses: actions/setup-node@39370e3970a6d050c480ffad4ff0ed4d3fdee5af # v4
            if: steps.cache-coverage.outputs.cache-hit != 'true'
            with:
              node-version-file: package.json
              cache: 'pnpm'
          - name: Install dependencies
            if: steps.cache-coverage.outputs.cache-hit != 'true'
            run: pnpm install --frozen-lockfile
          - name: Run tests with coverage
            if: steps.cache-coverage.outputs.cache-hit != 'true'
            run: pnpm --filter bmad-dashboard test:coverage
          - name: Prepare coverage for caching
            if: steps.cache-coverage.outputs.cache-hit != 'true' && success()
            run: |
              mkdir -p coverage-cached
              cp -r packages/bmad-dashboard/coverage/. coverage-cached/
          - name: Upload base coverage
            if: steps.cache-coverage.outputs.cache-hit != 'true' && success()
            uses: actions/upload-artifact@b4b15b8c7c6ac21ea08fcf65892d2ee8f75cf882 # v4
            with:
              name: coverage-base
              path: coverage-cached/
              retention-days: 1

      report:
        needs: [test, test-base]
        if: ${{ always() && !cancelled() && needs.test.result == 'success' }}
        runs-on: ubuntu-latest
        permissions:
          contents: read
          pull-requests: write
        steps:
          - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4
          - name: Download current coverage
            uses: actions/download-artifact@fa0a91b85d4f404e444e00e005971372dc801d16 # v4
            with:
              name: coverage-current
              path: coverage/
          - name: Download base coverage
            if: needs.test-base.result == 'success'
            uses: actions/download-artifact@fa0a91b85d4f404e444e00e005971372dc801d16 # v4
            with:
              name: coverage-base
              path: coverage-base/
          - name: Coverage Report
            uses: davelosert/vitest-coverage-report-action@v2
            with:
              json-summary-path: coverage/coverage-summary.json
              json-final-path: coverage/coverage-final.json
              vite-config-path: packages/bmad-dashboard/vitest.config.ts
              json-summary-compare-path: ${{ needs.test-base.result == 'success' && 'coverage-base/coverage-summary.json' || '' }}
    ```

- [x] **Task 9: Verify setup works locally**
  - Action: Run verification commands from package directory:
    ```bash
    cd packages/bmad-dashboard
    pnpm test           # Should pass with all tests green
    pnpm test:coverage  # Should show 90%+ coverage, generate coverage/
    ```
  - Verify: `coverage/coverage-summary.json` and `coverage/coverage-final.json` exist
  - Verify: Root `pnpm test` includes bmad-dashboard (run from repo root after Task 7)

### Acceptance Criteria

- [x] **AC 1:** Given Vitest is installed, when running `pnpm test` in `packages/bmad-dashboard`, then tests execute and pass with exit code 0.

- [x] **AC 2:** Given test:coverage script exists, when running `pnpm test:coverage`, then coverage report is generated in `packages/bmad-dashboard/coverage/` with `coverage-summary.json` AND `coverage-final.json` files.

- [x] **AC 3:** Given 90% coverage thresholds are configured, when coverage falls below 90% on any metric (lines, functions, branches, statements), then the test command fails with non-zero exit code.

- [x] **AC 4:** Given the sample test file exists, when running tests, then all tests for `example.ts` pass and coverage meets 90% threshold.

- [x] **AC 5:** Given test globals are enabled in both vitest.config.ts AND tsconfig.json, when writing tests, then `describe`, `it`, and `expect` are available without imports and TypeScript shows no errors.

- [x] **AC 6:** Given the CI workflow exists, when a non-draft PR is opened to main, then the tests workflow runs and posts a coverage report comment. Draft PRs are intentionally skipped.

- [x] **AC 7:** Given the CI workflow uses coverage comparison, when comparing to base branch with available coverage, then the PR comment shows coverage delta. When base coverage is unavailable (first PR or cache miss failure), the report still posts without comparison.

- [x] **AC 8:** Given test scripts are added to package.json (Task 7 complete), when running `pnpm test` from repo root, then bmad-dashboard tests are included in the recursive run.

## Additional Context

### Dependencies

**To Install (devDependencies):**

- `vitest` (^4.0.0) - Test framework with native ESM and TypeScript support
- `@vitest/coverage-v8` (^4.0.0) - V8 coverage provider for fast, accurate coverage

**No Additional Dependencies Needed:**

- TypeScript already installed
- No jsdom (using node environment)
- No Playwright (no browser tests)
- No additional test utilities for this phase

### Testing Strategy

**Unit Tests Only:**

- Test pure functions and utilities
- Node environment (no DOM simulation)
- Co-located test files (`*.test.ts` next to source)
- ESM imports in all test files (`.js` extension in imports)

**Coverage Enforcement:**

- 90% thresholds on all metrics from day one
- V8 provider for accurate coverage
- Exclusions for entry points (`cli.ts`) and type-only files (`types.ts`, `*.d.ts`)
- Both `json` and `json-summary` reporters required for CI action

**CI Integration:**

- Separate workflow from code-quality (intentional, both run on PRs)
- Coverage comparison against base branch with SHA-based caching
- Graceful degradation when base coverage unavailable
- PR comments with visual indicators

### Notes

**Clean Slate:**

- This is the first Vitest setup in the monorepo
- Establishes patterns for other packages to follow
- Creates `src/lib/` directory structure for future utility modules

**Future Considerations (Out of Scope):**

- Story 2.1 will add jsdom environment for Ink component testing
- May add `@testing-library/react` when testing React components
- Consider `vitest-fail-on-console` for stricter testing (reference uses it)

**Risks:**

- Coverage path configuration must match between vitest.config.ts (`reportsDirectory: 'coverage'`) and CI artifact paths (`packages/bmad-dashboard/coverage/`)
- SHA-pinned actions in workflow need periodic updates for security patches
- First PR will have no base coverage to compare against (handled gracefully by `continue-on-error: true`)

## Review Notes

- Adversarial review completed
- Findings: 15 total, 4 fixed, 11 skipped (noise/uncertain/suggestions)
- Resolution approach: auto-fix

**Fixes Applied:**
- F1: Added `engines` field to root package.json for `node-version-file` compatibility
- F4: Extended test file pattern to include `.tsx` files
- F8: Created separate `tsconfig.test.json` to isolate vitest globals from production code
- F9: Pinned `vitest-coverage-report-action` to SHA for security
