---
description: Creates a branch (if needed), pushes changes, and opens a pull request with proper naming conventions
---

# Create Pull Request

**User-provided context:**
$ARGUMENTS

## Arguments

- `--ready` - Create PR as ready for review (not draft).
  Triggers CI immediately.

By default, PRs are created as **drafts** to conserve GitHub Action minutes during iteration.
Use `--ready` when confident the PR is ready for CI and review.

## Pre-flight Check and Current State (PARALLEL)

**Run these commands in parallel** (no dependencies between them):

```bash
git status --porcelain      # Check for uncommitted changes
git branch --show-current   # Determine current branch
```

**After both complete:**

- **If `git status --porcelain` shows changes: STOP.**
  - Report: "Cannot create PR - uncommitted or untracked changes detected"
  - List the files with changes
  - Do not proceed until changes are committed
- **If on main:** Proceed to branch creation.
- **If on another branch:** Skip to push step.

## Branch Creation (if on main)

### Fetch Latest Remote State

Always fetch before checking for divergence:

```bash
git fetch origin
```

### Check for Divergence (PARALLEL)

**Run both merge-base commands in parallel:**

```bash
git merge-base --is-ancestor origin/main HEAD && echo "AHEAD_OR_EQUAL"
git merge-base --is-ancestor HEAD origin/main && echo "BEHIND_OR_EQUAL"
```

**Interpretation:**

| Result               | Meaning                         | Action                      |
| -------------------- | ------------------------------- | --------------------------- |
| Both succeed         | HEAD and origin/main are equal  | STOP - nothing to PR        |
| First only (AHEAD)   | origin/main is ancestor of HEAD | Normal flow - create branch |
| Second only (BEHIND) | HEAD is ancestor of origin/main | STOP - fast-forward first   |
| Neither (DIVERGED)   | Branches have diverged          | Create branch, then rebase  |

### Handle Diverged Main

**If origin/main has commits not in local main:**

This happens when commits were merged to main remotely while you worked locally.
Local commits on main are always WIP intended for a PR, never direct pushes.

**Resolution:**

1. Create feature branch from current HEAD (preserving your work):

   ```bash
   git checkout -b <branch-name>
   ```

2. Rebase onto updated origin/main:

   ```bash
   git rebase origin/main
   ```

3. If rebase conflicts occur:
   - Analyze both sides of each conflict
   - Resolve automatically when intent is clear:
     - Changes to different logical sections
     - Additive changes that don't contradict
     - One side is clearly the "updated" version
   - After resolving, run `git add <file>` and `git rebase --continue`
   - Only STOP for user resolution when:
     - Both sides modify the same logic with different intent
     - Semantic conflict where correct resolution is ambiguous
     - Report what the conflict is and why it needs human judgment

4. After successful rebase, continue with push step

5. **If rebase fails completely** (too many conflicts, cannot resolve):
   - Abort rebase: `git rebase --abort`
   - Fall back to merge: `git merge origin/main`
   - Resolve merge conflicts if any
   - This preserves work but creates a merge commit
   - Report to user that merge was used instead of rebase

### Analyze Commits

Get commits that will be included:

```bash
git log origin/main..HEAD --oneline
```

**If no commits ahead of origin/main: STOP.**

- Report: "No commits to create PR from"
- Nothing to do

### Determine Branch Name

Use the `pull-request-conventions` skill for naming format.

Analyze the commits to determine:

1. **Type** - What kind of change? (`feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `build`, `ci`, `perf`, `style`)
2. **Description** - Brief summary of the change (2-4 words, hyphenated)

**Format:** `<type>/<description>`

**Examples based on commits:**

- "Add user authentication" → `feat/user-authentication`
- "Fix login validation bug" → `fix/login-validation`
- "Update API documentation" → `docs/api-updates`

### Create and Switch to Branch

```bash
git checkout -b <branch-name>
```

## Push to Remote

Check if branch is already pushed:

```bash
git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null
```

**If tracking branch exists:** Check if up to date.
**If no tracking branch:** Push with upstream:

```bash
git push -u origin <branch-name>
```

## Open GitHub Pull Request

### Check for Existing PR

```bash
gh pr list --head <branch-name> --json number,url --jq '.[0]'
```

**If PR already exists:**

- Report: "PR already exists: `url`"
- Return the existing PR URL
- Do not create a new one

### Derive PR Title

Reference the `pull-request-conventions` skill for title format.

**Derive from commits, not branch name.**
The branch name is a short handle that may have diverged from the actual changes.
Analyze the commits to determine the appropriate title.

**Process:**

1. Review commits: `git log origin/main..HEAD --oneline`
2. Identify the primary type of change (`feat`, `fix`, `refactor`, etc.)
3. Summarize what the changes accomplish
4. Add scope if changes are clearly scoped to a specific area

**Examples:**

- Commits add authentication → `feat(auth): add user authentication`
- Commits fix validation bug → `fix: resolve login validation error`
- Commits update docs → `docs(api): update endpoint documentation`
- Branch `feat/123-user-auth` with commits that add JWT → `feat(auth): add JWT-based authentication`

### Generate PR Description

Analyze commits to create description:

```bash
git log origin/main..HEAD --pretty=format:"- %s"
```

**Description format:**

```markdown
## Summary

<1-3 bullet points summarizing the changes>

## Test plan

<How to verify - infer from changes or use "Tested locally">
```

### Create the PR

**If `--ready` flag provided (create as ready for review):**

```bash
gh pr create --title "<title>" --body "$(cat <<'EOF'
## Summary
<bullet points>

## Test plan
<verification steps>
EOF
)"
```

**Otherwise (default - create as draft):**

```bash
gh pr create --draft --title "<title>" --body "$(cat <<'EOF'
## Summary
<bullet points>

## Test plan
<verification steps>
EOF
)"
```

## Output

After successful creation, report:

**For draft PRs:**

```text
Created draft PR #<number>: <title>
<url>

CI is skipped for draft PRs. When ready for CI and review:
- Run: /git:orchestrate --ready
- Or manually: gh pr ready <number>
```

**For ready PRs:**

```text
Created PR #<number>: <title>
<url>
```

## Edge Cases

### Branch Already Pushed, No PR

- Create PR for existing branch
- Use branch name for title derivation

### PR Creation Fails

Common failures:

1. **No commits** - "Pull request has no commits"
   - Verify commits exist between branch and main
2. **Auth issues** - Check `gh auth status`
3. **Repository permissions** - User may not have push access

Report the error clearly and stop.
