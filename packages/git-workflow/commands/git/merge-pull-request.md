---
description: Merges pull requests using squash merge with proper validation and cleanup
---

# Merge Pull Request

**User-provided context:**
$ARGUMENTS

## Determine PR Number

**If user provided a PR number in arguments:** Use that PR number.

**If no PR number provided:** Automatically determine from current branch:

```bash
git branch --show-current
gh pr list --head <branch-name> --json number --jq '.[0].number'
```

- If found: use that PR number
- If not found: "No PR found for branch `branch-name`"
- If multiple PRs: show list and ask user which one

## Pre-Merge Validation

**Use TodoWrite to create todos for EACH validation step.**

### Step 1: Gather All Data (PARALLEL)

**Run both queries in parallel** (no dependencies between them):

```bash
# Query 1: Get all PR data in one call (includes headRefName for branch)
gh pr view <number> --json number,title,body,statusCheckRollup,mergeable,headRefName

# Query 2: Get commit history for description verification
# Use PR branch name (headRefName) to ensure correct history regardless of current branch
git log origin/main..origin/<headRefName> --oneline
```

### Step 2: Verify PR Title

Reference the `pull-request-conventions` skill for title format.

**Check format:** `<type>[optional scope]: <description>`

The title becomes the squashed commit message on main.

### Step 3: Verify PR Description

**Foundational principle: Description must be 100% accurate.
No exceptions.**

Use the body from Step 1 and commit history from Step 1.

**If description mentions specific features, approaches, or code changes, verify with diff:**

```bash
gh pr diff <number>
```

Reference the `pull-request-conventions` skill for description requirements.

**Red flags that block merge:**

- Removed features: Description mentions "Added X" but X was removed
- Changed approaches: Description says "Using Y" but implementation uses Z
- Removed safeguards: Description claims safeguard that was removed
- Outdated code examples: Snippets don't match final implementation

**If ANY red flags found - DO NOT MERGE:**

1. Update description first:

```bash
gh pr edit <number> --body "$(cat <<'EOF'
## Summary
<corrected description reflecting actual changes>

## Test plan
<verification steps>
EOF
)"
```

2. Verify description is now accurate
3. Only then proceed to merge

### Step 4: Verify CI Checks

Use `statusCheckRollup` from Step 1.

**All checks must show one of:**

- `"conclusion": "SUCCESS"` and `"status": "COMPLETED"` (passed)
- `"conclusion": null` and `"status": "SKIPPED"` (legitimately skipped)

**If any checks show SKIPPED:** Verify it's intentional (conditional workflows, platform-specific tests).

**If any checks failed:**

- Flaky test: Rerun the check
- Real failure: **DO NOT MERGE**
  - If fix needs code changes: STOP, inform user
  - Never push unreviewed fixes to pass CI

### Step 5: Verify Mergeable Status

**CRITICAL:** GitHub computes mergeability asynchronously.
Always verify before merge.

Use `mergeable` from Step 1.

**Expected states:**

- `"mergeable": "MERGEABLE"` - Ready to merge
- `"mergeable": "CONFLICTING"` - Has conflicts, cannot merge
- `"mergeable": "UNKNOWN"` - GitHub still computing, must wait

**If status is UNKNOWN:**

GitHub hasn't computed mergeability yet.
This commonly happens after:

- Recent pushes to the PR branch
- Recent changes to the base branch
- PR just created or reopened

**Wait and retry (up to 3 attempts, 5 seconds apart):**

```bash
# Check status
gh pr view <number> --json mergeable --jq '.mergeable'

# If UNKNOWN, wait 5 seconds and check again
sleep 5
gh pr view <number> --json mergeable --jq '.mergeable'
```

**If still UNKNOWN after 3 attempts:**

- Inform user: "GitHub hasn't computed merge status yet.
  Try again in a moment."
- DO NOT attempt merge with UNKNOWN status.
  It will fail with misleading errors.

**If CONFLICTING:**

- Inform user: "PR has merge conflicts - needs resolution"
- User decides approach (rebase, merge main, manual resolution)

## Merge the PR

Always use squash merge:

```bash
gh pr merge <number> --squash
```

**Why squash merge:**

- Clean, linear history - one commit per PR on main
- PR title becomes commit message
- Individual commits preserved in closed PR if needed

## If Merge Fails

```bash
gh pr view <number> --json mergeable,mergeStateStatus
```

**Common failures:**

1. **Merge conflicts** - `"mergeable": "CONFLICTING"`
   - Inform user: "PR has merge conflicts - needs resolution"
   - User decides approach (rebase, merge main, manual resolution)
   - After resolved, return to Step 1

2. **Branch protection violations**
   - Check failed status checks, required reviews
   - Re-verify Step 4

3. **Insufficient permissions**
   - Inform user of permission issue

**DO NOT attempt to resolve merge failures without user input.**

## Post-Merge Cleanup

**After successful merge, IMMEDIATELY clean up:**

```bash
# 1. Verify merge succeeded
gh pr view <number> --json state,mergedAt

# 2. Switch to main and pull (sequential - must complete before cleanup)
git checkout main
git pull origin main

# 3. Clean up local and remote refs (PARALLEL - run both simultaneously)
git branch -D <branch-name>    # Delete local branch (-D required for squash merges)
git fetch --prune               # Prune stale remote-tracking references

# 4. Verify remote branch was deleted
git branch -r | grep <branch-name> || echo "Remote branch deleted"

# 5. Update session purpose to indicate completion
# First, read the current purpose
cat .claude-metadata.json | jq -r '.purpose'
# Then update with completion prefix
./scripts/claude-instance purpose "COMPLETED: <previous-purpose>"
```

**Note:** Read the current purpose from `.claude-metadata.json` first, then replace
`<previous-purpose>` in the command with the actual value.
This marks the session as having completed its primary objective.

**If remote branch still exists after verified merge: STOP.**

- This shouldn't happen (GitHub auto-deletes)
- Inform user: "Remote branch still exists - check GitHub PR page"
- May indicate repository settings issue

**Why cleanup immediately:**

- Prevents accidentally adding commits to merged branch
- Keeps local git clean
- "I'll clean up later" never happens

## Process Violations (Never Do These)

- Manually merge PR changes with `git merge` to main
- Cherry-pick commits from PR branch directly
- Copy code changes without closing the PR
- Leave PRs open after manually incorporating changes
- Merge with outdated description
- Push code changes to fix CI without re-review
- Skip branch cleanup after merge
- Continue working on branch after it's been merged

## Common Rationalizations (STOP)

If you think any of these, stop and follow the process:

| Thought                            | Reality                                                 |
| ---------------------------------- | ------------------------------------------------------- |
| "PR title is what matters"         | Description is permanent record. Both must be accurate. |
| "Description can be updated later" | Can't edit after merge. Do it now.                      |
| "Production urgency"               | 5 min now saves hours debugging later.                  |
| "It's probably fine"               | Run the commands. Takes 30 seconds.                     |
| "I'll clean up later"              | You won't. Cleanup now.                                 |
