# Minimal Custom Orchestration Architecture (Fallback)

**Date:** 2026-01-03
**Purpose:** Day 10 fallback if all tool evaluations fail
**LOC Target:** <500 lines total
**Status:** DRAFT - Ready if needed

---

## Overview

This architecture assumes NO external tools meet criteria. It defines the minimum viable orchestration layer to run BMAD workflows reliably.

**Design Principles:**
1. Use Claude Code CLI directly (no PTY wrappers)
2. YAML files remain source of truth
3. Simple retry logic (no complex state machines)
4. Event-driven for future extensibility

---

## Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATOR                              │
│                        (Python ~300 LOC)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ State Manager│  │ Executor     │  │ Event Bus    │           │
│  │ (~100 LOC)   │  │ (~150 LOC)   │  │ (~50 LOC)    │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
│        │                  │                  │                   │
│        │    Atomic YAML   │   Claude CLI     │   Pub/Sub         │
│        │    Read/Write    │   Subprocess     │   (EventEmitter)  │
│        ▼                  ▼                  ▼                   │
│  sprint-status.yaml   claude -p "..."    Listeners               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component 1: State Manager (~100 LOC)

**Purpose:** Atomic read/write of sprint-status.yaml with file locking

```python
# state_manager.py
import fcntl
import yaml
from pathlib import Path
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class Story:
    id: str
    title: str
    status: str  # backlog, ready-for-dev, in-progress, review, done
    epic: str

@dataclass
class SprintState:
    epics: List[dict]
    stories: List[Story]

class StateManager:
    def __init__(self, state_path: Path):
        self.state_path = state_path
        self.lock_path = state_path.with_suffix('.lock')

    @contextmanager
    def atomic_update(self):
        """Context manager for atomic YAML updates with file locking."""
        with open(self.lock_path, 'w') as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                state = self.read()
                yield state
                self.write(state)
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def read(self) -> SprintState:
        """Read current state from YAML."""
        with open(self.state_path) as f:
            data = yaml.safe_load(f)
        return SprintState(
            epics=data.get('epics', []),
            stories=[Story(**s) for s in data.get('stories', [])]
        )

    def write(self, state: SprintState):
        """Write state to YAML atomically."""
        data = {
            'epics': state.epics,
            'stories': [{'id': s.id, 'title': s.title, 'status': s.status, 'epic': s.epic}
                       for s in state.stories]
        }
        temp_path = self.state_path.with_suffix('.tmp')
        with open(temp_path, 'w') as f:
            yaml.safe_dump(data, f, default_flow_style=False)
        temp_path.rename(self.state_path)

    def update_story_status(self, story_id: str, new_status: str) -> Optional[Story]:
        """Update a story's status atomically."""
        with self.atomic_update() as state:
            for story in state.stories:
                if story.id == story_id:
                    story.status = new_status
                    return story
        return None

    def get_next_story(self) -> Optional[Story]:
        """Get next story by priority: in-progress > review > ready-for-dev."""
        state = self.read()
        priority = ['in-progress', 'review', 'ready-for-dev']
        for status in priority:
            for story in state.stories:
                if story.status == status:
                    return story
        return None
```

---

## Component 2: Executor (~150 LOC)

**Purpose:** Invoke Claude CLI with JSON output, parse results, handle retries

```python
# executor.py
import subprocess
import json
import time
from dataclasses import dataclass
from typing import Optional, Callable
from enum import Enum

class ExecutionResult(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"

@dataclass
class SkillResult:
    status: ExecutionResult
    session_id: Optional[str]
    output: str
    error: Optional[str]
    duration_seconds: float

class Executor:
    def __init__(self,
                 max_retries: int = 3,
                 retry_delays: tuple = (1, 2, 4),  # Exponential backoff
                 timeout_seconds: int = 300):
        self.max_retries = max_retries
        self.retry_delays = retry_delays
        self.timeout_seconds = timeout_seconds

    def invoke_skill(self,
                     skill: str,
                     story_id: str,
                     on_progress: Optional[Callable[[str], None]] = None) -> SkillResult:
        """
        Invoke a BMAD skill via Claude CLI.

        Args:
            skill: BMAD skill name (e.g., "bmad:bmm:workflows:dev-story")
            story_id: Story ID to process
            on_progress: Optional callback for streaming output

        Returns:
            SkillResult with status, output, and metadata
        """
        prompt = f"/{skill} for story {story_id}"

        for attempt in range(self.max_retries):
            start_time = time.time()
            try:
                result = self._run_claude(prompt, on_progress)
                return SkillResult(
                    status=ExecutionResult.SUCCESS,
                    session_id=result.get('session_id'),
                    output=result.get('result', ''),
                    error=None,
                    duration_seconds=time.time() - start_time
                )
            except subprocess.TimeoutExpired:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delays[min(attempt, len(self.retry_delays)-1)])
                    continue
                return SkillResult(
                    status=ExecutionResult.TIMEOUT,
                    session_id=None,
                    output='',
                    error=f'Timeout after {self.timeout_seconds}s',
                    duration_seconds=time.time() - start_time
                )
            except subprocess.CalledProcessError as e:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delays[min(attempt, len(self.retry_delays)-1)])
                    continue
                return SkillResult(
                    status=ExecutionResult.FAILURE,
                    session_id=None,
                    output=e.stdout or '',
                    error=e.stderr or str(e),
                    duration_seconds=time.time() - start_time
                )

        # Should not reach here
        return SkillResult(
            status=ExecutionResult.FAILURE,
            session_id=None,
            output='',
            error='Max retries exceeded',
            duration_seconds=0
        )

    def _run_claude(self, prompt: str, on_progress: Optional[Callable]) -> dict:
        """Run Claude CLI and return parsed JSON output."""
        cmd = [
            'claude', '-p', prompt,
            '--output-format', 'json',
            '--allowedTools', 'Read,Edit,Write,Bash,Glob,Grep,Task'
        ]

        if on_progress:
            # Streaming mode
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            output_lines = []
            for line in process.stdout:
                output_lines.append(line)
                on_progress(line)
            process.wait(timeout=self.timeout_seconds)
            if process.returncode != 0:
                raise subprocess.CalledProcessError(
                    process.returncode, cmd,
                    output=''.join(output_lines),
                    stderr=process.stderr.read()
                )
            return json.loads(''.join(output_lines))
        else:
            # Blocking mode
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=True
            )
            return json.loads(result.stdout)

    def resume_session(self, session_id: str, prompt: str) -> SkillResult:
        """Resume a previous session."""
        cmd = [
            'claude', '-p', prompt,
            '--resume', session_id,
            '--output-format', 'json'
        ]
        start_time = time.time()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True,
                                   timeout=self.timeout_seconds, check=True)
            data = json.loads(result.stdout)
            return SkillResult(
                status=ExecutionResult.SUCCESS,
                session_id=data.get('session_id'),
                output=data.get('result', ''),
                error=None,
                duration_seconds=time.time() - start_time
            )
        except Exception as e:
            return SkillResult(
                status=ExecutionResult.FAILURE,
                session_id=session_id,
                output='',
                error=str(e),
                duration_seconds=time.time() - start_time
            )
```

---

## Component 3: Event Bus (~50 LOC)

**Purpose:** Simple pub/sub for decoupled state change notifications

```python
# event_bus.py
from typing import Callable, Dict, List, Any
from dataclasses import dataclass
from enum import Enum

class EventType(Enum):
    STORY_STATUS_CHANGED = "story_status_changed"
    SKILL_STARTED = "skill_started"
    SKILL_COMPLETED = "skill_completed"
    SKILL_FAILED = "skill_failed"
    RETRY_SCHEDULED = "retry_scheduled"

@dataclass
class Event:
    type: EventType
    payload: Dict[str, Any]

class EventBus:
    def __init__(self):
        self._listeners: Dict[EventType, List[Callable[[Event], None]]] = {}

    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]):
        """Subscribe to an event type."""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)

    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], None]):
        """Unsubscribe from an event type."""
        if event_type in self._listeners:
            self._listeners[event_type].remove(callback)

    def emit(self, event: Event):
        """Emit an event to all subscribers."""
        if event.type in self._listeners:
            for callback in self._listeners[event.type]:
                try:
                    callback(event)
                except Exception as e:
                    # Log but don't crash
                    print(f"Event handler error: {e}")

    def emit_status_change(self, story_id: str, old_status: str, new_status: str):
        """Convenience method for status change events."""
        self.emit(Event(
            type=EventType.STORY_STATUS_CHANGED,
            payload={
                'story_id': story_id,
                'old_status': old_status,
                'new_status': new_status
            }
        ))
```

---

## Component 4: Orchestrator Main (~100 LOC)

**Purpose:** Tie components together, run workflow loop

```python
# orchestrator.py
from pathlib import Path
from state_manager import StateManager, Story
from executor import Executor, ExecutionResult
from event_bus import EventBus, EventType, Event

class Orchestrator:
    def __init__(self, state_path: Path):
        self.state = StateManager(state_path)
        self.executor = Executor()
        self.events = EventBus()

        # Subscribe to events for logging/dashboards
        self.events.subscribe(EventType.STORY_STATUS_CHANGED, self._log_status_change)
        self.events.subscribe(EventType.SKILL_COMPLETED, self._log_completion)

    def run_next_story(self) -> bool:
        """
        Find and process the next story.
        Returns True if a story was processed, False if none available.
        """
        story = self.state.get_next_story()
        if not story:
            return False

        # Determine skill based on current status
        skill = self._get_skill_for_status(story.status)
        if not skill:
            return False

        # Emit start event
        self.events.emit(Event(
            type=EventType.SKILL_STARTED,
            payload={'story_id': story.id, 'skill': skill}
        ))

        # Execute skill
        result = self.executor.invoke_skill(skill, story.id)

        if result.status == ExecutionResult.SUCCESS:
            # Update status based on completed phase
            new_status = self._get_next_status(story.status)
            old_status = story.status
            self.state.update_story_status(story.id, new_status)

            self.events.emit_status_change(story.id, old_status, new_status)
            self.events.emit(Event(
                type=EventType.SKILL_COMPLETED,
                payload={'story_id': story.id, 'skill': skill, 'duration': result.duration_seconds}
            ))
        else:
            self.events.emit(Event(
                type=EventType.SKILL_FAILED,
                payload={'story_id': story.id, 'skill': skill, 'error': result.error}
            ))

        return True

    def run_continuous(self, max_iterations: int = 100):
        """Run orchestration loop until no stories left or max iterations."""
        for i in range(max_iterations):
            if not self.run_next_story():
                print("No more stories to process")
                break
            print(f"Iteration {i+1} complete")

    def _get_skill_for_status(self, status: str) -> str:
        """Map story status to BMAD skill."""
        mapping = {
            'ready-for-dev': 'bmad:bmm:workflows:dev-story',
            'in-progress': 'bmad:bmm:workflows:dev-story',  # Continue work
            'review': 'bmad:bmm:workflows:code-review',
        }
        return mapping.get(status)

    def _get_next_status(self, current: str) -> str:
        """Determine next status after skill completion."""
        transitions = {
            'ready-for-dev': 'in-progress',
            'in-progress': 'review',
            'review': 'done',
        }
        return transitions.get(current, current)

    def _log_status_change(self, event: Event):
        """Log status changes."""
        p = event.payload
        print(f"[STATUS] {p['story_id']}: {p['old_status']} -> {p['new_status']}")

    def _log_completion(self, event: Event):
        """Log skill completions."""
        p = event.payload
        print(f"[DONE] {p['story_id']}: {p['skill']} ({p['duration']:.1f}s)")


# Entry point
if __name__ == '__main__':
    import sys
    state_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('sprint-status.yaml')
    orchestrator = Orchestrator(state_path)
    orchestrator.run_continuous()
```

---

## File Structure

```
packages/bmad-orchestrator/
├── src/
│   ├── __init__.py
│   ├── state_manager.py   # ~100 LOC
│   ├── executor.py        # ~150 LOC
│   ├── event_bus.py       # ~50 LOC
│   └── orchestrator.py    # ~100 LOC
├── tests/
│   ├── test_state_manager.py
│   ├── test_executor.py
│   └── test_orchestrator.py
└── pyproject.toml
```

**Total Estimated LOC:** ~400 (under 500 target)

---

## Extension Points (Deferred)

### For Visualization Dashboard (Future)
```python
# dashboard.py - NOT in MVP
from event_bus import EventBus, EventType

class DashboardAdapter:
    def __init__(self, bus: EventBus, websocket_url: str):
        self.ws = connect(websocket_url)
        bus.subscribe(EventType.STORY_STATUS_CHANGED, self._send_update)
        bus.subscribe(EventType.SKILL_COMPLETED, self._send_update)

    def _send_update(self, event):
        self.ws.send(json.dumps(event.payload))
```

### For Multi-Instance Coordination (Future)
```python
# coordinator.py - NOT in MVP
class InstanceCoordinator:
    def __init__(self, state: StateManager):
        self.state = state
        self.locks = {}  # story_id -> instance_id

    def claim_story(self, story_id: str, instance_id: str) -> bool:
        """Atomically claim a story for an instance."""
        with self.state.atomic_update() as s:
            if story_id in self.locks:
                return False
            self.locks[story_id] = instance_id
            return True
```

---

## Comparison to Current Implementation

| Aspect | Current (executor.py) | Fallback Architecture |
|--------|----------------------|----------------------|
| LOC | 545 | ~150 |
| PTY handling | Complex pseudoterminal | None - direct subprocess |
| Output parsing | Fragile string matching | JSON structured output |
| State tracking | Signal files + hooks | Event bus + atomic YAML |
| Retry logic | Manual restart | Built-in exponential backoff |
| Extensibility | Monolithic | Event-driven |

---

## When to Use This Fallback

**Use if:**
- Claude Agent SDK doesn't work with BMAD skills
- CodeMachine-CLI doesn't support Claude Code
- All evaluated tools score <4 on critical criteria
- Day 10 deadline reached without viable option

**Do NOT use if:**
- Claude Agent SDK works (Task 1.1 success) - use SDK instead
- CodeMachine-CLI viable (Task 1.2 success) - evaluate further
- DevPod handles instance management - combine with SDK

---

## Implementation Notes

1. **No PTY required** - Claude CLI with `--output-format json` gives structured output
2. **File locking** - Uses `fcntl` for POSIX systems (our devcontainer is Linux)
3. **Atomic writes** - Write to temp file, then rename (prevents corruption)
4. **Simple retry** - 3 attempts with 1s, 2s, 4s delays (not configurable in MVP)
5. **Event-driven** - Easy to add dashboard, logging, metrics later

---

**Document Status:** Ready for Day 10 fallback if needed
