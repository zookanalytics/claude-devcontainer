---
title: 'BMAD Orchestration Infrastructure Evaluation'
slug: 'bmad-orchestration-infrastructure-eval'
created: '2026-01-03'
completed: '2026-01-03'
status: 'completed-with-caveats'
stepsCompleted: [1, 2, 3, 4]
tech_stack:
  - Claude Agent SDK (CLI headless mode) - ADOPT
  - DevPod - COEXIST for container layer
  - Auto-Claude patterns - ADAPT for visualization
  - Minimal custom layer (~235 LOC estimated) - BUILD for state
files_to_modify:
  - packages/bmad-orchestrator/ (potential replacement/refactor)
  - packages/claude-instance/ (potential replacement)
code_patterns:
  - BMAD agent prompts from _bmad/bmm/agents/
  - File-based YAML state management (sprint-status.yaml, bmm-workflow-status.yaml)
test_patterns:
  - Integration tests for orchestration layer
  - State transition validation
  - Failure/retry scenario testing
review_notes:
  adversarial_review: completed
  findings_total: 15
  findings_fixed: 9
  findings_skipped: 6
  resolution_approach: auto-fix
  key_caveats:
    - LOC reduction claims are estimates (F3)
    - Quantitative baselines are theoretical (F10)
    - Dual-instance test not performed (F11)
    - CodeMachine rejected without hands-on test (F2)
    - Vendor lock-in risk accepted (~200 hours escape cost) (F15)
---

# Tech-Spec: BMAD Orchestration Infrastructure Evaluation

**Created:** 2026-01-03

## Overview

### Problem Statement

The current `bmad-orchestrator` and supporting scripts are accumulating complexity:
- **State management is unclear**: Where does official state reside? YAML files are scattered.
- **Job tracking is fragile**: Success/failure detection relies on signal files, exit codes, manual checking.
- **No visualization**: CLI output only - can't see workflow progress, bottlenecks, or agent handoffs.
- **Coordination overhead**: PTY subprocess approach with fragile parsing requires workaround after workaround.

We want to USE BMAD effectively, not BUILD infrastructure around it. If community tools can solve coordination, containers, and instances, we should adopt them. Our time should go to projects that use these tools, not building the plumbing.

### Solution

Evaluate community tools and frameworks that can provide orchestration infrastructure for BMAD workflows. The goal is to find the right balance of "adopt vs. build" - maximizing use of existing tools while ensuring compatibility with BMAD's methodology (agent prompts, YAML state, workflow patterns).

### Scope

**In Scope:**
- Evaluate orchestration tools for BMAD workflow compatibility
- Assess state management, job tracking, failure handling capabilities
- Evaluate visualization options (must-have vs nice-to-have TBD)
- Research container/instance management tools (DevPod, ClaudeBox)
- Produce clear recommendation: adopt X, adapt patterns from Y, or build minimal custom layer

**Out of Scope:**
- Changing BMAD methodology or workflow structure
- Full implementation (this is evaluation/research only)
- Replacing BMAD agent prompts with alternative methodologies

## Context for Development

### Current Pain Points (from Party Mode Discussion)

| Pain Point | Current State | What "Good" Looks Like |
|------------|---------------|------------------------|
| **State Location** | YAML files scattered, unclear source of truth | Single authoritative state with clear ownership |
| **Job Tracking** | Signal files, exit codes, manual checking | Clear success/failure per job, history, retry capability |
| **Visualization** | None - CLI output only | See workflow progress, bottlenecks, agent handoffs |
| **Coordination** | PTY subprocess, fragile parsing | Reliable agent-to-agent handoffs with context passing |

### Infrastructure Decomposition

```
┌─────────────────────────────────────────────────────────┐
│                    BMAD METHODOLOGY                      │
│        (Agents, Workflows, YAML State - KEEPS)          │
└─────────────────────────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
   │  INSTANCE   │ │ MULTI-AGENT │ │  CONTAINER  │
   │ MANAGEMENT  │ │COORDINATION │ │  LIFECYCLE  │
   │             │ │             │ │             │
   │ claude-     │ │ bmad-       │ │ devcontainer│
   │ instance    │ │orchestrator │ │ management  │
   └─────────────┘ └─────────────┘ └─────────────┘
```

Each layer may have a different "adopt vs build" answer.

### Codebase Patterns

**Current Architecture (~4200 LOC total):**

```
┌────────────────────────────────────────────────────────────────────────┐
│                          HOST MACHINE                                   │
│                                                                         │
│  claude-instance (bash, 1700 LOC)                                       │
│  ├─ create/list/remove/open/browse                                      │
│  ├─ dashboard/attach/menu (tmux-based terminal sharing)                 │
│  └─ run (dispatch command to container)                                 │
│                                                                         │
│  bmad-cli (Python, ~2500 LOC total)                                     │
│  ├─ status.py (270 LOC) - YAML parsing, priority logic                  │
│  ├─ executor.py (545 LOC) - PTY spawn, signal file watching             │
│  └─ cli.py (1730 LOC) - menu, dispatch, audit, restart                  │
└────────────────────────────────────────────────────────────────────────┘
                              │
                              │ dispatch via subprocess
                              ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        DEVCONTAINER                                     │
│                                                                         │
│  Claude Code (invoked via PTY)                                          │
│  └─ BMAD Skills: /{skill} for story {story_id}                          │
│                                                                         │
│  State Files:                                                           │
│  ├─ _bmad-output/implementation-artifacts/sprint-status.yaml            │
│  ├─ .claude-metadata.json (instance purpose)                            │
│  ├─ .claude/.bmad-dispatched.json (dispatch tracking)                   │
│  ├─ .claude/.bmad-running/*.json (lock files)                           │
│  └─ .claude/.bmad-phase-signal.json (phase completion signal)           │
└────────────────────────────────────────────────────────────────────────┘
```

**BMAD Agent Prompt Pattern:**
```xml
<agent id="analyst.agent.yaml" name="Mary" title="Business Analyst">
  <activation>
    <step n="1">Load persona from agent file</step>
    <step n="2">Load config.yaml, store variables</step>
    <step n="3">Show greeting, display menu</step>
    <step n="4">Wait for user input</step>
  </activation>
  <persona>
    <role>Strategic Business Analyst</role>
    <communication_style>...</communication_style>
  </persona>
  <menu>
    <item cmd="PB" exec="workflow.md">[PB] Create Product Brief</item>
  </menu>
  <menu-handlers>
    <handler type="workflow">Load workflow.xml, pass yaml path</handler>
    <handler type="exec">Load and execute file at path</handler>
  </menu-handlers>
</agent>
```

**Story Lifecycle & Priority:**
```
Priority Order: in-progress > review > ready-for-dev > backlog

backlog ──────────────────→ ready-for-dev ──→ in-progress ──→ review ──→ done
   │                             │                │              │
   │ create-story workflow       │                │              │
   └─────────────────────────────┘                │              │
                                  dev-story       │              │
                                  workflow ───────┘              │
                                                   code-review   │
                                                   workflow ─────┘
```

**Current State Tracking Mechanism:**
1. `sprint-status.yaml`: Source of truth for story/epic statuses
2. `.bmad-dispatched.json`: Tracks which story is running on which instance
3. `.bmad-running/*.json`: Lock files with PID, action, starting_status
4. `.bmad-phase-signal.json`: Signal file for phase completion (workaround for PTY limitations)
5. Stop hook (`stop-on-phase-complete.sh`): Watches for signal file, kills Claude when phase done

**Key Integration Points (any replacement must handle):**
1. Read/update `sprint-status.yaml` (YAML with simple structure)
2. Invoke Claude Code with BMAD skill: `claude -p "/{skill} for story {story_id}"`
3. Detect phase completion (story status transitions)
4. Track success/failure per phase
5. Support retry/restart from any phase
6. Work across multiple devcontainer instances

### Files to Reference

| File | Purpose | LOC |
| ---- | ------- | --- |
| `packages/bmad-orchestrator/scripts/bmad/executor.py` | PTY-based execution, signal file watching | 545 |
| `packages/bmad-orchestrator/scripts/bmad/status.py` | YAML state parsing, priority logic | 270 |
| `packages/bmad-orchestrator/scripts/bmad/cli.py` | Full CLI: menu, dispatch, audit, restart | 1730 |
| `packages/claude-instance/bin/claude-instance` | Instance management, tmux dashboard | 1673 |
| `_bmad/bmm/agents/*.md` | BMAD agent prompts (analyst, architect, dev, etc.) | ~100 each |
| `_bmad-output/implementation-artifacts/sprint-status.yaml` | Story/epic status tracking | varies |
| `.claude/.bmad-dispatched.json` | Dispatch tracking (story → instance mapping) | varies |

### Technical Decisions (Pending Evaluation)

- **Orchestration Approach**: TBD - adopt framework vs. minimal custom layer
- **State Management**: Must work with BMAD's YAML files (non-negotiable)
- **Visualization**: Evaluate if must-have or nice-to-have for first iteration
- **Claude Code Integration**: Must be able to invoke Claude Code with BMAD skills

## Tools to Evaluate

### Category 1: AI Agent Orchestration Frameworks

| Tool | Key Features | BMAD Fit Notes |
|------|--------------|----------------|
| [LangGraph](https://langchain.com/langgraph) | Graph-based workflows, LangGraph Studio visualization, fastest performance | Need to evaluate if can wrap Claude Code CLI |
| [CrewAI](https://crewai.com) | Role-based teams (matches BMAD agents!), Crews + Flows dual model | Role model similar to BMAD, but has own methodology |
| [n8n](https://n8n.io) | Visual workflow builder, 1000+ integrations, self-hostable | Good visualization, but AI orchestration is secondary |
| [AutoGen](https://microsoft.github.io/autogen/) | Multi-agent conversations, planner-executor-critic loops | MS backing, but conversation-centric vs workflow-centric |
| [Agno](https://agno.dev) | Lightweight, fast (50x less memory than LangGraph), microsecond agent spawn | Performance-focused, evaluate for minimal overhead |
| [MARSYS](https://github.com/rezaho/MARSYS) | 7 topology patterns (hub-spoke, pipeline, mesh), parallel execution, human-in-loop, state persistence | Python, supports Claude via Anthropic API, topology patterns match BMAD workflow patterns |

### Category 2: Claude Code Specific Tools

| Tool | Key Features | BMAD Fit Notes |
|------|--------------|----------------|
| [Claude Agent SDK](https://docs.anthropic.com/claude-code/sdk) | Official SDK, headless mode, subagents, hooks | Direct integration, TypeScript/Python SDKs |
| [Auto-Claude](https://github.com/AndyMik90/Auto-Claude) | Kanban UI, parallel agents, Memory Layer, git worktrees | Great visualization but own methodology - inspiration source |
| [CodeMachine-CLI](https://github.com/moazbuilds/CodeMachine-CLI) | Multi-agent orchestration, supports Claude Code, parallel execution | Spec-to-code pipeline, claims 25-37x faster |
| [ClaudeBox](https://github.com/RchGrav/claudebox) | Containerized Claude Code with profiles | Instance management focus |
| [zhsama/claude-sub-agent](https://github.com/zhsama/claude-sub-agent) | Nearly identical to BMAD agent pattern | Quality gates between stages - close match |
| [Nimbalyst](https://nimbalyst.com/) | WYSIWYG editor, session manager for Claude Code | Session management, probably not orchestration focused |

### Category 3: Container/Instance Management

| Tool | Key Features | BMAD Fit Notes |
|------|--------------|----------------|
| [DevPod](https://devpod.sh) | Open-source, devcontainer.json compatible, full lifecycle | Strong candidate for container management |
| ClaudeBox | Profiles, containerized Claude Code | Evaluate overlap with DevPod |

### Category 4: Workflow Engines (Reference/Patterns)

| Tool | Key Features | BMAD Fit Notes |
|------|--------------|----------------|
| [Temporal](https://temporal.io) | Durable execution, workflow-as-code, great debugging | Enterprise-grade, may be overkill |
| [Prefect](https://prefect.io) | Python-native, good UI, cloud or self-hosted | Data pipeline focus but patterns apply |

## Evaluation Criteria

### Scoring Matrix

| Criteria | Weight | Min Pass | Question |
|----------|--------|----------|----------|
| **BMAD Compatibility** | 10x | 4/5 | Can it use our agent .md files and YAML state? |
| **Claude Code Integration** | 10x | 4/5 | Can it invoke Claude Code CLI (not just API)? |
| **State Externalization** | 5x | 3/5 | Can state remain git-trackable (YAML/JSON files OR exportable)? |
| **Failure Semantics** | 5x | 3/5 | Retry, skip, manual intervention - how configurable? |
| **Visualization** | 2x | 2/5 | Built-in? Pluggable? None? (deferred to post-eval) |
| **Maintenance Burden** | 5x | 3/5 | Active community (2+ maintainers, 10+ commits/90 days)? |
| **Escape Hatch** | 2x | 2/5 | Migration cost <40 hours if tool abandoned? |

**Scoring Guide:**
- 5 = Fully meets requirement, no workarounds needed
- 4 = Meets requirement with minor configuration
- 3 = Partially meets, requires wrapper code (<100 LOC)
- 2 = Significant gaps, requires substantial custom code
- 1 = Does not meet requirement

### Evaluation Success Criteria

**Tool Adoption Threshold:**
- All 10x criteria (BMAD Compatibility, Claude Code Integration) must score **4+**
- Weighted average across all criteria must be **≥3.5**
- No single criterion can score **1** (hard fail)

**Tie-Breaking Rules:**
1. Higher score on 10x criteria wins
2. If tied, prefer tool with lower maintenance burden
3. If still tied, prefer tool with better escape hatch

**Failure Threshold:**
- If no tool meets adoption threshold by Day 5, default to "build minimal custom" recommendation
- If multiple tools tie after Day 7, select the one with best Claude Code Integration score

**State Externalization Clarification:**
The requirement is **git-trackable state**, not necessarily raw YAML:
- ✅ Direct YAML/JSON file read/write
- ✅ Framework state that exports to YAML/JSON on demand
- ✅ SQLite with human-readable schema (can diff via dump)
- ❌ Proprietary binary format
- ❌ Cloud-only state store with no local export

## Implementation Plan

### Time Constraints

| Phase | Target Duration | Decision Point |
|-------|-----------------|----------------|
| **Phase 1** | 3-5 days | Day 5: If no tool scores 4+ on critical criteria → build custom |
| **Phase 2** | 2-3 days | Day 8: Prototype must demonstrate 1 complete workflow |
| **Phase 3** | 1 day | Day 9: Final recommendation documented |
| **Total** | ≤10 working days | Day 10: Hard stop, decision required |

**Decision Rules:**
- Day 5: If primary candidates (SDK, CodeMachine) both fail → skip Phase 2, write "build custom" recommendation
- Day 7: If prototype not working → abandon and document learnings
- Day 10: Whatever state we're in, write final recommendation

### Standard Test Harness

All tool evaluations use identical test scenarios for reproducibility.

#### Test Fixtures Setup

Create these files before starting evaluation:

**File 1:** `_bmad-output/test-fixtures/sprint-status-baseline.yaml`
```yaml
# Baseline state - copy to sprint-status.yaml before each test
epics:
  - id: E999
    title: "Test Epic"
    status: in-progress
stories:
  - id: S999
    title: "Test Story for Orchestration Evaluation"
    status: ready-for-dev
    epic: E999
```

**File 2:** `_bmad-output/test-fixtures/expected-after-invocation.yaml`
```yaml
# Expected state AFTER successful skill invocation
epics:
  - id: E999
    title: "Test Epic"
    status: in-progress
stories:
  - id: S999
    title: "Test Story for Orchestration Evaluation"
    status: in-progress  # Changed from ready-for-dev
    epic: E999
```

#### Test Skill

**Skill:** `/bmad:bmm:workflows:workflow-status`

**Valid Output Example:**
```json
{
  "status": "success",
  "stories": {
    "total": 1,
    "ready-for-dev": 0,
    "in-progress": 1,
    "review": 0,
    "done": 0
  }
}
```

#### Expected Outcomes (Concrete)

| Test | Setup | Action | Pass Criteria |
|------|-------|--------|---------------|
| **Skill invocation** | Copy baseline.yaml → sprint-status.yaml | Run `/{skill}` | Exit code 0 AND output matches JSON schema above |
| **State read** | Use baseline.yaml | Read sprint-status.yaml | Returns: stories.total=1, stories.ready-for-dev=1 |
| **State write** | Use baseline.yaml | Update S999 to in-progress | `git diff` shows exactly: `- status: ready-for-dev` → `+ status: in-progress` |
| **Failure recovery** | Start invocation, SIGKILL after 2s | Retry invocation | State preserved (in-progress), second run completes |

### Phase 1: Research Deep-Dives (Priority Order)

#### Task 0.1: Verify Claude SDK Documentation (Prerequisite)
- [ ] **Verify**: Confirm SDK docs exist and cover required features
  - URL: https://docs.anthropic.com/en/docs/claude-code/sdk
  - Required features: headless mode, subagents, hooks, programmatic invocation
  - If docs missing/sparse: Escalate to user, consider promoting CodeMachine to Task 1.1
  - Notes: Do NOT proceed with Task 1.1 until this is verified

#### Task 0.2: Draft Fallback Architecture (Day 0 - 4 hours)

If all tool evaluations fail, we need a ready-to-go "build minimal custom" architecture.

- [ ] **Draft**: Minimal custom orchestration architecture
  - File: `_bmad-output/planning-artifacts/architecture/orchestration-minimal-fallback.md` (create)
  - Scope: Assume NO external tools meet criteria
  - Components:
    - **Event Bus**: Simple pub/sub for state changes (Node.js EventEmitter or similar)
    - **YAML State Manager**: Atomic read/write with file locking
    - **Subprocess Wrapper**: Claude Code invocation with JSON output parsing
    - **Retry Logic**: Basic exponential backoff (3 attempts, 1s/2s/4s delays)
  - LOC Target: <500 lines total
  - Purpose: This becomes the Day 10 fallback if all evaluations fail

**Why before Phase 1:** Having this ready ensures Day 10 has a concrete decision, not just "write something." If we reach Day 10 with no viable tool, we immediately know what to build.

#### Task 1.1: Evaluate Claude Agent SDK (Highest Priority - Day 1-2)
- [ ] **Research**: Read official SDK documentation for TypeScript and Python
  - File: `_bmad-output/planning-artifacts/research/claude-agent-sdk-eval.md` (create)
  - Action: Document headless mode, subagent pattern, hooks, state handling
  - Reference: Use SDK docs verified in Task 0.1
  - Notes: This is the official path - evaluate first before third-party tools

- [ ] **Hands-on Test**: Create minimal orchestrator using SDK
  - File: `packages/bmad-orchestrator/spike/sdk-test/` (create directory)
  - Action: Invoke Claude Code with standard test harness (see above)
  - Test: `/bmad:bmm:workflows:workflow-status` with test-story-S999.yaml
  - Notes: Must pass all 4 expected outcomes from test harness

- [ ] **Evaluate**: Score against criteria matrix
  - BMAD Compatibility: Can it pass BMAD prompts?
  - State Externalization: Can we use our YAML files?
  - Failure Semantics: How does it handle skill failures?
  - Document scores with rationale in eval.md

#### Task 1.2: Evaluate CodeMachine-CLI (High Priority - Day 2-3)
- [ ] **Research**: Clone repo, read architecture docs
  - File: `_bmad-output/planning-artifacts/research/codemachine-cli-eval.md` (create)
  - Repo: https://github.com/moazbuilds/CodeMachine-CLI
  - Reference: iterathon.tech comparison article
  - Action: Document how it orchestrates agents, state handling, parallel execution
  - Notes: Claims direct Claude Code support - verify this works with skills

- [ ] **Hands-on Test**: Run with standard test harness
  - Action: Configure to invoke `/bmad:bmm:workflows:workflow-status`
  - Test: Use test-story-S999.yaml as input
  - Notes: Must pass all 4 expected outcomes from test harness

- [ ] **Evaluate**: Score against criteria matrix
  - Document scores with rationale in eval.md
  - Compare directly to Task 1.1 results

#### Task 1.3: Study Auto-Claude Patterns (Day 3-4 - Inspiration Only)
- [ ] **Research**: Clone repo, study architecture without running
  - File: `_bmad-output/planning-artifacts/research/auto-claude-patterns.md` (create)
  - Repo: https://github.com/AndyMik90/Auto-Claude
  - Reference: n8n blog for pattern comparison
  - Action: Extract patterns for: Kanban visualization, Memory Layer, job tracking
  - Notes: NOT evaluating for adoption - extracting reusable patterns only

- [ ] **Document Learnings**: Patterns that solve our pain points
  - Requirement: At least 3 patterns with <200 LOC implementation sketches
  - Focus: State management, visualization, job tracking
  - Outcome: Each pattern must map to one of our 4 pain points

#### Task 1.4: Evaluate DevPod for Container Management (Day 4)
- [ ] **Research**: Read DevPod docs, compare to `claude-instance`
  - File: `_bmad-output/planning-artifacts/research/devpod-eval.md` (create)
  - URL: https://devpod.sh/docs
  - Action: Feature gap analysis vs `claude-instance` commands
  - Notes: devcontainer.json compatible is key requirement

- [ ] **Hands-on Test**: Create instance using DevPod
  - Action: `devpod up` with our devcontainer.json
  - Test: Can we replicate create/list/remove/open workflow?
  - Notes: Check if OrbStack integration works

#### Task 1.5: Secondary Candidates (Day 5 - Only if Primary Fail)

**Scope:** These tools are NOT evaluated unless Task 1.1 and 1.2 both score <4 on critical criteria.

**Promotion Trigger:** If Claude SDK and CodeMachine both fail by Day 5, promote ONE of these to full evaluation based on quick scan results.

| Tool | Quick Scan | Promotion Criteria |
|------|------------|-------------------|
| **LangGraph** | 1-hour: Can it wrap CLI tools? | Promote if has subprocess/shell integration |
| **MARSYS** | 1-hour: Topology patterns fit BMAD? | Promote if pipeline/hub-spoke matches analyst→architect flow |
| **ClaudeBox** | 30-min: Security model conflicts? | Promote if profiles work with our hooks |
| **zhsama/claude-sub-agent** | 30-min: Pattern similarity? | Promote if agent model matches BMAD closely |
| **Nimbalyst** | 15-min: Relevant at all? | Likely exclude - session manager, not orchestrator |

- [ ] **Quick Scans**: Document findings in `_bmad-output/planning-artifacts/research/quick-scans.md`
  - Each tool: 1 paragraph summary + go/no-go for promotion
  - Due: Day 5 if primary candidates failing

### Phase 2: Prototype Top Candidate(s) (Day 6-8)

Based on Phase 1 findings, select 1-2 top candidates and build working prototype.

#### Quantitative Baselines (Current State)

| Metric | Current Value | Target (30%+ improvement) |
|--------|---------------|---------------------------|
| Orchestration LOC | 2,500 | <1,750 |
| State file types | 5 | ≤3 |
| Failure recovery time | ~30s (manual) | <10s (automatic) |
| Coordination reliability | ~80% (PTY fragile) | >95% |

#### Prototype Scope

**IN Scope (must implement):**
- Single-instance orchestration
- YAML state read/write (sprint-status.yaml)
- Sequential skill invocation (workflow-status)
- Basic failure detection (exit code, timeout)
- Retry on failure
- **Minimal dual-instance test** (see below)

**Dual-Instance Test (required):**
Validates state coordination across 2 instances - a core pain point.
```
Setup:
  - Instance A: assigned story S999
  - Instance B: assigned story S998
  - Both share same sprint-status.yaml

Test:
  1. Instance A starts S999 → status becomes "in-progress"
  2. Instance B starts S998 → status becomes "in-progress"
  3. Verify: No collision, both stories tracked correctly
  4. Instance A completes → status becomes "review"
  5. Verify: S998 still "in-progress", S999 is "review"

Pass Criteria:
  - No race conditions on YAML write
  - Each instance sees other's state changes
  - Final state shows both stories in correct status
```

**OUT of Scope (do not implement):**
- Full multi-instance coordination (N instances)
- Parallel agent execution within single instance
- Visualization/dashboard
- Advanced retry policies (exponential backoff)
- Audit logging

**DEFER to Phase 3 (architecture only):**
- N-instance scaling design
- Visualization extension points
- Event-driven architecture hooks

#### Task 2.1: Prototype Selection
- [ ] **Decision**: Based on Phase 1 scores, select tool(s) to prototype
  - File: `_bmad-output/planning-artifacts/research/prototype-decision.md` (create)
  - Action: Document why selected, what we're testing
  - Notes: Could be single tool, hybrid, or minimal custom build
  - Threshold: Only prototype tools scoring 4+ on critical criteria

#### Task 2.2: Build Minimal Prototype
- [ ] **Implement**: Orchestrate single workflow
  - File: `packages/bmad-orchestrator/spike/prototype/` (create directory)
  - Action: Read sprint-status.yaml, invoke workflow-status skill, update state
  - Constraint: Must stay within IN scope items above

- [ ] **Test with Standard Harness**: All 4 expected outcomes must pass
  - Skill invocation: Exit code 0
  - State read: Correct story count
  - State write: YAML updated, git-diffable
  - Failure recovery: SIGKILL → state preserved → retry works

#### Task 2.3: Failure Scenario Testing

| Test Case | Setup | Expected Behavior | Pass Criteria |
|-----------|-------|-------------------|---------------|
| **SIGKILL** | Kill process mid-execution | State shows "in-progress", retry succeeds | State not corrupted, retry completes |
| **Exit Code 1** | Skill returns error | State captures error, logs output | Error message captured, rollback optional |
| **Ctrl+C** | User cancels | State rollback to previous status | Clean state, no partial writes |
| **Timeout** | Skill exceeds 5min | Timeout detected, process killed | Same as SIGKILL behavior |

- [ ] **Run all 4 failure tests**: Document results in prototype-decision.md
  - All 4 must pass for prototype to be considered successful

#### Task 2.4: Evaluate Prototype Against Baselines

- [ ] **Measure**: Compare to quantitative baselines
  - Orchestration LOC: Count lines in spike/prototype/
  - State file types: How many files does prototype use?
  - Failure recovery time: Measure with stopwatch
  - Coordination reliability: Run 10 invocations, count failures

- [ ] **Assess**: Does it solve the pain points?
  - State Location: Is state clearer than current?
  - Job Tracking: Is success/failure reliable?
  - Visualization: Can we add it later? (architecture review)
  - Coordination: Is it less fragile than PTY?

### Phase 3: Recommendation (Day 9-10)

#### Task 3.1: Risk Analysis

Before writing recommendation, assess risks for each candidate:

| Risk Factor | Assessment Criteria | Red Flag |
|-------------|--------------------|---------|
| **Maintainer Count** | GitHub contributors with >10 commits | <2 active maintainers |
| **Commit Frequency** | Commits in last 90 days | <10 commits |
| **Commercial Backing** | Company sponsor, funding | None AND <1000 stars |
| **Breaking Changes** | Major version changes, deprecations | >2 breaking changes in 12 months |
| **Escape Cost** | Hours to migrate away | >40 hours estimated |

- [ ] **Risk Assessment**: Document in decision.md
  - For each evaluated tool, complete risk table
  - Flag any red flags with mitigation plan
  - If tool has 3+ red flags, recommend against adoption

#### Task 3.2: Write Recommendation Document
- [ ] **Document**: Clear adopt/adapt/build decision
  - File: `_bmad-output/planning-artifacts/decisions/orchestration-infrastructure-decision.md` (create)
  - Action: For each infrastructure layer (instance, orchestration, container):
    - **Adopt**: Tool X handles this completely
    - **Adapt**: Extract patterns from Y
    - **Build**: Minimal custom layer (with architecture spec)
  - Include: Risk assessment from Task 3.1

#### Task 3.3: Integration Strategy

Define how to transition from current orchestrator to recommended solution:

| Strategy | Description | When to Use |
|----------|-------------|-------------|
| **Replace** | New tool runs in parallel, gradually take over, deprecate old | Tool scores 5 on critical criteria |
| **Wrap** | New tool calls existing status.py/executor.py as libraries | Tool scores 4, existing code is valuable |
| **Coexist** | New tool handles orchestration, existing handles instance mgmt | Different tools for different layers |

- [ ] **Integration Plan**: Document in decision.md
  - Which strategy for each layer
  - Rollback triggers: "If failure rate >10% in first week, revert"
  - Migration phases with go/no-go checkpoints

#### Task 3.4: Migration Path
- [ ] **Plan**: How do we transition from current to recommended?
  - File: Same as 3.2 (section in decision doc)
  - Action: Document incremental migration steps
  - Include rollback procedure for each step
  - Timeline: No time estimates, just sequence

#### Task 3.5: Architecture Proposal (if building)
- [ ] **Design**: If "build" recommended, provide architecture
  - File: `_bmad-output/planning-artifacts/architecture/orchestration-v2.md` (create)
  - Action: Design that's visualization-ready from day 1
  - Requirements:
    - Event-driven architecture (enables dashboard later)
    - Plugin points for state backends
    - Clear extension API for multi-instance (deferred)

### Acceptance Criteria (Outcome-Focused)

**Phase 1 Completion:**
- [ ] AC1: Given Claude Agent SDK, when tested with standard harness, then it CAN/CANNOT invoke `/bmad:bmm:workflows:workflow-status` with <30 LOC wrapper code
- [ ] AC2: Given CodeMachine-CLI, when tested with standard harness, then it CAN/CANNOT invoke BMAD skills AND scores documented for all 7 criteria
- [ ] AC3: Given Auto-Claude patterns, when analyzed, then ≥3 patterns provide actionable solution to ≥1 pain point (state/tracking/viz/coordination) with <200 LOC sketch
- [ ] AC4: Given DevPod, when tested with our devcontainer.json, then it CAN/CANNOT replace ≥80% of `claude-instance` commands (create/list/remove/open)

**Phase 2 Completion:**
- [ ] AC5: Given prototype, when run with test-story-S999.yaml, then story status updates correctly in sprint-status.yaml (git diff shows expected change)
- [ ] AC6: Given prototype, when all 4 failure scenarios executed (SIGKILL/Exit1/Ctrl+C/Timeout), then 4/4 pass with state preserved and retry successful
- [ ] AC7: Given prototype metrics, when compared to baselines, then ≥30% improvement in ≥2 metrics AND no regression >10% in any metric (LOC, state files, recovery time, reliability)

**Phase 3 Completion:**
- [ ] AC8: Given evaluation scores, when recommendation written, then decision is ADOPT/ADAPT/BUILD for each layer (instance, orchestration, container) with quantitative justification
- [ ] AC9: Given recommendation, when migration path written, then each step has explicit rollback trigger ("if X fails, do Y")
- [ ] AC10: Given "build" recommendation, when architecture proposed, then it includes: event-driven hooks, state backend plugin API, multi-instance extension point

## Additional Context

### Dependencies

**Current Stack (must maintain compatibility):**
- Python 3.12+ (bmad-cli)
- Bash (claude-instance)
- Docker / devcontainers
- Claude Code CLI
- tmux (terminal sharing)
- jq (JSON processing)

**Potential New Dependencies (by tool):**
- LangGraph: Python, langchain ecosystem
- CrewAI: Python, crewai package
- n8n: Node.js, self-hosted or cloud
- Claude Agent SDK: TypeScript or Python
- DevPod: Go binary, devcontainer CLI

**Constraints:**
- Must work inside devcontainers (Linux)
- Must work on host (macOS primary, Linux secondary)
- Cannot require additional cloud services (self-hosted preference)

### Testing Strategy

**Phase 1 Validation (Research):**
- Each tool evaluation produces a scored matrix (1-5 per criterion)
- Hands-on tests use actual BMAD skills, not synthetic examples
- Results documented in markdown files for review

**Phase 2 Validation (Prototype):**
- Test scenario: Complete story lifecycle (backlog → done)
- Failure injection: Kill Claude mid-skill, verify state preserved
- Comparison: Side-by-side with current approach on same workflow
- Metrics: Lines of orchestration code, number of state files, failure recovery time

**Phase 3 Validation (Recommendation):**
- Team review of decision document (Party Mode session)
- Rollback plan verified: Can we revert to current approach if needed?
- Migration risk assessment: What could go wrong?

**Manual Testing Checklist:**
1. [ ] Can invoke BMAD skill via new approach?
2. [ ] Does sprint-status.yaml update correctly?
3. [ ] Can we see what's running across instances?
4. [ ] Does failure recovery work without data loss?
5. [ ] Is the new approach simpler than current (fewer LOC, fewer state files)?

### Research References (Mapped to Tasks)

| Reference | URL | Used In |
|-----------|-----|---------|
| **Prior Research** | `_bmad-output/planning-artifacts/research/technical-ai-dev-environment-tools-research-2026-01-03.md` | All tasks - baseline context |
| **Claude Agent SDK Docs** | https://docs.anthropic.com/en/docs/claude-code/sdk | Task 0.1, 1.1 |
| **CodeMachine-CLI Repo** | https://github.com/moazbuilds/CodeMachine-CLI | Task 1.2 |
| **Auto-Claude Repo** | https://github.com/AndyMik90/Auto-Claude | Task 1.3 |
| **DevPod Docs** | https://devpod.sh/docs | Task 1.4 |
| **MARSYS Repo** | https://github.com/rezaho/MARSYS | Task 1.5 (topology patterns) |
| **n8n Blog: AI Orchestration** | https://blog.n8n.io/ai-agent-orchestration-frameworks/ | Task 1.3 (patterns) |
| **aimultiple: Agentic Frameworks** | https://research.aimultiple.com/agentic-orchestration/ | Task 1.5 (benchmarks) |
| **iterathon: LangGraph/CrewAI Guide** | https://iterathon.tech/blog/ai-agent-orchestration-frameworks-2026 | Task 1.2, 1.5 |
| **langwatch: Best AI Frameworks** | https://langwatch.ai/blog/best-ai-agent-frameworks-in-2025-comparing-langgraph-dspy-crewai-agno-and-more | Task 1.5 |
| **langflow: Framework Guide** | https://www.langflow.org/blog/the-complete-guide-to-choosing-an-ai-agent-framework-in-2025 | Task 3.1 (risk) |

**Usage Rule:** If prior research already scores a tool, start with those scores and validate/update rather than re-running benchmarks.

### Key Insights from Research

**Performance Benchmarks (from aimultiple.com):**
- LangGraph: Fastest execution (2.2x quicker than CrewAI), lowest token usage
- CrewAI: Longest latency (9s) due to autonomous deliberation, but comprehensive outputs
- AutoGen: 8-9x token difference vs LangGraph

**Market Context:**
- 86% of copilot spending ($7.2B) goes to agent-based systems
- 70%+ of new AI projects use orchestration frameworks
- Common pattern: Langflow for prototyping, LangGraph for production

**CodeMachine-CLI Claims:**
- 25-37x faster than manual AI prompting
- Supports Claude Code, Cursor CLI, and others
- Cross-service awareness and full project context

### Notes

**Party Mode Discussion Summary:**
The team (Winston, Mary, Barry, Murat) concluded that the original "Claude SDK spike" was too narrow. The real question is: "What's the minimum we need to build to get clean multi-agent coordination with BMAD, leveraging as much community work as possible?"

Auto-Claude's visualization is compelling as inspiration, but its methodology doesn't match BMAD. The evaluation should focus on finding tools that can **wrap** BMAD rather than **replace** it.
