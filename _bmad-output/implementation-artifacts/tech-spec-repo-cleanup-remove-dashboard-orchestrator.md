---
title: 'Repository Cleanup - Remove Dashboard and Orchestrator Packages'
slug: 'repo-cleanup-remove-dashboard-orchestrator'
created: '2026-01-20'
status: 'ready-for-dev'
stepsCompleted: [1, 2, 3, 4]
tech_stack: ['Node.js 22', 'pnpm workspaces', 'TypeScript', 'GitHub Actions', 'Docker', 'Husky', 'Commitlint']
files_to_delete:
  - 'packages/bmad-dashboard/'
  - 'packages/bmad-orchestrator/'
  - '_bmad-output/'
  - 'image/hooks/bmad-phase-complete.sh'
  - 'image/hooks/managed-settings.bmad.json'
  - 'docs/plans/bmad-*.md'
  - 'docs/plans/monorepo-migration-plan.md'
files_to_modify:
  - 'package.json'
  - 'image/Dockerfile'
  - 'image/scripts/assemble-managed-settings.sh'
  - '.github/workflows/tests.yml'
  - '.github/workflows/code-quality.yml'
  - '.github/workflows/publish.yml'
  - 'commitlint.config.mjs'
  - '.husky/pre-commit'
  - '.claude-plugin/marketplace.json'
  - 'docs/commit_specification.md'
  - 'docs/project-context.md'
  - 'docs/existing-documentation.md'
  - 'docs/project-parts.json'
  - 'docs/project-scan-report.json'
  - 'docs/plans/2026-01-18-devcontainer-feature-migration.md'
  - 'docs/index.md'
  - 'docs/architecture.md'
  - 'docs/development-guide.md'
  - 'docs/technology-stack.md'
  - 'docs/source-tree.md'
  - 'docs/project-structure.md'
code_patterns: ['pnpm workspace glob', 'conventional commits with scopes', 'GitHub Actions filters']
test_patterns: ['Vitest (bmad-dashboard only - being removed)']
---

# Tech-Spec: Repository Cleanup - Remove Dashboard and Orchestrator Packages

**Created:** 2026-01-20

## Overview

### Problem Statement

The repository evolved into a monorepo with packages (bmad-dashboard, bmad-orchestrator) that are no longer aligned with the project's focus on secure devcontainer and claude hooks. These packages and their associated planning artifacts need to be removed to refocus the repository.

### Solution

Systematically delete bmad-dashboard and bmad-orchestrator packages, all related planning artifacts in `_bmad-output/`, BMAD-specific hooks, and update all references across config files, CI workflows, and documentation. Keep claude-instance package for session purpose tracking functionality. Regenerate the lock file after package removal.

### Scope

**In Scope:**
- Delete `packages/bmad-dashboard/` directory
- Delete `packages/bmad-orchestrator/` directory
- Delete entire `_bmad-output/` directory (clean slate)
- Delete BMAD-specific hooks from `image/hooks/`
- Delete 6 obsolete BMAD planning docs from `docs/plans/`
- Update docs files with bmad-dashboard/bmad-orchestrator references
- Update config files: Dockerfile, CI workflows, commitlint, husky, marketplace.json
- Regenerate pnpm-lock.yaml

**Out of Scope (KEEP):**
- `packages/claude-instance/` - KEEP (session purpose tracking functionality needed for devpod work)
- `packages/git-workflow/` - KEEP unchanged
- `image/` directory structure - KEEP (update bmad-orchestrator references only)
- `.devcontainer/` - KEEP unchanged
- `.claude/` - KEEP unchanged
- Monorepo structure - KEEP (packages/* pattern remains)
- `docs/plans/2025-01-10-claude-devcontainer.md` - KEEP unchanged

## Context for Development

### Codebase Patterns

- **Workspace Config:** `pnpm-workspace.yaml` uses `packages/*` glob - no change needed
- **CI Workflows:** Reference packages by name in `--filter` flags and path triggers
- **Commit Scopes:** `commitlint.config.mjs` and `code-quality.yml` define valid scopes
- **Docker Image:** `Dockerfile` copies CLI tools from packages into container
- **Hooks:** `assemble-managed-settings.sh` has optional BMAD_ORCHESTRATOR module
- **git-workflow:** Uses claude-instance for session purpose tracking - unchanged

### Files to Reference

| File | Purpose | Action |
| ---- | ------- | ------ |
| `image/Dockerfile:196-199` | bmad-orchestrator COPY + RUN | Remove 4 lines (keep claude-instance) |
| `image/hooks/bmad-phase-complete.sh` | BMAD hook script | Delete file |
| `image/hooks/managed-settings.bmad.json` | BMAD hook config | Delete file |
| `image/scripts/assemble-managed-settings.sh` | Hook assembly | Remove line 8, lines 22-38 |
| `.github/workflows/tests.yml` | Runs bmad-dashboard tests | Replace with optimized placeholder |
| `.github/workflows/code-quality.yml:35-36` | PR title scopes validation | Remove 2 scopes (keep claude-instance) |
| `.github/workflows/code-quality.yml:55` | Lint filter | Replace with `- run: pnpm lint` |
| `.github/workflows/publish.yml:11` | Path trigger for bmad-orchestrator | Remove 1 line (keep claude-instance) |
| `commitlint.config.mjs` | Commit scope validation | Remove 2 scopes (keep claude-instance) |
| `.husky/pre-commit` | Git pre-commit hook | Change to `pnpm pre-commit` |
| `.claude-plugin/marketplace.json` | Plugin registry | Remove bmad-orchestrator entry only |
| `docs/commit_specification.md` | Scope documentation | Remove 2 scope rows |
| `docs/project-context.md` | Project overview | Remove BMAD Dashboard section |
| `docs/existing-documentation.md:36-45` | Doc index | Remove bmad-orchestrator section |
| `docs/project-parts.json` | Project parts | Remove bmad-orchestrator entry only |
| `docs/project-scan-report.json:47` | Scan report | Remove bmad-orchestrator entry only |
| `docs/plans/2026-01-18-devcontainer-feature-migration.md:354` | Migration plan | Remove bmad-cli reference (keep claude-instance) |

### Technical Decisions

- **Keep claude-instance:** Session purpose tracking functionality is needed for devpod work stream
- **Clean deletion approach:** Remove directories entirely rather than selective file removal
- **Delete all `_bmad-output/`:** User confirmed clean slate for planning artifacts
- **Keep monorepo structure:** `packages/*` pattern remains for remaining packages
- **CI workflow strategy:** Simplify tests.yml but preserve paths-ignore, draft PR check, and timeout
- **Pre-commit behavior:** Will run `pnpm lint` and `pnpm typecheck` recursively
- **Script simplification:** Keep assemble-managed-settings.sh for future extensibility, just remove BMAD logic

### Implementation Notes

**Line Number Handling:** When editing files with multiple changes, work from bottom-to-top (highest line numbers first) to prevent line shifts from affecting subsequent edits. Alternatively, use content-matching patterns rather than line numbers.

## Implementation Plan

### Tasks

**IMPORTANT:** Execute phases in order. Phase 5 (pnpm install) must run AFTER all deletions in Phases 1-4.

#### Phase 1: Delete Package Directories

- [ ] Task 1: Delete bmad-dashboard package
  - File: `packages/bmad-dashboard/`
  - Action: `rm -rf packages/bmad-dashboard`
  - Notes: Contains src, tests, config files - all removed

- [ ] Task 2: Delete bmad-orchestrator package
  - File: `packages/bmad-orchestrator/`
  - Action: `rm -rf packages/bmad-orchestrator`
  - Notes: Contains plugin.json, scripts, hooks - all removed

- [ ] Task 3: Delete planning artifacts
  - File: `_bmad-output/`
  - Action: `rm -rf _bmad-output`
  - Notes: All PRD, architecture, epics, sprint-status removed (clean slate)
  - **SELF-REFERENCE WARNING:** This tech-spec is located at `_bmad-output/implementation-artifacts/tech-spec-*.md` and will be deleted by this task. Before executing: either work from the plan in memory, keep a browser tab open with the spec, or copy key sections to clipboard. The spec should be fully understood before this deletion occurs.

- [ ] Task 4: Delete BMAD hook files
  - Files:
    - `image/hooks/bmad-phase-complete.sh`
    - `image/hooks/managed-settings.bmad.json`
  - Action: `rm image/hooks/bmad-phase-complete.sh image/hooks/managed-settings.bmad.json`
  - Notes: These are BMAD-specific hooks no longer needed. The Dockerfile's `COPY image/hooks/ /etc/claude-code/hooks/` will still work - it simply copies fewer files after deletion.

- [ ] Task 5: Delete obsolete planning docs
  - Files to DELETE:
    - `docs/plans/bmad-automation-proposal.md`
    - `docs/plans/bmad-build-vs-buy-analysis.md`
    - `docs/plans/bmad-completion-detection-research.md`
    - `docs/plans/bmad-filesystem-orchestration.md`
    - `docs/plans/bmad-orchestration-implementation-brief.md`
    - `docs/plans/monorepo-migration-plan.md`
  - Files to KEEP:
    - `docs/plans/2025-01-10-claude-devcontainer.md`
    - `docs/plans/2026-01-18-devcontainer-feature-migration.md` (update line 354)
  - Action: `rm docs/plans/bmad-*.md docs/plans/monorepo-migration-plan.md`

#### Phase 2: Update CI Workflows

- [ ] Task 6: Replace tests.yml workflow
  - File: `.github/workflows/tests.yml`
  - Action: Replace entire file with optimized placeholder:
    ```yaml
    name: Tests

    on:
      push:
        branches: [main]
        paths-ignore:
          - 'docs/**'
          - '.claude/**'
          - '*.md'
      pull_request:
        types: [opened, synchronize, reopened, ready_for_review]
        paths-ignore:
          - 'docs/**'
          - '.claude/**'
          - '*.md'

    jobs:
      test:
        runs-on: ubuntu-latest
        timeout-minutes: 15
        if: github.event.pull_request.draft == false || github.event_name == 'push'
        steps:
          - uses: actions/checkout@v4
          - uses: pnpm/action-setup@v4
          - uses: actions/setup-node@v4
            with:
              node-version-file: package.json
              cache: 'pnpm'
          - run: pnpm install --frozen-lockfile
          - run: pnpm test --if-present
    ```
  - Notes:
    - Removes `_bmad-output/**` from paths-ignore (this is safe because Task 3 deletes that directory - execute Phase 1 before Phase 2)
    - Removes coverage comparison infrastructure
    - Uses `--if-present` flag: After removing bmad-dashboard, remaining packages (git-workflow, claude-instance) have no test scripts. `--if-present` prevents failure when no tests exist.
    - Preserves: paths-ignore optimization, draft PR check, timeout

- [ ] Task 7: Update code-quality.yml scopes
  - File: `.github/workflows/code-quality.yml`
  - Action 1: Remove these lines from scopes list (around lines 35-36):
    ```yaml
    # DELETE THESE LINES:
              bmad-dashboard|
              bmad-orchestrator|
    ```
  - Action 2: Replace line 55 `- run: pnpm --filter bmad-dashboard check` with:
    ```yaml
          - run: pnpm lint
    ```
  - Notes: Keep claude-instance and remaining scopes

- [ ] Task 8: Update publish.yml path triggers
  - File: `.github/workflows/publish.yml`
  - Action: Remove line 11 only:
    ```yaml
    # DELETE THIS LINE:
      - 'packages/bmad-orchestrator/**'
    ```
  - Notes: Keep `image/**` and `packages/claude-instance/**` triggers

#### Phase 3: Update Config Files

- [ ] Task 9: Update Dockerfile
  - File: `image/Dockerfile`
  - **Current state (lines 195-199):**
    ```dockerfile
    COPY packages/claude-instance/bin/claude-instance /usr/local/bin/claude-instance
    COPY packages/bmad-orchestrator/scripts/ /usr/local/lib/bmad/
    RUN chmod 755 /usr/local/bin/claude-instance && \
      ln -s /usr/local/lib/bmad/bmad-cli /usr/local/bin/bmad-cli && \
      chmod 755 /usr/local/lib/bmad/bmad-cli
    ```
  - **Target state (lines 195-196):**
    ```dockerfile
    COPY packages/claude-instance/bin/claude-instance /usr/local/bin/claude-instance
    RUN chmod 755 /usr/local/bin/claude-instance
    ```
  - Action: Delete lines 196-199 entirely, then add single RUN line after line 195
  - Notes: Net change: 4 lines removed, 1 line added. Keep claude-instance COPY and chmod.

- [ ] Task 10: Update commitlint.config.mjs
  - File: `commitlint.config.mjs`
  - Action: Remove from scope-enum array:
    - `"bmad-dashboard"`
    - `"bmad-orchestrator"`
  - Notes: Keep claude-instance scope (8 scopes remaining)

- [ ] Task 11: Update husky pre-commit hook
  - File: `.husky/pre-commit`
  - Action: Replace entire file content:
    ```bash
    pnpm pre-commit
    ```
  - Notes: Root pre-commit runs `pnpm -r --if-present run lint && pnpm -r --if-present run typecheck`
  - **BEHAVIORAL CHANGE:** Previous hook only ran checks on bmad-dashboard (`cd packages/bmad-dashboard && pnpm pre-commit`). New hook runs lint/typecheck on ALL packages. This is intentional - ensures git-workflow and claude-instance are also validated on commit.

- [ ] Task 12: Update marketplace.json
  - File: `.claude-plugin/marketplace.json`
  - Action: Remove plugins array entry for `bmad-orchestrator` only
  - Notes: Keep `git-workflow` and `claude-instance` plugin entries

- [ ] Task 13: Simplify assemble-managed-settings.sh
  - File: `image/scripts/assemble-managed-settings.sh`
  - **Edit bottom-to-top to avoid line number shifts:**
  - Action 1: Remove lines 22-38 FIRST (entire BMAD if block)
  - Action 2: Then remove line 8 (ENABLE_BMAD_ORCHESTRATOR documentation comment)
  - Notes: Script becomes simpler - just copies base settings. Editing bottom-to-top prevents line shift issues.

- [ ] Task 14: Update root package.json test script
  - File: `package.json`
  - Action: Change line 14 from:
    ```json
    "test": "pnpm -r test",
    ```
    to:
    ```json
    "test": "pnpm -r --if-present test",
    ```
  - Notes: After removing bmad-dashboard, remaining packages have no test scripts. `--if-present` prevents `pnpm -r test` from failing when no package has a test script.

#### Phase 4: Update Documentation

- [ ] Task 15: Update commit_specification.md
  - File: `docs/commit_specification.md`
  - Action 1: Remove from Standardized Scopes table (lines 51-62):
    - Row: `| bmad-dashboard   | TUI dashboard package...`
    - Row: `| bmad-orchestrator| BMAD workflow automation...`
  - Action 2: Remove from Scope Selection Guidelines table (lines 66-77):
    - Row: `| packages/bmad-dashboard/                | bmad-dashboard   |`
    - Row: `| packages/bmad-orchestrator/             | bmad-orchestrator|`
  - Action 3: Update line 94 text from "10 standardized scopes" to "8 standardized scopes"
  - Notes: Scopes count changes from 10 to 8 (keeping claude-instance)

- [ ] Task 16: Update project-context.md
  - File: `docs/project-context.md`
  - Action 1: Remove entire "BMAD Dashboard Package" section (lines 132-226)
  - Action 2: Update Repository Structure to remove bmad-dashboard, bmad-orchestrator references (keep claude-instance)
  - Action 3: Update Commit Types & Scopes section to remove 2 scopes
  - Action 4: Update footer at line 230: Change "*Updated: 2026-01-04 with BMAD Dashboard patterns*" to remove "with BMAD Dashboard patterns" or update the date
  - Notes: Keep claude-instance references

- [ ] Task 17: Update existing-documentation.md
  - File: `docs/existing-documentation.md`
  - Action: Remove entire bmad-orchestrator section (lines 36-45)
  - Notes: This section documents files that are being deleted

- [ ] Task 18: Update project-parts.json
  - File: `docs/project-parts.json`
  - Action 1: Remove entire bmad-orchestrator entry from `parts` array (lines 77-101)
    - Search for: `"part_id": "bmad-orchestrator"` and remove the entire object including trailing comma
  - Action 2: Remove bmad-orchestrator from `integration_points` array (lines 110-115)
    - Search for: `"to": "bmad-orchestrator"` and remove that entire object
  - Notes: JSON array - ensure valid syntax after removal, keep claude-instance and git-workflow entries

- [ ] Task 19: Update project-scan-report.json
  - File: `docs/project-scan-report.json`
  - Action: Remove from project_types array (line 47):
    ```json
    {"part_id": "bmad-orchestrator", ...}
    ```
  - Notes: Keep claude-instance entry

- [ ] Task 20: Update devcontainer-feature-migration.md
  - File: `docs/plans/2026-01-18-devcontainer-feature-migration.md`
  - Action: Update lines 353-354 to remove BMAD references:
    - Line 353: Remove or update "BMAD-related hooks and settings assembly"
    - Line 354: Change to "CLI tools (claude-instance)" - remove bmad-cli
  - Notes: Keep claude-instance reference

- [ ] Task 21: Update remaining docs files
  - Files to review and update (remove bmad-dashboard/bmad-orchestrator references only):
  - **`docs/index.md`:** (177 lines total)
    - Line 31: Update "Claude Code plugins - Git workflow, instance management, BMAD automation" to remove "BMAD automation"
    - Line 57: Remove bmad-orchestrator row from Project Parts table
    - Lines 149-155: Remove bmad-orchestrator detailed section
    - Line 162: Remove broken `[BMAD Framework Documentation](_bmad/)` link (pre-existing broken link - `docs/_bmad/` doesn't exist)
  - **`docs/architecture.md`:**
    - Lines 185-188: Remove bmad-cli from "Embedded CLIs" diagram
    - Lines 194-202: Remove bmad-orchestrator from "Claude Code Plugins" diagram
    - Lines 216, 220-221: Remove bmad-orchestrator rows from Integration Points table
  - **`docs/development-guide.md`:**
    - Lines 43, 378-398: Remove bmad-orchestrator package references
  - **`docs/technology-stack.md`:**
    - Lines 137-158: Remove bmad-orchestrator technology entries
  - **`docs/source-tree.md`:**
    - Lines 157-214: Remove entire `packages/bmad-orchestrator` section
    - Lines 264-265: Remove bmad-orchestrator from "By Part" table
  - **`docs/project-structure.md`:**
    - Lines 67-79: Remove bmad-orchestrator from structure
    - Lines 130-138: Remove bmad-orchestrator references
  - Notes: Keep claude-instance and git-workflow references. Use content-matching (search for "bmad-orchestrator", "bmad-dashboard") rather than relying solely on line numbers.

#### Phase 5: Regenerate and Verify

**IMPORTANT:** Only run this phase AFTER all deletions and updates in Phases 1-4 are complete.

- [ ] Task 22: Regenerate pnpm-lock.yaml
  - Action: Run `pnpm install`
  - Notes: Lock file will regenerate without deleted packages

- [ ] Task 23: Verify pnpm test runs successfully
  - Action: Run `pnpm test --if-present`
  - Expected behavior: Command succeeds with exit code 0. Since remaining packages (git-workflow, claude-instance) have no test scripts, the `--if-present` flag causes pnpm to skip them gracefully rather than failing.
  - Notes: If any package adds tests later, they will run automatically.

- [ ] Task 24: Run verification commands
  - Action 1: Run `pnpm lint` to verify plugin validation passes
  - Action 2: Run `pnpm pre-commit` to verify hooks work
  - Action 3: Run grep to find remaining references:
    ```bash
    grep -r "bmad-dashboard\|bmad-orchestrator" \
      --include="*.yml" --include="*.yaml" --include="*.json" \
      --include="*.md" --include="*.mjs" --include="*.sh" \
      --include="*.ts" --include="*.py" --include="Dockerfile" \
      . | grep -v node_modules | grep -v pnpm-lock | grep -v ".git/"
    ```
  - Notes:
    - Should return no results after cleanup
    - NOT grepping for `claude-instance` (it's kept)
    - NOT grepping for generic `bmad` - only removing package-specific references. The `_bmad/` framework directory and general BMAD references in comments may remain (this is intentional - we're cleaning up packages, not all BMAD mentions)
    - pnpm-lock.yaml is excluded because Task 22 regenerates it fresh - it won't contain the old package references after `pnpm install`
  - **WARNING:** `pnpm lint` will fail if run during partial phase execution (after Phase 1 but before Task 12). This is expected - run only after all Phase 1-4 tasks complete.

- [ ] Task 25: Verify assemble-managed-settings.sh works
  - Action: Verify script syntax is valid: `bash -n image/scripts/assemble-managed-settings.sh`
  - Notes: Verify no BMAD references remain in script

- [ ] Task 26: Test Docker build
  - Action: Run `pnpm build:image`
  - Notes: Verify Dockerfile still builds with claude-instance

### Acceptance Criteria

- [ ] AC 1: Given packages deleted, when running `ls packages/`, then `git-workflow` and `claude-instance` directories exist

- [ ] AC 2: Given _bmad-output deleted, when running `ls _bmad-output/ 2>&1`, then "No such file or directory" error

- [ ] AC 3: Given config files updated, when running `pnpm install`, then no errors occur

- [ ] AC 4: Given commitlint updated, when running `echo "feat(bmad-dashboard): test" | pnpm commitlint`, then validation fails

- [ ] AC 5: Given commitlint updated, when running `echo "feat(claude-instance): test" | pnpm commitlint`, then validation passes

- [ ] AC 6: Given Dockerfile updated, when running `pnpm build:image`, then image builds successfully with claude-instance

- [ ] AC 7: Given all updates complete, when running grep from Task 24, then no bmad-dashboard/bmad-orchestrator references found

- [ ] AC 8: Given husky updated, when running `pnpm pre-commit`, then hook executes successfully

- [ ] AC 9: Given marketplace.json updated, when running `pnpm lint`, then plugin validation passes

- [ ] AC 10: Given BMAD hooks deleted, when running `ls image/hooks/bmad* 2>&1`, then "No such file" error

- [ ] AC 11: Given docs/plans cleaned, when running `ls docs/plans/`, then exactly these 2 files remain: `2025-01-10-claude-devcontainer.md` and `2026-01-18-devcontainer-feature-migration.md`

- [ ] AC 12: Given assemble-managed-settings.sh updated, when running `bash -n` syntax check, then no errors

## Additional Context

### Dependencies

- No external dependencies affected
- pnpm-lock.yaml will regenerate automatically after package deletion
- git-workflow depends on claude-instance (kept)
- Docker image build will work with claude-instance

### Testing Strategy

1. **Structural Verification:**
   - Verify `packages/git-workflow/` and `packages/claude-instance/` remain
   - Verify `packages/bmad-dashboard/` and `packages/bmad-orchestrator/` deleted
   - Verify `_bmad-output/` is deleted
   - Verify `image/hooks/bmad*` files are deleted
   - Verify `docs/plans/` has only 2 files

2. **Build Verification:**
   - `pnpm install` succeeds
   - `pnpm test --if-present` completes (exits 0, no tests run)
   - `pnpm lint` passes
   - `pnpm pre-commit` runs successfully
   - `pnpm build:image` succeeds (Docker with claude-instance)

3. **Reference Verification:**
   - Grep returns no matches for bmad-dashboard or bmad-orchestrator
   - claude-instance references are preserved
   - commitlint rejects old scopes, accepts claude-instance

4. **Script Verification:**
   - assemble-managed-settings.sh has valid syntax
   - No BMAD references remain in script

5. **CI Verification (post-merge):**
   - GitHub Actions workflows run without errors

### Notes

- **Decision:** Keep claude-instance for session purpose tracking - needed for parallel devpod work stream
- **Tradeoff:** tests.yml loses coverage infrastructure. Re-add when packages have tests.
- **Risk:** If any file is missed, CI or Docker build will fail - grep verification catches this.
- **Future:** Integrate claude-instance functionality into holistic devpod offering.
- **Future:** Consider updating repo description/README to reflect new focus.
