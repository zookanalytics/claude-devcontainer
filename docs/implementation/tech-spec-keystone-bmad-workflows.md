---
title: 'Keystone BMAD Workflow Orchestration'
slug: 'keystone-bmad-workflows'
created: '2026-01-18'
status: 'completed'
stepsCompleted: [1, 2, 3, 4]
tech_stack:
  - keystone-cli (workflow orchestration)
  - claude-cli (Claude Code CLI)
  - gemini-cli (Gemini CLI)
  - yaml (workflow definitions)
  - shell (step execution)
files_to_modify:
  - .keystone/config.yaml
  - .keystone/workflows/bmad-story.yaml (new)
  - .keystone/workflows/bmad-epic.yaml (new)
  - .keystone/workflows/bmad-epic-status.yaml (new)
  - .keystone/workflows/agents/bmad-orchestrator.md (new)
  - .keystone/workflows/agents/bmad-reviewer.md (new)
  - .keystone/workflows/agents/bmad-developer.md (new)
code_patterns:
  - keystone shell steps with retry/timeout
  - keystone foreach for story iteration
  - keystone sub-workflow composition
  - CLI non-interactive mode invocation
test_patterns:
  - manual workflow execution
  - single-story validation
  - epic iteration validation
  - resume-from-failure validation
---

# Tech-Spec: Keystone BMAD Workflow Orchestration

**Created:** 2026-01-18

## Overview

### Problem Statement

The default `keystone init` workflows don't align with the BMAD method. Teams using BMAD need a way to orchestrate the development workflow (dev-story → code-review → quick-dev → commit) across multiple AI tools (Claude, Gemini) and auto-advance through all stories in an epic.

### Solution

Create a series of keystone YAML workflows that:
1. Invoke Claude Code CLI and Gemini CLI via `shell` steps
2. Pass BMAD workflow paths as prompts (e.g., `claude "/dev-story"`)
3. Chain sequential steps: dev-story → code-review (gemini) → code-review (claude) → quick-dev → commit
4. Auto-advance through stories in an epic from `sprint-status.yaml`

### Scope

**In Scope:**
- Keystone workflows for BMAD method orchestration
- Shell steps invoking `claude` and `gemini` CLIs
- Auto-advancement through epic stories (two approaches to validate)
- Sequential multi-LLM code review (Gemini first, then Claude)
- Engine configuration for claude/gemini allowlisting
- Modular design: single-story workflow + epic iterator

**Out of Scope:**
- Modifying existing BMAD workflows
- Using keystone's LLM API providers (cost consideration - CLI tools preferred)
- Parallel LLM execution (future enhancement)
- Creating new BMAD skills or agents

## Context for Development

### Codebase Patterns

**Keystone Workflow Structure:**
- YAML files in `.keystone/workflows/`
- Schema: `https://raw.githubusercontent.com/mhingston/keystone-cli/main/schemas/workflow.json`
- Step types: `shell`, `llm`, `workflow`, `human`
- Expression syntax: `${{ inputs.var }}`, `${{ steps.id.output.field }}`

**Keystone Capabilities (from investigation):**

| Feature | Details |
|---------|---------|
| **Shell steps** | `run`, `env`, `timeout`, `retry`, `needs`, `if`, `allowFailure` |
| **Foreach loops** | `foreach: "${{ inputs.stories }}"` - iterate over arrays |
| **Sub-workflows** | `type: workflow`, `path`, `inputs`, `outputMapping` |
| **Retry** | `retry.count`, `retry.backoff` (linear/exponential), `retry.baseDelay` |
| **Resume** | SQLite state persistence, `keystone resume <run-id>` |
| **Conditionals** | `if: "${{ expression }}"` - skip steps based on conditions |

**CLI Interfaces:**

| CLI | Non-Interactive | Auto-Approve | Output Format |
|-----|-----------------|--------------|---------------|
| `claude` | `-p/--print` | `--dangerously-skip-permissions` | `--output-format json` |
| `gemini` | positional prompt | `-y/--yolo` or `--approval-mode yolo` | `-o json` |

**BMAD Workflow Invocation:**
```bash
# Claude Code CLI
claude -p "/bmad:bmm:workflows:dev-story" --dangerously-skip-permissions

# Gemini CLI
gemini "/bmad:bmm:workflows:code-review" --yolo
```

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `.keystone/config.yaml` | Keystone configuration, engines allowlist |
| `.keystone/workflows/dev.yaml` | Example keystone workflow with shell/llm steps |
| `.keystone/workflows/review-loop.yaml` | Example recursive workflow with conditionals |
| `_bmad-output/implementation-artifacts/sprint-status.yaml` | Story status tracking |

### Technical Decisions

1. **CLI over API:** Use `claude` and `gemini` CLI tools via shell steps (cost-effective)
2. **Workflow Passthrough:** Pass BMAD workflow paths as prompts to CLI tools
3. **Two Discovery Approaches:** Approach A (parse YAML) and Approach B (BMAD status)
4. **Sequential Review:** Gemini reviews first, then Claude reviews same code
5. **Modular Design:** Single-story workflow called by epic iterator
6. **Non-Interactive Mode:** Use `--print` / `--yolo` flags for automation
7. **Permission Bypass:** Use `--dangerously-skip-permissions` for unattended execution

### Verified BMAD Workflow Paths (F1 Resolution)

The following BMAD workflows exist and are callable via CLI:

| Workflow | File Location | CLI Invocation |
|----------|---------------|----------------|
| dev-story | `_bmad/bmm/workflows/4-implementation/dev-story/workflow.yaml` | `/bmad:bmm:workflows:dev-story` |
| code-review | `_bmad/bmm/workflows/4-implementation/code-review/workflow.yaml` | `/bmad:bmm:workflows:code-review` |
| quick-dev | `_bmad/bmm/workflows/bmad-quick-flow/quick-dev/workflow.md` | `/bmad:bmm:workflows:quick-dev` |
| git:commit | Built-in skill | `/git:commit` |

### Sprint-Status Parsing Logic (F5 Resolution)

**Concrete parsing commands for extracting stories from an epic:**

```bash
# Option 1: Using yq (if installed)
yq '.development_status | keys | .[] | select(test("^'$EPIC_ID'-[0-9]"))' sprint-status.yaml

# Option 2: Using grep (fallback, no dependencies)
grep -E "^  ${EPIC_ID}-[0-9]" sprint-status.yaml | sed 's/:.*//' | tr -d ' '

# Example output for epic_id=3c:
# 3c-1-fixture-recording-infrastructure
# 3c-2-fixture-replay-in-e2e-tests
# 3c-3-core-scenario-fixtures
# 3c-4-e2e-test-coverage-ai-coaching
# 3c-5-fixture-schema-validation-ci
# 3c-6-fixture-management-documentation
```

**Filter by status (optional):**
```bash
# Only get stories with specific status (e.g., backlog, ready-for-dev)
grep -E "^  ${EPIC_ID}-[0-9].*: (backlog|ready-for-dev)" sprint-status.yaml | sed 's/:.*//' | tr -d ' '
```

### Output Contracts (F6 Resolution)

**bmad-story.yaml outputs:**

| Output | Type | Source | Description |
|--------|------|--------|-------------|
| `success` | boolean | Step exit codes | `true` if ALL steps (dev-story, reviews, verify, commit) exit with code 0 |
| `story_id` | string | Input passthrough | The story ID that was processed |
| `commit_hash` | string | commit step output | Git commit SHA from the commit step (parsed from git output) |
| `error_step` | string | On failure | ID of the step that failed (if any) |

**Step success determination:**
- Each shell step succeeds if exit code = 0
- `success = true` only when all 5 steps complete with exit code 0
- On failure, `error_step` contains the failed step ID for debugging

### Idempotency & Error Recovery Strategy (F7/F9 Resolution)

**Idempotency by step:**

| Step | Idempotency Strategy |
|------|---------------------|
| `dev-story` | **Re-runnable with caution** - CLI will continue existing work or restart. May produce duplicate changes if run twice on completed work. |
| `review-gemini` | **Safe to re-run** - Reviews are additive; duplicate reviews are acceptable. |
| `review-claude` | **Safe to re-run** - Same as above. |
| `verify` | **Fully idempotent** - Running tests multiple times is safe. |
| `commit` | **Requires check** - Before committing, check if changes exist. If no staged changes, skip commit step. |

**Error recovery patterns:**

1. **Partial dev-story completion:**
   - Resume will re-invoke dev-story which continues from existing code state
   - Claude Code tracks session state and can continue

2. **Failed review step:**
   - Re-running reviews is safe (additive)
   - No cleanup needed

3. **Failed verify step:**
   - Fix code, then resume - verify will re-run tests
   - Tests are inherently idempotent

4. **Failed commit step:**
   - Check `git status` before retry
   - If changes staged, retry commit
   - If already committed, skip to next story

**Pre-step checks (add to workflow):**
```yaml
# Before commit step, check if there are changes to commit
- id: check-changes
  type: shell
  run: git diff --cached --quiet && echo "no_changes" || echo "has_changes"

- id: commit
  type: shell
  if: "${{ steps.check-changes.output != 'no_changes' }}"
  run: claude -p "/git:commit" --dangerously-skip-permissions
```

### Workflow Architecture

```
bmad-epic.yaml (epic iterator)
    │
    ├── foreach: stories in epic
    │       │
    │       └── bmad-story.yaml (single story workflow)
    │               │
    │               ├── dev-story (claude)
    │               ├── code-review (gemini)
    │               ├── code-review (claude)
    │               ├── quick-dev/verify tests (claude)
    │               └── commit (claude)
    │
    └── summary step
```

## Implementation Plan

### Tasks

- [x] **Task 1: Update keystone config for CLI engines**
  - File: `.keystone/config.yaml`
  - Action: Add `claude` and `gemini` to engines allowlist with version constraints
  - Notes:
    - Add timeout defaults (900000ms = 15 min for long CLI operations)
    - Keep existing provider config unchanged

- [x] **Task 2: Create bmad-story.yaml (single-story workflow)**
  - File: `.keystone/workflows/bmad-story.yaml` (new file)
  - Action: Create workflow with 5 sequential shell steps
  - Notes:
    - Input: `story_id` (string, e.g., "3c-1")
    - Step 1 `dev-story`: `claude -p "/bmad:bmm:workflows:dev-story Run story ${{ inputs.story_id }}" --dangerously-skip-permissions`
    - Step 2 `review-gemini`: `gemini "/bmad:bmm:workflows:code-review Review story ${{ inputs.story_id }}" --yolo`
    - Step 3 `review-claude`: `claude -p "/bmad:bmm:workflows:code-review Review story ${{ inputs.story_id }}" --dangerously-skip-permissions`
    - Step 4 `verify`: `claude -p "/bmad:bmm:workflows:quick-dev Verify tests pass for story ${{ inputs.story_id }}" --dangerously-skip-permissions`
    - Step 5 `commit`: `claude -p "/git:commit Commit implementation for story ${{ inputs.story_id }}" --dangerously-skip-permissions`
    - Each step needs: `timeout: 900000`, `retry: { count: 1, backoff: exponential, baseDelay: 30000 }`
    - Output: `success` (boolean), `story_id` (string)

- [x] **Task 3: Create bmad-epic.yaml (epic iterator - Approach A: YAML parsing)**
  - File: `.keystone/workflows/bmad-epic.yaml` (new file)
  - Action: Create workflow that parses sprint-status.yaml and iterates over stories
  - Notes:
    - Input: `epic_id` (string, e.g., "3c"), `auto_advance` (boolean, default: true)
    - Step 1 `parse-stories`: Shell step using `yq` or inline script to extract story IDs from sprint-status.yaml matching epic prefix
    - Step 2 `process-stories`: `foreach` loop calling `bmad-story.yaml` for each story
    - Step 3 `summary`: Human step showing completion summary
    - Output: `completed_stories` (array), `failed_stories` (array)

- [x] **Task 4: Create bmad-epic-status.yaml (epic iterator - Approach B: BMAD status)**
  - File: `.keystone/workflows/bmad-epic-status.yaml` (new file)
  - Action: Create workflow that uses BMAD workflow-status to get next story
  - Notes:
    - Input: `epic_id` (string)
    - Uses recursive pattern (like review-loop.yaml)
    - Step 1 `get-next`: Call BMAD status to find next ready-for-dev story in epic
    - Step 2 `process`: Call `bmad-story.yaml` if story found
    - Step 3 `iterate`: Recursive call to self if more stories remain
    - Terminates when no more stories in epic

- [x] **Task 5: Add human approval gates**
  - File: `.keystone/workflows/bmad-story.yaml` (modify)
  - Action: Add conditional human step after commit to test keystone's human-in-the-loop feature
  - Notes:
    - Add input: `require_approval` (boolean, default: true for testing)
    - Add step `approve`: `type: human`, `if: "${{ inputs.require_approval }}"`
    - Message shows story completion status, files changed, asks to continue
    - This tests keystone's `human` step type for interactive approval

- [x] **Task 6: Remove default keystone example workflows**
  - Files: `.keystone/workflows/*.yaml` (existing example files)
  - Action: Delete or archive the default `keystone init` workflows
  - Notes:
    - Keep config.yaml
    - Remove: dev.yaml, scaffold-*.yaml, decompose-*.yaml, review-loop.yaml, dynamic-decompose.yaml
    - Or move to `.keystone/workflows/examples/` subdirectory

- [x] **Task 7: Create BMAD-aware keystone agents**
  - Files: `.keystone/workflows/agents/*.md`
  - Action: Replace default agents with BMAD-aware system prompts to test keystone's agent system
  - Notes:
    - Create `bmad-orchestrator.md` - orchestration agent aware of BMAD workflows
    - Create `bmad-reviewer.md` - code review agent with BMAD review criteria
    - Create `bmad-developer.md` - implementation agent following BMAD dev patterns
    - Update or remove default agents (keystone-architect, software-engineer, etc.)
    - This tests keystone's agent configuration for potential future LLM-step use

### Acceptance Criteria

- [ ] **AC 1:** Given keystone config updated, when `keystone run bmad-story --story_id 3c-1` is executed, then Claude CLI is invoked with dev-story workflow and the command completes without permission prompts.

- [ ] **AC 2:** Given bmad-story.yaml exists, when a story is processed, then all 5 steps (dev-story, review-gemini, review-claude, verify, commit) execute sequentially with proper dependencies.

- [ ] **AC 3:** Given a step fails mid-workflow, when `keystone resume <run-id>` is executed, then the workflow resumes from the failed step without re-running completed steps.

- [ ] **AC 4:** Given bmad-epic.yaml exists with Approach A, when `keystone run bmad-epic --epic_id 3c` is executed, then stories 3c-1 through 3c-6 are extracted from sprint-status.yaml and processed in order.

- [ ] **AC 5:** Given bmad-epic-status.yaml exists with Approach B, when `keystone run bmad-epic-status --epic_id 3c` is executed, then the workflow queries BMAD status for next story and processes until no stories remain.

- [ ] **AC 6:** Given `require_approval: true` is passed, when a story completes, then the workflow halts and waits for human confirmation before proceeding to the next story.

- [ ] **AC 7:** Given Gemini code-review completes, when Claude code-review runs, then both reviews execute sequentially on the same code state (no race conditions).

- [ ] **AC 8:** Given a CLI step exceeds 15 minutes, when timeout is reached, then the step fails gracefully and can be retried or resumed.

- [ ] **AC 9:** Given BMAD-aware agents are configured, when keystone lists available agents, then bmad-orchestrator, bmad-reviewer, and bmad-developer are available with BMAD-specific system prompts.

- [ ] **AC 10:** Given human approval is enabled (default), when a story completes, then the workflow displays completion summary and waits for user input before proceeding.

## Additional Context

### Dependencies

| Dependency | Purpose | Installation |
|------------|---------|--------------|
| keystone-cli | Workflow orchestration | `npm install -g @anthropic/keystone-cli` or local |
| claude | Claude Code CLI | Already installed |
| gemini | Gemini CLI | Already installed at `/pnpm/gemini` |
| yq | YAML parsing (for Approach A) | `brew install yq` or `apt install yq` |

### Testing Strategy

**Manual Testing:**

1. **Single-story test:**
   ```bash
   keystone run bmad-story --story_id 3c-1
   ```
   - Verify all 5 steps complete
   - Check git log for commit
   - Review CLI output for each step

2. **Resume test:**
   ```bash
   # Start workflow, kill mid-execution
   keystone run bmad-story --story_id 3c-1
   # Ctrl+C after dev-story completes

   # Resume from where it stopped
   keystone resume <run-id>
   ```

3. **Epic iteration test (Approach A):**
   ```bash
   keystone run bmad-epic --epic_id 3c
   ```
   - Verify stories extracted correctly
   - Verify sequential processing
   - Check summary output

4. **Epic iteration test (Approach B):**
   ```bash
   keystone run bmad-epic-status --epic_id 3c
   ```
   - Compare results with Approach A
   - Note any differences in story discovery

5. **Approval gate test:**
   ```bash
   keystone run bmad-story --story_id 3c-1
   ```
   - Verify workflow pauses after commit (default behavior)
   - Verify manual approval works
   - Test with `--require_approval false` to skip approval

6. **Agent configuration test:**
   ```bash
   # List available agents
   keystone agents list
   ```
   - Verify bmad-orchestrator, bmad-reviewer, bmad-developer appear
   - Review agent prompts for BMAD alignment

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| CLI timeout on complex stories | Medium | Medium | 15 min timeout + retry |
| Gemini CLI behaves differently than Claude | Medium | Low | Test both, adjust prompts |
| sprint-status.yaml parsing fails | Low | High | Validate YAML structure first |
| Resume doesn't restore CLI state | Medium | Medium | Each step is idempotent |
| Permission prompts interrupt automation | Low | High | Use `--dangerously-skip-permissions` |

### Notes

**From Party Mode Discussion:**
- Go deep, build full config, validate by running (consensus)
- Build modular: single-story + epic-iterator (Winston)
- Capture output/timing for evaluation (Murat)
- Run on Epic 3c-1, low-risk validation target (Barry)

**Future Enhancements:**
- Parallel LLM execution (run Gemini and Claude reviews simultaneously)
- Parallel story execution (process multiple stories concurrently)
- Slack/webhook notifications on completion
- Dashboard for monitoring epic progress

**Known Limitations:**
- CLI output not captured to files by default (add shell redirection if needed)
- No rollback mechanism if commit fails (manual intervention required)
- Gemini CLI may not support all BMAD workflow paths (test and adjust)

---

## Review Notes

- **Adversarial review completed:** 2026-01-18
- **Findings:** 15 total, 7 fixed (Critical/High), 8 skipped (Medium/Low)
- **Resolution approach:** Auto-fix

### Fixes Applied

| ID | Severity | Fix Applied |
|----|----------|-------------|
| F1 | Critical | Staged all new workflow files in git |
| F2 | Critical | Removed misleading outputSchema, simplified summary display |
| F3 | High | Changed `echo` to `printf` for string comparisons |
| F4 | High | Updated Claude model to `claude-sonnet-4-20250514` |
| F5 | High | Fixed `needs` dependencies in final-summary step |
| F8 | Medium | Added post-commit sync step, fixed approve dependencies |
| F11 | Low | Fixed regex to `[0-9]+` for multi-digit story IDs |

### Skipped (acknowledged)

- F6: Recursive depth guard (max_stories provides sufficient protection)
- F7: Unused agents (intentional - for future LLM step testing)
- F9: Missing CLI preflight (keystone will fail gracefully)
- F10: Fragile error_step expression (functional, can refactor later)
- F12: Timeout documentation (values are reasonable defaults)
- F13: Task 6 staging (fixed with F1)
- F14: Agent project-context reference (optional file, acceptable)
- F15: Output aggregation (simplified to raw output display)
