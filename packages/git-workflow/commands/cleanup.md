---
allowed-tools: Bash(git status:--porcelain), Bash(git stash:list), Bash(git fetch:--all --prune), Bash(git branch:--show-current), Bash(git branch:-vv), Bash(git branch:--merged*), Bash(git branch:-d*), Bash(git branch:-D*), Bash(git merge-base:--is-ancestor*), Bash(git rev-list:*), Bash(gh pr list:*), Bash(gh pr view:*)
description: 'Syncs local repository with remote, cleans up merged branches, and reports status'
---

# Claude Command: Git Cleanup

Performs comprehensive git repository synchronization and cleanup while preserving local work.

## Usage

```claude
/git:cleanup
```

## Process

This command performs a safe sync and cleanup of your git repository by:

1. **Pre-flight checks (parallel)** - Check uncommitted changes and stash simultaneously
2. **Fetching and pruning** - Syncs with remote and removes stale references
3. **Categorizing branches (parallel)** - Check each branch's merge status concurrently
4. **Cleaning up merged branches** - Removes local branches that were merged/deleted remotely
5. **Preserving new work** - Keeps branches with commits not yet pushed
6. **Reporting status** - Provides clear summary of actions taken

### Steps 1-2: Pre-flight Checks (PARALLEL)

**Run these commands in parallel** (no dependencies between them):

```bash
git status --porcelain    # Check for uncommitted changes
git stash list            # Check for stashed changes
```

**After both complete:**

- If `git status --porcelain` shows changes: **STOP** and notify user concisely
  - Report what files/directories have changes
  - State that cleanup cannot proceed until changes are committed or stashed
  - Do NOT provide options or suggestions - just state the facts
- Count stash entries for final report (informational only)
- User should be made aware of forgotten stashed work

### Step 3: Fetch and Prune

Sync with remote and remove stale remote-tracking branches:

```bash
git fetch --all --prune
```

**What this does:**

- Downloads latest commits from all remotes
- Removes remote-tracking branches that no longer exist on remote
- Does not modify local branches or working tree

### Step 4: Identify Stale Branches

Find local branches whose remote counterparts are gone:

```bash
git branch -vv
```

**Analysis:**

- Parse output for branches marked `[origin/...: gone]`
- These are candidates for deletion (likely merged PRs)
- Extract branch names for review

### Step 5: Categorize Branches (PARALLEL)

For each candidate branch with `[origin/...: gone]`, determine if it's safe to delete.

**Understanding merged PRs:**

- When a PR is merged via GitHub (squash or rebase merge), the remote branch is deleted
- The local branch shows `[origin/branch-name: gone]`
- Squash/rebase merges create new commits, so the branch won't appear in `git branch --merged`
- Git ancestry checks (`git merge-base --is-ancestor`) don't work for squash merges
- We must check if a PR associated with the branch was merged on GitHub

**Parallel categorization strategy:**

```bash
# First, get shared context (run these in parallel):
git branch --show-current              # Current branch (protected)
git branch --merged origin/main        # All traditionally merged branches

# Then, for ALL candidate branches simultaneously, check GitHub PR status:
# Launch these in parallel - each is independent:
gh pr list --state merged --head BRANCH_1 --json number,title
gh pr list --state merged --head BRANCH_2 --json number,title
gh pr list --state merged --head BRANCH_3 --json number,title
# ... one call per candidate branch, ALL IN PARALLEL

# For branches with no merged PR, check unique commits (can also be parallel):
git rev-list origin/main..BRANCH_NAME --count
```

**Why parallel:** Each `gh pr list` call takes 1-2 seconds.
With 5 branches:

- Sequential: 5-10 seconds
- Parallel: 1-2 seconds total

**Categorization logic per branch:**

1. Skip if it's the current branch or main (protected)
2. Check if `gh pr list --state merged --head BRANCH` returns a PR → safe to delete
3. Check if branch appears in `git branch --merged origin/main` → safe to delete
4. Check `git rev-list origin/main..BRANCH --count`:
   - 0 = no unique commits → safe to delete
   - > 0 = has unpushed work → preserve

**Categories:**

- **Safe to delete**:
  - Branch has a merged PR on GitHub (primary indicator), OR
  - Branch appears in `git branch --merged origin/main` (traditional merge), OR
  - Branch has no unique commits compared to origin/main (empty branch)
- **Has new work**:
  - No merged PR found AND
  - Branch has commits not in origin/main AND
  - Branch not in merged list
- **Protected**:
  - Current branch (never delete)
  - Main branch (never delete)

### Step 6: Clean Up Safe Branches

Delete branches that are safe to remove:

```bash
# Use -d flag for safe deletion (will fail if truly unmerged)
git branch -d BRANCH_NAME

# If -d fails but we verified it's merged via PR:
# This WILL happen with squash/rebase merges
git branch -D BRANCH_NAME
```

**Deletion strategy:**

1. If branch has merged PR on GitHub:
   - Try `git branch -d` first (may succeed for traditional merges)
   - If fails, use `git branch -D` (expected for squash/rebase merges)
   - Safe because GitHub confirms the PR was merged
2. If branch appears in `git branch --merged origin/main`:
   - Use `git branch -d` (will succeed)
3. If branch has zero unique commits:
   - Use `git branch -d` (will succeed, branch is empty)
4. Otherwise:
   - Do NOT delete
   - Report to user as preserved branch with unpushed work

**Rules:**

- Only delete if `[origin/...: gone]` AND one of:
  - Has merged PR on GitHub (checked via `gh pr list`), OR
  - Appears in `git branch --merged origin/main`, OR
  - Has zero unique commits
- Use `-D` only when PR is confirmed merged but `-d` fails (squash/rebase case)
- Always protect current branch and main branch
- Report any branches that couldn't be safely categorized

### Step 7: Report Results

Provide comprehensive status report:

**If everything is clean:**

```text
✅ Repository is fully synced with remote

Summary:
- No uncommitted changes
- No stashed changes
- Deleted X merged branches: [list]
- All local branches are up to date
```

**If local work exists:**

```text
⚠️  Repository synced with local work preserved

Summary:
- Uncommitted changes: [files list]
  Action needed: Commit or stash these changes

- Stashed changes: X entries found
  Reminder: You have stashed work that may need attention
  Run 'git stash list' to review

- Deleted X merged branches: [list]

- Branches with unpushed work: [list]
  These branches were kept because they have commits not yet pushed to remote
```

## How Merged PR Detection Works

**The Challenge:**
When you merge a PR on GitHub using "Squash and merge" or "Rebase and merge", GitHub:

1. Creates new commit(s) on main with different SHAs
2. Deletes the remote branch
3. Your local branch shows `[origin/branch-name: gone]`
4. BUT `git branch --merged` won't show it as merged (different commit SHAs)
5. AND `git merge-base --is-ancestor` returns false (branch not in main's history)

**The Solution:**
This command uses a three-tiered approach to safely identify merged branches:

1. **GitHub PR Check** (`gh pr list --state merged --head BRANCH`)
   - **PRIMARY METHOD** - Checks if GitHub has a merged PR for this branch
   - Works perfectly for squash/rebase merges (the standard workflow)
   - Most reliable method because GitHub is the source of truth
   - Handles all merge strategies (squash, rebase, traditional merge)

2. **Traditional Merge Check** (`git branch --merged origin/main`)
   - Standard git merge detection
   - Works for traditional merge commits
   - Backup method if no PR found (direct commits to main)

3. **Unique Commit Count** (`git rev-list origin/main..BRANCH --count`)
   - Counts commits in branch not in main
   - If zero, branch adds nothing new (safe to delete)
   - Catches empty branches or work already cherry-picked

**Why git ancestry checks don't work:**

- `git merge-base --is-ancestor` checks if commits are in the history tree
- Squash merge creates a NEW commit, discarding the branch's commit history
- The branch's commits are never added to main's history
- Therefore ancestry check returns false even though changes were merged

**Result:** Branches from merged PRs are safely deleted even with GitHub's squash/rebase merge strategies by checking GitHub's PR state directly.

## Safety Features

- **Smart merge detection**: Properly identifies merged PRs even with squash/rebase merges
- **Ancestor verification**: Uses `git merge-base --is-ancestor` to confirm merges
- **Pre-flight checks**: Validates working tree before making changes
- **Conservative deletion**: Only removes branches confirmed safe through multiple checks
- **Protected branches**: Never deletes current branch or main
- **Clear reporting**: Always explains what was kept and why

## Error Handling

- **Dirty working tree**: Stop with concise message listing uncommitted changes only
- **Failed deletions**: Report which branches couldn't be deleted and why
- **Network issues**: Report fetch failures clearly
- **Protected branches**: Never attempt to delete main or current branch

## Output Style

**Concise error reporting:**

- State the blocker clearly and briefly
- List affected files/directories
- No suggestions, options, or explanations unless cleanup proceeds
- Example: "Cannot proceed - uncommitted changes detected: .claude/commands/git/"

## Example Output

```text
Checking for uncommitted changes...
✓ Working tree is clean

Checking stash...
✓ Found 2 stashed entries

Fetching from remote and pruning stale references...
✓ Synced with origin
✓ Pruned 5 stale remote-tracking branches

Analyzing local branches...
Found 4 branches with deleted remotes:
- feat/user-auth [gone] - checking merge status...
  ✓ Found merged PR #45 on GitHub (squash merged)
- fix/login-bug [gone] - checking merge status...
  ✓ Found in git merged branches (traditional merge)
- docs/update-readme [gone] - checking merge status...
  ✓ No unique commits (empty branch)
- feat/new-feature [gone] - checking merge status...
  ⚠️  No merged PR found, has 3 unique commits (preserving)

Cleaning up merged branches...
✓ Deleted feat/user-auth (merged PR #45)
✓ Deleted fix/login-bug (traditional merge)
✓ Deleted docs/update-readme (no unique commits)

✅ Repository cleanup complete

Summary:
- Deleted 3 merged branches
- Kept 1 branch with unpushed work: feat/new-feature (3 unique commits)
- Current branch 'main' is up to date with origin/main
- Stashed changes: 2 entries (run 'git stash list' to review)
```
