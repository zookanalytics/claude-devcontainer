---
description: Process PR review comments using parallel subagents for evaluation and implementation
allowed-tools: Bash(gh api:*), Bash(git branch:*), Glob, Grep, Read, Edit, Task
argument-hint: [PR number]
---

# Receiving Code Review

**User-provided context:** $ARGUMENTS

## Overview

Process review comments on a GitHub PR using **parallel subagent orchestration**.

Use Skill tool to load `superpowers:receiving-code-review` for evaluation criteria.

## Get Context (PARALLEL)

**If no PR number provided, run both queries in parallel:**

```bash
# Query 1: Get repository info
gh repo view --json owner,name --jq '{owner: .owner.login, repo: .name}'

# Query 2: Detect PR from current branch
gh pr list --head "$(git branch --show-current)" --json number --jq '.[0].number'
```

**If PR number is provided:** Only run Query 1 (repo info).

Use owner/repo values in all API calls below.

## Fetch Unresolved Threads

```bash
gh api graphql -f query='
  query($owner: String!, $repo: String!, $number: Int!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $number) {
        reviewThreads(first: 50) {
          nodes {
            id
            isResolved
            comments(first: 10) {
              nodes { id, author { login }, body, path, line }
            }
          }
        }
      }
    }
  }
' -f owner="$OWNER" -f repo="$REPO" -F number=$PR_NUMBER
```

Filter to `isResolved: false` only.

---

## Parallel Processing Architecture

### Phase 1: Parallel Evaluation

**Dispatch one Task per thread** with `subagent_type: "general-purpose"`:

```text
Evaluate review thread. Context: repo={owner}/{repo}, PR={number}, thread_id={id}, file={path}, line={line}.

Comment: <body>

Evaluation criteria (from receiving-code-review skill):
1. Technically correct for THIS codebase?
2. Breaks existing functionality?
3. Reason for current implementation?
4. Reviewer has full context?

Read the file. Categorize: implement|decline|escalate.

Return JSON only:
{"thread_id":"<id>","comment_id":"<comment_id>","category":"implement|decline|escalate","affected_files":["<path>"],"response":"<explanation>","fix":"<description or null>"}
```

**Launch ALL evaluation subagents in a single message** (parallel Task invocations).

### Phase 2: Group Results

| Category    | Action                               |
| ----------- | ------------------------------------ |
| `implement` | Check file overlap → dispatch fixes  |
| `decline`   | Reply + resolve (parallel API calls) |
| `escalate`  | Reply only, report to user           |

### Phase 3: Decline/Escalate (Parallel API Calls)

No subagents needed—just parallel `gh api` calls:

```bash
# Reply to comment thread
gh api repos/<owner>/<repo>/pulls/<pr>/comments \
  -f body="<response>" \
  -F in_reply_to=<comment_id>

# Resolve thread (decline only)
gh api graphql -f query='
  mutation($threadId: ID!) {
    resolveReviewThread(input: {threadId: $threadId}) {
      thread { isResolved }
    }
  }
' -f threadId="<thread_id>"
```

### Phase 4: Smart Implementation

**Group by file overlap:**

- Non-overlapping → parallel Task dispatch
- Overlapping → sequential within group

**Implementation subagent prompt:**

```text
Implement fix. Context: repo={owner}/{repo}, PR={number}, thread_id={id}, file={path}.

Feedback: <comment body>
Fix required: <description from evaluation>

Read file. Make ONLY the required change. Return JSON:
{"thread_id":"<id>","status":"fixed|failed","changes":"<description>","files":["<path>"]}
```

### Phase 5: Reply and Resolve Each Thread

After implementations complete, **for EVERY thread**:

1. **Reply directly to the thread** (not a standalone PR comment):

   ```bash
   gh api repos/<owner>/<repo>/pulls/<pr>/comments \
     -f body="<response>" \
     -F in_reply_to=<comment_id>
   ```

2. **Resolve the thread** (mark it closed in GitHub):
   ```bash
   gh api graphql -f query='
     mutation($threadId: ID!) {
       resolveReviewThread(input: {threadId: $threadId}) {
         thread { isResolved }
       }
     }
   ' -f threadId="<thread_id>"
   ```

**Response templates:**

- Fixed: "Fixed. {description of changes}"
- Declined: "Declined. {reasoning why current approach is correct}"
- Escalated: "Escalating. {why this needs human decision}"

### Phase 6: Verify All Threads Resolved

> **BLOCKING: Do NOT report completion until this passes.**

```bash
UNRESOLVED=$(gh api graphql -f query='
  query($owner: String!, $repo: String!, $pr: Int!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $pr) {
        reviewThreads(first: 100) {
          nodes { isResolved }
        }
      }
    }
  }
' -f owner="<owner>" -f repo="<repo>" -F pr=<number> \
  --jq '[.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false)] | length')

echo "Unresolved threads: $UNRESOLVED"
```

**If UNRESOLVED > 0:** Go back and resolve remaining threads before proceeding.

---

## Summary Report

```markdown
| #   | Comment | Response     | Status      |
| --- | ------- | ------------ | ----------- |
| 1   | desc    | what changed | ✓ Fixed     |
| 2   | desc    | reasoning    | ✓ Declined  |
| 3   | desc    | uncertainty  | Needs input |
```

---

## Rationalization Counters

**Do NOT skip parallelization because:**

| Excuse                         | Reality                                              |
| ------------------------------ | ---------------------------------------------------- |
| "Only 2 threads, not worth it" | Parallel dispatch has no overhead. Use it.           |
| "I'll evaluate as I go"        | Sequential = slower. Parallel evaluation first.      |
| "File overlap is complex"      | Simple set intersection. Check `affected_files`.     |
| "Subagents add latency"        | Parallel subagents are faster than sequential agent. |

**Do NOT skip thread processing because:**

| Excuse                             | Reality                                   |
| ---------------------------------- | ----------------------------------------- |
| "This one seems minor"             | Every comment deserves acknowledgment.    |
| "I'll batch similar ones"          | Each thread gets its own reply. No batch. |
| "Already addressed by another fix" | Still reply explaining this.              |

---

## Important Notes

- **Never skip threads** — every comment deserves acknowledgment
- **Reply directly to thread** — use `in_reply_to` parameter, not standalone comments
- **Resolve every thread** — unresolved threads block PR merge
- **Verify before claiming done** — run Phase 6 check, confirm 0 unresolved
- **Escalate honestly** — if uncertain, say so (but still resolve the thread)
- **Commit after implementing** — use `creating-commits` skill
- **Maximize parallelism** — only serialize for file overlap

> **Completion means UNRESOLVED = 0.**
> If any threads remain open, you have NOT completed this command.
