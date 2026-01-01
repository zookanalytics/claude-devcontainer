# Tech Spec: BMAD Orchestrator

## Overview

### What We're Building

A lightweight CLI tool (`bmad`) that reads BMAD workflow state files and orchestrates development work across devcontainer instances. The tool provides:

1. **Status awareness** - Always knows "where are we?" and "what's next?"
2. **Epic automation** - Runs an entire epic through all stories with minimal intervention
3. **Clean audit trail** - One commit per story completion or code review feedback
4. **Foundation for full automation** - Structured to evolve into a dispatcher with parallel execution

### Why It Matters

Currently, BMAD requires manual triggering of each phase and remembering which step comes next. This orchestrator eliminates that cognitive overhead while preserving human oversight at meaningful checkpoints.

### Success Criteria

- Single command shows current state and recommended next action
- Can run an entire epic from start to finish with user involvement only at completion or critical questions
- Each story produces clean, atomic commits
- Works with existing `claude-instance` infrastructure
- Terminal-only interface (no web UI)

### Intervention Triggers

The orchestrator pauses automation and notifies the user when:

| Trigger | Detection Method | User Action Required |
|---------|------------------|---------------------|
| **Story blocked** | Status set to `blocked` in YAML | Review blocked_reason, resolve issue |
| **Test failures** | BMAD workflow sets `blocked` with test output | Fix tests or adjust acceptance criteria |
| **Timeout exceeded** | Story running > 30 min (configurable) | Check instance, extend or abort |
| **Merge conflict** | Git operation fails in workflow | Manual conflict resolution |
| **Claude asks question** | (Future) Detected via instance output parsing | Answer question, resume |
| **Epic complete** | All stories in epic reach `done` | Review, merge PR, start next epic |

**Intervention Response Options:**

```
[!] Story 1-3-protected-routes BLOCKED
    Reason: Test auth_redirect_test failing - expected 302, got 401

    Options:
    [r] Retry story (re-run dev-story)
    [s] Skip story (mark as blocked, continue epic)
    [f] Fix manually (pause automation, you take over)
    [a] Abort epic (stop all automation)

    Choice:
```

---

## Context for Development

### Existing Infrastructure

| Component | Location | Purpose |
|-----------|----------|---------|
| `claude-instance` | `scripts/claude-instance` | Manages devcontainer lifecycle, tmux integration |
| `bmm-workflow-status.yaml` | `_bmad-output/` | Tracks Phases 0-3 (Analysis → Solutioning) |
| `sprint-status.yaml` | `_bmad-output/implementation-artifacts/` | Tracks Phase 4 (epics, stories) |
| `.claude-metadata.json` | workspace root | Purpose tracking per instance |
| BMAD agents/workflows | `_bmad/` | 21 agents, 50+ workflows |

### State File Structures

**bmm-workflow-status.yaml** (Phases 0-3):
```yaml
workflow_status:
  - id: prd
    phase: 1
    status: "docs/prd.md"  # file path = complete
  - id: create-architecture
    phase: 2
    status: optional       # not started
```

**sprint-status.yaml** (Phase 4):
```yaml
development_status:
  epic-1: in-progress
  1-1-project-setup: review
  1-2-user-registration: done
  1-3-protected-routes: backlog
```

### Story Lifecycle

```
backlog → ready-for-dev → in-progress → review → done
```

- **backlog**: Story exists only in epic file
- **ready-for-dev**: Story file created via `create-story` workflow
- **in-progress**: Developer actively implementing
- **review**: Code review workflow running
- **done**: Story completed with passing tests

### Key Constraints

1. **Orchestration runs outside devcontainer** - Host machine with visibility to all instances
2. **Work runs inside devcontainer** - Claude instances execute in sandboxed environments
3. **One story at a time per epic** - Sequential within epic, parallel across epics (future)
4. **Commits are atomic** - One logical change per commit (story completion, review fix)
5. **No race conditions on state files** - Sequential-by-epic model means only one instance modifies `sprint-status.yaml` at a time per epic. Future parallel execution will use epic-level locking or separate status files per epic.

---

## Implementation Plan

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      bmad CLI (host)                        │
│                                                             │
│  bmad status    - Read YAML, display status and next action │
│  bmad next      - Execute recommended action                │
│  bmad run-epic  - Automate entire epic through completion   │
│  bmad run-story - Automate single story through completion  │
└─────────────────────────────────────────────────────────────┘
         │                                    │
         │ reads directly                     │ dispatches work
         ▼                                    ▼
┌─────────────────────────┐         ┌─────────────────────────┐
│ sprint-status.yaml      │         │ claude-instance         │
│                         │         │                         │
│ Parsed by orchestrator  │         │ Runs BMAD workflows:    │
│ for status + next story │         │ • create-story          │
│                         │         │ • dev-story             │
│                         │         │ • code-review           │
└─────────────────────────┘         └─────────────────────────┘
```

**Key insight:** The orchestrator reads YAML directly for fast status checks, but invokes BMAD workflows (via claude-instance) for actual work execution. This avoids expensive Claude calls just to read a file.

### File Structure

```
scripts/
├── claude-instance          # Existing - no changes needed
├── bmad                     # New - main CLI entry point (bash wrapper)
└── bmad/
    ├── __init__.py
    ├── cli.py               # Click-based CLI interface
    ├── status.py            # Reads sprint-status.yaml, computes next action
    └── executor.py          # Dispatches work to claude-instance
```

### Core Components

#### 1. Status Reader (`status.py`)

Reads `sprint-status.yaml` directly. Implements BMAD's priority logic (~20 lines).

```python
@dataclass
class SprintStatus:
    """Parsed sprint status with computed metrics."""
    epics: dict[str, str]           # {"epic-1": "in-progress", ...}
    stories: dict[str, str]         # {"1-1-project-setup": "review", ...}
    counts: dict[str, int]          # {"backlog": 3, "done": 2, ...}

@dataclass
class Action:
    type: str           # "create-story", "dev-story", "code-review"
    story_id: str       # Target story
    skill: str          # Full BMAD skill path

def load_sprint_status(project_path: str) -> SprintStatus:
    """
    Read and parse sprint-status.yaml directly.

    Handles flat dict format:
        development_status:
          epic-1: in-progress
          1-1-project-setup: review
    """
    yaml_path = f"{project_path}/_bmad-output/implementation-artifacts/sprint-status.yaml"
    with open(yaml_path) as f:
        data = yaml.safe_load(f)

    dev_status = data.get("development_status", {})

    epics = {k: v for k, v in dev_status.items() if k.startswith("epic-")}
    stories = {k: v for k, v in dev_status.items()
               if not k.startswith("epic-") and not k.endswith("-retrospective")}

    counts = {"backlog": 0, "ready-for-dev": 0, "in-progress": 0, "review": 0, "done": 0}
    for status in stories.values():
        if status in counts:
            counts[status] += 1

    return SprintStatus(epics=epics, stories=stories, counts=counts)

def get_next_action(status: SprintStatus) -> Action | None:
    """
    Compute next action using BMAD's priority logic.

    Priority (from BMAD sprint-status Step 3):
    1. in-progress → continue with dev-story
    2. review → code-review
    3. ready-for-dev → dev-story
    4. backlog → create-story
    5. All done → None
    """
    # Sort stories by ID for consistent ordering
    sorted_stories = sorted(status.stories.items(), key=lambda x: x[0])

    for story_id, story_status in sorted_stories:
        if story_status == "in-progress":
            return Action("dev-story", story_id, "bmad:bmm:workflows:dev-story")

    for story_id, story_status in sorted_stories:
        if story_status == "review":
            return Action("code-review", story_id, "bmad:bmm:workflows:code-review")

    for story_id, story_status in sorted_stories:
        if story_status == "ready-for-dev":
            return Action("dev-story", story_id, "bmad:bmm:workflows:dev-story")

    for story_id, story_status in sorted_stories:
        if story_status == "backlog":
            return Action("create-story", story_id, "bmad:bmm:workflows:create-story")

    return None  # All complete
```

#### 2. Executor (`executor.py`)

```python
def dispatch_to_instance(
    action: Action,
    instance_name: str,
    wait_for_completion: bool = True
) -> ExecutionResult:
    """
    Dispatch action to a claude-instance.

    1. Render prompt template with action.context
    2. Call claude-instance with prompt
    3. Wait for completion (if requested)
    4. Parse result and return status
    """

def run_story_to_completion(story_id: str) -> StoryResult:
    """
    Run a single story through all phases until done.

    Loop:
      1. Load current state
      2. Get next action for this story
      3. If action is None, story is done
      4. Execute action
      5. Check for user intervention needs
      6. Repeat
    """

def run_epic_to_completion(epic_id: str) -> EpicResult:
    """
    Run all stories in an epic sequentially.

    For each story in epic:
      1. If backlog, create story first
      2. Run story to completion
      3. Advance to next story
    """
```

#### 4. CLI Interface (`cli.py`)

```python
@click.group()
def bmad():
    """BMAD Orchestrator - Workflow automation for AI-driven development."""

@bmad.command()
def status():
    """Show current workflow state and next recommended action."""
    state = load_state(".")
    display_status_table(state)
    action = get_next_action(state)
    display_recommendation(action)

@bmad.command()
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def next(yes: bool):
    """Execute the next recommended action."""
    state = load_state(".")
    action = get_next_action(state)

    if not yes:
        if not confirm_action(action):
            return

    result = dispatch_to_instance(action, instance_name=f"bmad-{action.context['story_id']}")
    display_result(result)

@bmad.command()
@click.argument("epic_id")
@click.option("--dry-run", is_flag=True)
def run_epic(epic_id: str, dry_run: bool):
    """Run an entire epic through all stories to completion."""
    if dry_run:
        display_epic_plan(epic_id)
        return

    result = run_epic_to_completion(epic_id)
    display_epic_result(result)

@bmad.command()
@click.argument("story_id")
def run_story(story_id: str):
    """Run a single story through to completion."""
    result = run_story_to_completion(story_id)
    display_story_result(result)
```

### BMAD Integration

**Division of Responsibility:**

| Orchestrator Does (Fast, Local) | BMAD Does (Via Claude Instance) |
|---------------------------------|--------------------------------|
| Read sprint-status.yaml directly | Execute `create-story` workflow |
| Compute next action (priority logic) | Execute `dev-story` workflow |
| Display status and counts | Execute `code-review` workflow |
| Monitor for completion | Load agent personas |
| Set `in-progress` before dispatch | Update status files after work |
| Detect blocked/timeout | Create commits |

**Why This Split:**
- Status checking happens frequently → must be fast (no Claude calls)
- Work execution is expensive anyway → BMAD workflows add value
- Priority logic is ~20 lines → not worth a Claude call
- Risk detection can be added later if needed

**Dispatch Approach:**

```python
def dispatch_to_instance(
    action: Action,
    instance_name: str,
    timeout_minutes: int = 30
) -> ExecutionResult:
    """
    Launch claude-instance and invoke existing BMAD skill.

    Uses Popen with polling (not blocking subprocess.run) to:
    - Monitor progress via status file changes
    - Detect intervention triggers
    - Enforce timeout limits
    - Allow graceful interruption

    The BMAD workflow handles:
    - Agent persona loading
    - Reading relevant context files
    - Executing the workflow steps
    - Updating status files
    - Creating appropriate commits
    """
    skill = WORKFLOW_MAPPING[action.type]
    prompt = f"Run /{skill} for story {action.context['story_id']}"

    # Non-blocking launch
    process = subprocess.Popen(
        ["./scripts/claude-instance", "create", instance_name,
         "--prompt", prompt,
         "--branch", action.context.get("branch", "main")],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Polling loop
    start_time = time.time()
    while process.poll() is None:
        # Check timeout
        if time.time() - start_time > timeout_minutes * 60:
            process.terminate()
            return ExecutionResult(status="timeout", story_id=action.context['story_id'])

        # Check for intervention triggers (status file changes)
        current_status = load_story_status(action.context['story_id'])
        if current_status == "blocked":
            return ExecutionResult(status="intervention_needed", story_id=action.context['story_id'])

        time.sleep(5)  # Poll every 5 seconds

    exit_code = process.returncode
    return ExecutionResult(
        status="success" if exit_code == 0 else "failed",
        story_id=action.context['story_id'],
        exit_code=exit_code
    )
```

**Status Transition Ownership:**

| Transition | Who Sets It | When |
|------------|-------------|------|
| `backlog` → `ready-for-dev` | BMAD `create-story` workflow | After story file created |
| `ready-for-dev` → `in-progress` | **Orchestrator** | Before dispatching `dev-story` |
| `in-progress` → `review` | BMAD `dev-story` workflow | After implementation complete |
| `review` → `done` | BMAD `code-review` workflow | After review passes |
| Any → `blocked` | BMAD workflow | When intervention needed |

**Critical**: Orchestrator sets `in-progress` *before* dispatch to prevent race conditions where both sides assume the other will do it.

**Code Review Fresh Instance Requirement:**

The `code-review` action MUST spawn a **new Claude instance** (not continue in the same session). This ensures:
- Fresh context without implementation bias
- Independent evaluation of the code
- BMAD principle: "reviewer should not be the implementer"

```python
def dispatch_code_review(story_id: str) -> ExecutionResult:
    """
    Code review requires fresh instance - never reuse dev session.
    """
    instance_name = f"review-{story_id}-{int(time.time())}"  # Unique name
    return dispatch_to_instance(
        action=Action(type="code-review", ...),
        instance_name=instance_name
    )
```

**Responsibility Split:**

| Orchestrator Responsibility | BMAD Workflow Responsibility |
|----------------------------|------------------------------|
| Read state files | Load agent persona |
| Compute "what's next" | Read story/epic files |
| Select correct workflow | Execute implementation steps |
| Launch claude-instance | Update sprint-status.yaml |
| Monitor for completion | Create commits |
| Advance to next step | Handle workflow-specific logic |

### Implementation Tasks

#### Phase 1: Status Reader (MVP) ✅ COMPLETE
- [x] Create `scripts/bmad/status.py` with `load_sprint_status()`
- [x] Parse sprint-status.yaml flat dict format (custom parser, no pyyaml)
- [x] Implement `get_next_action()` with BMAD priority logic
- [x] Implement `bmad status` command (display counts + next action)
- [x] Implement `bmad run-epic --dry-run` and `bmad run-story --dry-run`
- [ ] **Tests**: YAML parsing, priority logic, edge cases (empty, all done)

#### Phase 2: Single Action Execution
- [ ] Create `scripts/bmad/executor.py` with `dispatch_to_instance()` using Popen
- [ ] Implement status transition (set `in-progress` before dispatch)
- [ ] Integrate with `claude-instance` script
- [ ] Implement `bmad next` command
- [ ] **Integration tests**: Mock subprocess, exit code handling, timeout

#### Phase 3: Story Automation
- [ ] Implement `run_story_to_completion()` with polling loop
- [ ] Add intervention trigger detection (blocked, timeout, etc.)
- [ ] Implement intervention response UI (retry/skip/fix/abort)
- [ ] Implement `bmad run-story` command
- [ ] Implement `dispatch_code_review()` with fresh instance requirement
- [ ] **Chaos tests**: Mid-story exit, BMAD data mode failure

#### Phase 4: Epic Automation
- [ ] Implement `run_epic_to_completion()`
- [ ] Add epic-level progress display
- [ ] Implement `bmad run-epic` command
- [ ] Add `--dry-run` to show plan without executing
- [ ] **E2E tests**: Full story lifecycle, full epic run-through

#### Phase 5: Polish & Documentation
- [ ] Add rich terminal output with progress indicators
- [ ] Add error handling and recovery guidance
- [ ] Add logging for audit trail
- [ ] Update AI-README.md with new commands
- [ ] Document intervention triggers and response options

### Dependencies

```
# Core (Python stdlib only - no external dependencies)
argparse          # CLI framework (stdlib)
dataclasses       # Data structures (stdlib)
pathlib           # Path handling (stdlib)

# Development/Testing
pytest>=7.0       # Testing framework
pytest-mock>=3.0  # Mocking utilities
```

**Note:** The orchestrator uses only Python stdlib to avoid dependency management issues. YAML parsing is done with a simple custom parser sufficient for sprint-status.yaml format.

### Testing Strategy

**Unit Tests (Required - Phase 1):**
- YAML parsing with various structures (empty, partial, complete)
- Priority logic: in-progress beats review beats ready-for-dev beats backlog
- Story ID sorting for consistent ordering
- Edge cases: empty sprint, all done, no stories

**Integration Tests (Required - Phase 2):**
- Mock `claude-instance` subprocess returning various exit codes
- Timeout detection and process termination
- Intervention trigger detection from status file changes

**Chaos Scenario Tests (Required - Phase 3):**
- Instance exits mid-story (process killed)
- Status file changes during polling (external edit)
- Recovery from `blocked` status
- Malformed YAML handling

**E2E Tests (Phase 4):**
- Full story lifecycle with real Claude instance
- Full epic run-through with multiple stories
- Intervention flow (block, user response, resume)

**Test Infrastructure:**
```python
# tests/conftest.py
@pytest.fixture
def sample_sprint_status(tmp_path):
    """Create sample sprint-status.yaml for testing."""
    yaml_content = """
development_status:
  epic-1: in-progress
  1-1-project-setup: done
  1-2-user-registration: review
  1-3-protected-routes: ready-for-dev
  epic-2: backlog
  2-1-document-model: backlog
"""
    status_file = tmp_path / "sprint-status.yaml"
    status_file.write_text(yaml_content)
    return status_file

@pytest.fixture
def mock_claude_instance(monkeypatch):
    """Mock subprocess calls to claude-instance."""

@pytest.fixture
def chaos_scenario(request):
    """Parameterized chaos scenarios for resilience testing."""
```

### Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Claude instance hangs | Add timeout with status check, manual recovery instructions |
| State file corruption | Validate before write, backup before modify |
| Merge conflicts | Fail fast, provide manual resolution steps |
| Story fails tests | Keep in `review` status, surface for human intervention |

---

## Open Questions

### Resolved

1. **Language preference?** → No preference, using Python (matches existing tooling patterns)
2. **Where does orchestration run?** → Host machine, outside devcontainer
3. **Full automation now?** → No, build foundation (Option A++) with path to full automation

### Pragmatic Decision: Direct YAML Reading

After analysis, the orchestrator should read `sprint-status.yaml` directly rather than invoking BMAD data mode:

**Why:**
- BMAD's priority logic is 5 simple if-statements - trivial to reimplement
- Calling Claude just to parse a YAML file is expensive and slow
- No reliable way to capture BMAD's template-output values
- The orchestrator runs outside devcontainer, needs direct file access anyway

**What we adopt from BMAD:**
- Priority logic: `in-progress > review > ready-for-dev > backlog`
- Status values and lifecycle transitions
- Story ID format conventions

**What we skip (for now):**
- Risk detection (stale files, orphaned stories) - add later
- Validation mode - orchestrator trusts the file format
- Interactive prompts - orchestrator is automation-focused

This is a pragmatic tradeoff: we reimplement ~20 lines of simple logic to avoid complex output parsing and expensive Claude calls for status checks.

## Future Enhancements (Out of Scope for Now)

- Parallel epic execution (multiple devcontainers)
- Web dashboard
- Slack/webhook notifications
- Automatic PR creation per epic
- Cost tracking per story

### Forward Compatibility for Full Dispatcher

The following design decisions enable future evolution to a full dispatcher with parallel execution:

| Current Design | Enables Future |
|---------------|----------------|
| `ExecutionResult` dataclass with status/exit_code | Dispatcher can aggregate results across instances |
| `dispatch_to_instance()` abstraction | Swap subprocess for container orchestration API |
| Epic-level operations (`run_epic`) | Natural unit for parallel execution |
| State files as source of truth | Multiple instances can poll same files with locking |
| Skill mapping validation | New workflows register without code changes |
| Intervention trigger system | Centralized alert routing to user |

**Critical interfaces to preserve:**
1. `Action` dataclass structure - dispatcher will queue these
2. `ExecutionResult` return type - dispatcher will aggregate these
3. `WORKFLOW_MAPPING` dict - add workflows without modifying dispatch logic
4. Status file format - add epic-level locks, not structural changes

---

*Generated by create-tech-spec workflow*
*Date: 2025-12-28*
