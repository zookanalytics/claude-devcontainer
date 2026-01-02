---
description: Orchestrates full PR workflow from local review through CI checks and external reviews to human sign-off readiness
---

# Orchestrate PR Workflow

**User-provided context:**
$ARGUMENTS

## Arguments

- `--ready` - Mark PR as ready for review and trigger CI.
  Without this flag, PRs remain as drafts.

By default, PRs are created and kept as **drafts** to conserve GitHub Action minutes during iteration.
Use `--ready` when confident the PR is ready for CI and review.

## Overview

This command orchestrates the complete pull request workflow as an **idempotent state machine**.
Run it multiple times - it detects current state and continues from where you left off.

**Phases (without --ready):** Self-Review → Draft PR Creation → Report (CI skipped)

**Phases (with --ready):** Self-Review → PR Creation → Mark Ready → CI + Copilot → External Feedback → Ready for Sign-off

**Key loop:** After addressing feedback, return to Phase 3 (CI + Copilot) for re-validation.

## State Detection

**Use TodoWrite to create a checklist tracking workflow progress.**

Example checklist items:

- Uncommitted changes addressed
- Commits ready
- Self-review completed
- PR opened
- CI and Copilot checks passed
- Feedback addressed
- Ready for sign-off

### Parallel State Detection

**Run these commands in parallel** (no dependencies between them):

```bash
# Group 1: Independent queries (run all in parallel)
git status --porcelain                    # Uncommitted changes
git branch --show-current                 # Current branch
git fetch origin                          # Fetch latest remote state
```

**After fetch completes**, run these in parallel:

```bash
# Group 2: Depends on fetch (run all in parallel)
git log origin/main..HEAD --oneline       # Commits ahead of main
git merge-base --is-ancestor origin/main HEAD && echo "AHEAD_OR_EQUAL"
git merge-base --is-ancestor HEAD origin/main && echo "BEHIND_OR_EQUAL"
# Interpretation: both succeed = EQUAL, first only = AHEAD, second only = BEHIND, neither = DIVERGED
```

**If on a feature branch**, also run:

```bash
# Group 3: PR status (run in parallel with Group 2 if branch known)
gh pr list --head <branch-name> --json number,state,isDraft --jq '.[0]'
gh pr view <number> --json statusCheckRollup,reviews,comments,isDraft  # If PR exists
```

**State determination:**

| Condition                                       | State            | Action                                |
| ----------------------------------------------- | ---------------- | ------------------------------------- |
| Uncommitted changes exist                       | `uncommitted`    | Run /git:commit, then continue        |
| No commits ahead of main                        | `nothing-to-do`  | STOP - nothing to review              |
| On main with commits, branches have diverged    | `needs-branch`   | Start at Phase 1                      |
| On feature branch, no PR exists                 | `needs-review`   | Start at Phase 1                      |
| PR exists, is draft, no `--ready` flag          | `draft`          | Self-review only, report draft status |
| PR exists, is draft, `--ready` flag provided    | `draft-ready`    | Mark ready, proceed to Phase 3        |
| PR exists, not draft, CI/Copilot pending        | `checks-pending` | Wait for CI and Copilot               |
| PR exists, not draft, CI failed                 | `ci-failed`      | Fix failures                          |
| PR exists, checks passed, unresolved threads    | `merge-blocked`  | Address ALL threads                   |
| PR exists, checks passed, no unresolved threads | `ready`          | Report completion                     |

> **CRITICAL:** The `merge-blocked` state means **unresolved review threads block the merge**.
> This is NOT about "requiring approving review" - it's about ALL review comments being resolved.
> GitHub branch protection rules require all Copilot (and other reviewer) threads to be resolved before merge is allowed.

### Validate Session Purpose

After state detection, validate the session purpose matches the work being orchestrated.

**Sources for purpose (in priority order):**

1. PR title (if PR exists) - e.g., "feat(app): add Automerge CRDT integration" → "Automerge CRDT Integration"
2. Branch name - e.g., `feat/automerge-crdt-integration` → "Automerge CRDT Integration"
3. First commit message summary

**Check and update:**

```bash
# Read current purpose
cat .claude-metadata.json 2>/dev/null | jq -r '.purpose // empty'

# If purpose is empty, stale, or doesn't match the work, update it
./scripts/claude-instance purpose "<derived-purpose>"
```

**Keep purpose broad** - describes the overall goal, not specific steps.
Examples:

- ✅ "Automerge CRDT Integration"
- ✅ "JWT Authentication"
- ❌ "Processing Copilot feedback" (too specific)
- ❌ "Phase 3 CI checks" (workflow step, not purpose)

### Handling `uncommitted` State

When uncommitted changes exist (staged or unstaged):

1. Run `/git:commit` to commit the changes
   - Follows the creating-commits skill workflow
   - Runs `pnpm fix`, analyzes staging, creates atomic commit
2. After successful commit, re-detect state and continue workflow
3. If commit fails (lint errors, user intervention needed), report and STOP

This allows orchestrate to take over from any working state - user doesn't need to
manually commit before running orchestrate.

### Handling `needs-branch` State

When on main with local commits and origin/main has diverged:

1. **Local commits on main are always WIP** - never intended to be pushed directly
2. **Proceed to Phase 1** (Self-Review) - review changes before creating PR
3. **Then Phase 2** (`/git:create-pull-request`) handles branch creation and rebase

The `needs-branch` state does NOT skip self-review.
Phase 2 will:

- Detect the divergence
- Create an appropriately named feature branch
- Rebase onto origin/main (or merge if rebase fails)
- Push and create the PR

### Handling `draft` State (no --ready flag)

When PR is draft and `--ready` flag not provided:

1. Run self-review (Phase 1 equivalent for existing PR)
2. Skip Phases 3-5 (CI wait, feedback, sign-off)
3. Report completion:

```text
Self-review complete. PR remains in draft mode.

PR: #<number> - <title>
URL: <url>

CI is skipped for draft PRs to conserve GitHub Action minutes.
When ready for CI and review:
- Run: /git:orchestrate --ready
- Or manually: gh pr ready <number>
```

**Rationale:** Allows frequent self-review cycles without burning CI minutes.

### Handling `draft-ready` State (--ready flag provided)

When PR is draft and `--ready` flag provided:

1. Run self-review (Phase 1 equivalent for existing PR)
2. Mark PR as ready: `gh pr ready <number>`
3. Proceed to Phase 3 (Wait for CI and Copilot)

## Phase 1: Local Self-Review

**Entry:** State is `needs-review` or `needs-branch` (committed but no PR yet)

**Goal:** Catch issues before external reviewers see them.

> **Use the slash command, not just a skill.**
> The `/superpowers:review-branch` command executes the full review workflow.
> **You MUST run the command.**

Run `/superpowers:review-branch` which will:

- Review all branch changes against main
- Identify code quality issues, bugs, missing tests
- Generate fixes for problems found

**Exit criteria:**

- All self-review issues addressed
- Changes committed (if any fixes made)
- Ready for PR creation

**Transition:** → Phase 2

## Phase 2: Create Pull Request

**Entry:** Self-review complete, no PR exists

**If `--ready` flag provided:**

Run `/git:create-pull-request --ready` to:

- Create feature branch if on main
- Push to remote
- Open PR as ready for review (not draft)

**Otherwise (default - create as draft):**

Run `/git:create-pull-request` to:

- Create feature branch if on main
- Push to remote
- Open PR as draft (CI skipped)

**Capture PR number and URL for tracking.**

**Transition:**

- If `--ready` flag: → Phase 3 (Wait for CI)
- If no `--ready` flag: → Report draft status and STOP

## Phase 3: Wait for CI and Copilot

**Entry:** PR exists, awaiting CI completion and Copilot review

### Detect Copilot Review Status

Use the timeline and requested_reviewers APIs to accurately detect Copilot status:

```bash
# Get Copilot events from timeline (review_requested and reviewed)
gh api repos/{owner}/{repo}/issues/{pr}/timeline --jq '
  [.[] | select(
    (.event == "review_requested" and .requested_reviewer.login == "Copilot") or
    (.event == "reviewed" and .user.login == "Copilot")
  )] | sort_by(if .event == "reviewed" then .submitted_at else .created_at end)'

# Check if Copilot is in pending reviewers
gh api repos/{owner}/{repo}/pulls/{pr}/requested_reviewers --jq '
  .users[] | select(.login == "Copilot")'
```

**Copilot Status Determination:**

| Condition                                       | Status        | Action              |
| ----------------------------------------------- | ------------- | ------------------- |
| Copilot in `requested_reviewers`                | In Progress   | Wait for completion |
| `review_requested` after latest `reviewed`      | Re-reviewing  | Wait for completion |
| `reviewed` exists, not in `requested_reviewers` | Complete      | Check for feedback  |
| No `review_requested` for Copilot               | Not Triggered | Wait up to 5 min    |

### Polling Strategy

Poll CI and Copilot status every 30 seconds:

1. **Get current PR state:**

   ```bash
   gh pr view <number> --json headRefOid,statusCheckRollup,reviews
   ```

2. **Check CI status:**
   - All checks `SUCCESS` or `SKIPPED` → CI passed
   - Any check `FAILURE` → CI failed
   - Otherwise → CI pending

3. **Check Copilot status** (using timeline + requested_reviewers as above)

> **Note:** `statusCheckRollup` contains `CheckRun` (.conclusion) and `StatusContext` (.state) - use `.conclusion // .state` to handle both.

**Timeouts:**

- Copilot triggered: 10 minutes from `review_requested` (typical: 30s-5min)
- Copilot not triggered: 5 minutes grace period to see if auto-triggered
- CI: No timeout (wait indefinitely)

**Decision Matrix:**

| CI Status  | Copilot Status   | Timeout? | Action                         |
| ---------- | ---------------- | -------- | ------------------------------ |
| ✅ Passed  | ✅ Complete      | Any      | → Phase 4 (check feedback)     |
| ✅ Passed  | ⏳ In Progress   | No       | Continue waiting               |
| ✅ Passed  | ⏳ In Progress   | Yes      | → Phase 4 (proceed anyway)     |
| ✅ Passed  | ❓ Not Triggered | < 5 min  | Wait for auto-trigger          |
| ✅ Passed  | ❓ Not Triggered | ≥ 5 min  | → Phase 4 (no review expected) |
| ⏳ Pending | Any              | Any      | Continue waiting for CI        |
| ❌ Failed  | Any              | Any      | → Handle CI Failure            |

**Exit:** CI passed AND (Copilot complete OR in-progress timeout OR not-triggered grace period)

**If Copilot in-progress timeout reached:**

- Report: "CI passed but Copilot hasn't completed after 10 minutes (unusual)"
- Offer to wait longer or proceed without Copilot review

**If Copilot never triggered:**

- After 5 minute grace period with no `review_requested` event
- Proceed to Phase 4 - no Copilot feedback expected
- Note: Auto-review may be disabled or not configured for this repo

### Handle CI Failure

1. Fetch failure logs: `gh run view <run-id> --log-failed`
2. Analyze root cause and fix the issue
3. Commit fix: `/git:commit`
4. Push: `git push`
5. → Restart Phase 3 (wait for new CI run)

**Retry limit:** 3 attempts per unique failure type.
After limit: STOP and report to user.

## Phase 4: Process External Feedback

**Entry:** CI passed and Copilot reviewed (or timeout)

### Check for Unresolved Threads

Query GitHub for unresolved review threads:

```bash
gh api graphql -f query='...' --jq '...' # See /git:receiving-code-review for full query
```

### If Unresolved Threads Exist

> **CRITICAL:** Unresolved threads block PR merges.
> You MUST resolve ALL threads before the PR can be merged.

Run `/git:receiving-code-review <pr-number>` to:

1. Fetch all unresolved review threads
2. Evaluate each using parallel subagents
3. Implement valid suggestions
4. Reply to AND resolve each thread
5. Generate summary report

See [/git:receiving-code-review](receiving-code-review.md) for complete workflow details.

**After command completes:**

1. Verify all threads resolved (command should do this, but double-check):

   ```bash
   gh api graphql ... | jq '[.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false)] | length'
   ```

2. If threads remain unresolved:
   - Re-run `/git:receiving-code-review` OR
   - Manually address remaining threads

3. Commit any changes: `/git:commit`

4. Push to update PR: `git push`

5. → Return to Phase 3 (wait for CI and Copilot to re-review)

**Common mistake:** Claiming work is "done" without verifying threads are resolved.
Check unresolved thread count FIRST before diagnosing merge blocks.

### If No Unresolved Threads

Proceed to Phase 5 (Ready for Sign-off).

## Phase 5: Ready for Sign-off

**Entry:** CI passing, all feedback addressed (or none received)

**Final verification:**

```bash
gh pr view <number> --json state,statusCheckRollup,reviews,mergeable
```

**Completion criteria:**

| Check              | Required                 |
| ------------------ | ------------------------ |
| PR state           | `OPEN`                   |
| All CI checks      | `SUCCESS` or `SKIPPED`   |
| Mergeable          | `MERGEABLE`              |
| Unresolved threads | 0 (or escalated to user) |

**Final Report:**

```markdown
## PR Ready for Sign-off

**PR:** #<number> - <title>
**URL:** <url>
**Branch:** <branch-name> → main

### Verification Complete

| Phase             | Status                      |
| ----------------- | --------------------------- |
| Self-Review       | ✓ Complete                  |
| CI + Copilot      | ✓ All passing               |
| External Feedback | ✓ Addressed / None received |

### Changes Summary

<1-3 sentence summary of what the PR accomplishes>

### Commits

<list of commits in PR>

### Escalated Items

<list any items that need human decision, or "None">

### Next Steps

Human review and approval, then:

- Merge: `/git:merge-pull-request`
```

## Iteration Limits

Prevent infinite loops:

| Limit           | Value              | On Exceed         |
| --------------- | ------------------ | ----------------- |
| CI fix attempts | 3 per failure type | Ask user          |
| Feedback cycles | 5 round-trips      | Ask user          |
| Copilot wait    | 10 minutes         | Proceed without   |
| CI wait         | None               | Wait indefinitely |

## Resume Capability

This command is **idempotent** - run it multiple times safely.

**On re-run:**

1. Detect current state (see State Detection)
2. Skip completed phases
3. Continue from current state
4. Preserve all previous work

**Example re-run scenarios:**

- "CI or Copilot pending" → Continue waiting from Phase 3
- "New comments appeared" → Process them in Phase 4
- "Everything green" → Report ready state

## Error Handling

### Merge Blocked

If PR merge fails, diagnose in priority order:

1. **Unresolved threads** (most common) → Return to Phase 4
2. **CI failing/pending** → Return to Phase 3 or fix failures
3. **Branch protection rules** → Check repository settings
4. **Merge conflicts** → Resolve conflicts with main

> **Common mistake:** Assuming "requires approving review" without checking unresolved threads first.
> Copilot review comments are the most common merge blocker.

### CI Repeatedly Fails

After 3 fix attempts for same failure:

```text
CI continues to fail after 3 fix attempts.

Failure: <check name>
Error: <error summary>

Options:
1. Show full error log
2. I'll investigate manually
3. Skip this check (not recommended)
```

### Cannot Address Feedback

If feedback requires architectural decisions:

- Escalate to user with context
- Do NOT guess or make assumptions
- Mark as "Needs Discussion" in report
- Continue with other actionable items

### API/Network Errors

- Retry transient errors (3 attempts with backoff)
- Report persistent failures clearly
- Preserve local state (never lose work)

## Key Principles

- **Idempotent** - Safe to run multiple times
- **State-aware** - Detects where you are, continues from there
- **Transparent** - Reports what it's doing and why
- **Escalates honestly** - Uncertain items need human judgment
- **Never blocks indefinitely** - Timeouts and user prompts prevent hangs
