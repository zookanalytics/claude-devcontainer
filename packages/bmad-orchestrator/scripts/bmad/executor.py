"""
Executor module for BMAD orchestrator.

Handles local execution of BMAD workflows inside a devcontainer.
Dispatching to instances is handled by the CLI via claude-instance run.
"""

import json
import os
import pty
import select
import signal
import sys
import termios
import time
import tty
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .status import Action, find_sprint_status_file, load_sprint_status

# Signal file path for phase completion detection
SIGNAL_FILE = ".claude/.bmad-phase-signal.json"


def _pty_spawn_with_signal(
    cmd: list[str], project_path: Path, check_interval: float = 0.5
) -> tuple[int, bool]:
    """
    Spawn a command in a PTY with signal file watching.

    Like pty.spawn() but periodically checks for the signal file.
    When the signal file is detected, terminates the child process.

    Args:
        cmd: Command to execute
        project_path: Path to project root (for signal file)
        check_interval: How often to check for signal file (seconds)

    Returns:
        Tuple of (exit_status in waitpid format, was_signaled)
    """
    signal_file = project_path / SIGNAL_FILE

    # Fork with PTY
    pid, master_fd = pty.fork()

    if pid == 0:
        # Child process - exec the command
        os.execlp(cmd[0], *cmd)
        # Never returns

    # Parent process - I/O loop with signal watching
    was_signaled = False

    # Save terminal settings and set to raw mode
    stdin_fd = sys.stdin.fileno()
    try:
        old_settings = termios.tcgetattr(stdin_fd)
        tty.setraw(stdin_fd)
        restore_terminal = True
    except termios.error:
        # Not a terminal (e.g., piped input)
        restore_terminal = False
        old_settings = None

    try:
        while True:
            # Check for signal file
            if signal_file.exists():
                try:
                    signal_file.unlink()
                except FileNotFoundError:
                    pass  # Race condition - file already deleted, this is fine
                except OSError as e:
                    # Log permission/filesystem errors but continue
                    print(f"Warning: Could not delete signal file: {e}", file=sys.stderr)
                # Signal detected - terminate Claude gracefully
                os.kill(pid, signal.SIGTERM)
                was_signaled = True
                break

            # Wait for I/O with timeout for signal checking
            try:
                rfds, _, _ = select.select([master_fd, stdin_fd], [], [], check_interval)
            except (select.error, ValueError):
                break

            # Handle output from child
            if master_fd in rfds:
                try:
                    data = os.read(master_fd, 1024)
                    if not data:
                        break  # Child closed PTY
                    os.write(sys.stdout.fileno(), data)
                except OSError:
                    break

            # Handle input from user
            if stdin_fd in rfds:
                try:
                    data = os.read(stdin_fd, 1024)
                    if data:
                        os.write(master_fd, data)
                except OSError:
                    break

    finally:
        # Restore terminal settings
        if restore_terminal and old_settings:
            try:
                termios.tcsetattr(stdin_fd, termios.TCSADRAIN, old_settings)
            except termios.error:
                pass

        # Clean up
        try:
            os.close(master_fd)
        except OSError:
            pass

    # Wait for child to exit
    _, status = os.waitpid(pid, 0)
    return status, was_signaled


def _update_lock_starting_status(project_path: Path, story_id: str, status: str) -> None:
    """
    Update the starting_status in the lock file for Stop hook detection.

    The Stop hook compares current status against starting_status to detect
    phase completion. This must be called at the start of each phase.
    """
    lock_file = project_path / ".claude" / ".bmad-running" / f"{story_id}.json"
    if not lock_file.exists():
        return

    try:
        lock_data = json.loads(lock_file.read_text())
        lock_data["starting_status"] = status
        lock_file.write_text(json.dumps(lock_data, indent=2) + "\n")
    except (json.JSONDecodeError, OSError):
        pass  # Lock file corrupted or inaccessible


@dataclass
class ExecutionResult:
    """Result of executing an action."""

    status: str  # "success", "failed", "timeout", "intervention_needed", "dry_run"
    story_id: str
    exit_code: int | None = None
    message: str = ""
    duration_seconds: float = 0.0


@dataclass
class StoryResult:
    """Result of running a story to completion."""

    story_id: str
    final_status: str
    phases_completed: list[str] = field(default_factory=list)
    intervention_reason: str | None = None


@dataclass
class EpicResult:
    """Result of running an epic to completion."""

    epic_id: str
    stories_completed: list[str] = field(default_factory=list)
    stories_failed: list[str] = field(default_factory=list)
    stories_skipped: list[str] = field(default_factory=list)


# Mapping from action types to BMAD skills
WORKFLOW_MAPPING = {
    "create-story": "bmad:bmm:workflows:create-story",
    "dev-story": "bmad:bmm:workflows:dev-story",
    "code-review": "bmad:bmm:workflows:code-review",
}


def update_story_status(
    project_path: str | Path,
    story_id: str,
    new_status: str,
) -> None:
    """
    Update a story's status in sprint-status.yaml.

    Uses simple text manipulation to avoid YAML library dependency.
    """
    project_path = Path(project_path)
    yaml_path = find_sprint_status_file(project_path)

    if not yaml_path:
        raise FileNotFoundError(f"sprint-status.yaml not found in {project_path}")

    content = yaml_path.read_text()
    lines = content.split("\n")
    updated_lines = []

    for line in lines:
        # Match lines like "  1-1-project-setup: backlog"
        stripped = line.strip()
        if stripped.startswith(f"{story_id}:"):
            # Preserve indentation
            indent = line[: len(line) - len(line.lstrip())]
            updated_lines.append(f"{indent}{story_id}: {new_status}")
        else:
            updated_lines.append(line)

    yaml_path.write_text("\n".join(updated_lines))


def build_local_command(action: Action, yolo: bool = False) -> list[str]:
    """
    Build the command to execute an action locally.

    Returns command as list of strings suitable for pty.spawn.
    Must be run inside a devcontainer.

    Args:
        action: The action to execute
        yolo: If True, run in yolo mode (skip prompts, auto-fix)
    """
    skill = WORKFLOW_MAPPING.get(action.type, action.skill)
    prompt = f"/{skill} for story {action.story_id}"
    if yolo:
        # Add yolo mode instruction - BMAD workflows will skip prompts and auto-fix
        prompt += " #yolo mode: skip all prompts, auto-fix all issues"
    # Pass prompt as argument (not -p) to keep Claude interactive
    return ["claude", prompt]


def dispatch_to_instance(
    action: Action,
    project_path: str | Path = ".",
    dry_run: bool = False,
    yolo: bool = False,
) -> ExecutionResult:
    """
    Execute action locally inside a devcontainer.

    Runs fully interactively - inherits stdin/stdout/stderr from parent.
    User can interact with prompts and Ctrl+C to interrupt.

    Args:
        action: The action to execute
        project_path: Path to the project
        dry_run: If True, just show what would be done
        yolo: If True, run in yolo mode (skip prompts, auto-fix)

    Returns:
        ExecutionResult with status and details
    """
    project_path = Path(project_path).resolve()

    # Build the local command
    cmd = build_local_command(action, yolo=yolo)

    if dry_run:
        cmd_str = " ".join(cmd)
        return ExecutionResult(
            status="dry_run",
            story_id=action.story_id,
            message=f"Would run: {cmd_str}",
        )

    # Update status to in-progress before dispatch
    try:
        if action.type in ("dev-story", "create-story"):
            update_story_status(project_path, action.story_id, "in-progress")
    except FileNotFoundError:
        pass  # Status file may not exist yet

    # Execute the command with full PTY transparency and signal file watching
    # Uses custom PTY loop that checks for phase completion signal file
    # When the Stop hook detects phase completion, it writes the signal file
    # and this function terminates Claude to proceed to the next phase
    sys.stdout.flush()
    sys.stderr.flush()

    start_time = time.time()
    try:
        # Use custom PTY spawn that watches for signal file
        exit_status, was_signaled = _pty_spawn_with_signal(cmd, project_path)
        duration = time.time() - start_time

        # Extract exit code from waitpid status
        if os.WIFEXITED(exit_status):
            exit_code = os.WEXITSTATUS(exit_status)
        elif os.WIFSIGNALED(exit_status):
            # Process was killed by signal (including our SIGTERM on phase complete)
            if was_signaled:
                # We terminated Claude because phase completed - this is success
                exit_code = 0
            else:
                exit_code = 128 + os.WTERMSIG(exit_status)
        else:
            exit_code = 1

        return ExecutionResult(
            status="success" if exit_code == 0 else "failed",
            story_id=action.story_id,
            exit_code=exit_code,
            duration_seconds=duration,
        )

    except KeyboardInterrupt:
        duration = time.time() - start_time
        return ExecutionResult(
            status="interrupted",
            story_id=action.story_id,
            message="Interrupted by user",
            duration_seconds=duration,
        )

    except FileNotFoundError as e:
        return ExecutionResult(
            status="failed",
            story_id=action.story_id,
            message=f"Command not found: {e}",
        )


def run_story_to_completion(
    story_id: str,
    project_path: str | Path = ".",
    yolo: bool = False,
) -> StoryResult:
    """
    Run a single story through all phases until done.

    Loops through the story lifecycle:
    1. Load current state
    2. Get next action for this story
    3. If story is done, return success
    4. Execute action
    5. Track retries per status (detect stuck)
    6. Repeat

    Args:
        story_id: The story to run
        project_path: Path to the project
        yolo: If True, skip prompts and auto-fix issues

    Safety limits:
    - Max 3 retries for same status (e.g., repeated code-review passes)
    - Max 10 total phases (shouldn't happen in practice)
    """
    project_path = Path(project_path).resolve()
    phases_completed: list[str] = []
    max_phases = 10  # Total phase limit
    max_same_status_retries = 3  # Retries allowed for same status (e.g., review iterations)

    previous_status: str | None = None
    same_status_count = 0

    for phase_num in range(max_phases):
        # Load current state
        try:
            status = load_sprint_status(project_path)
        except (FileNotFoundError, ValueError) as e:
            return StoryResult(
                story_id=story_id,
                final_status="failed",
                phases_completed=phases_completed,
                intervention_reason=str(e),
            )

        # Check current story status
        current_status = status.stories.get(story_id)

        if current_status is None:
            return StoryResult(
                story_id=story_id,
                final_status="not_found",
                phases_completed=phases_completed,
                intervention_reason=f"Story {story_id} not found in status file",
            )

        if current_status == "done":
            return StoryResult(
                story_id=story_id,
                final_status="done",
                phases_completed=phases_completed,
            )

        if current_status == "blocked":
            return StoryResult(
                story_id=story_id,
                final_status="blocked",
                phases_completed=phases_completed,
                intervention_reason="Story marked as blocked",
            )

        # Track same-status retries
        if current_status == previous_status:
            same_status_count += 1
            if same_status_count >= max_same_status_retries:
                return StoryResult(
                    story_id=story_id,
                    final_status=current_status,
                    phases_completed=phases_completed,
                    intervention_reason=f"Status unchanged after {max_same_status_retries} attempts (stuck at '{current_status}')",
                )
        else:
            same_status_count = 0

        # Determine next action based on current status
        action = _get_action_for_status(story_id, current_status)

        if action is None:
            return StoryResult(
                story_id=story_id,
                final_status=current_status,
                phases_completed=phases_completed,
                intervention_reason=f"No action for status: {current_status}",
            )

        # Remember status before execution
        previous_status = current_status

        # Update lock file with current status so Stop hook can detect phase completion
        _update_lock_starting_status(project_path, story_id, current_status)

        # Execute the action
        result = dispatch_to_instance(
            action,
            project_path=project_path,
            yolo=yolo,
        )

        if result.status != "success":
            return StoryResult(
                story_id=story_id,
                final_status=result.status,
                phases_completed=phases_completed,
                intervention_reason=result.message,
            )

        phases_completed.append(action.type)

    # Hit max phases (shouldn't happen in practice)
    return StoryResult(
        story_id=story_id,
        final_status="max_phases",
        phases_completed=phases_completed,
        intervention_reason=f"Exceeded {max_phases} total phases",
    )


def _get_action_for_status(story_id: str, status: str) -> Action | None:
    """Get the appropriate action for a story based on its status."""
    if status == "backlog":
        return Action("create-story", story_id, WORKFLOW_MAPPING["create-story"])
    elif status == "ready-for-dev":
        return Action("dev-story", story_id, WORKFLOW_MAPPING["dev-story"])
    elif status == "in-progress":
        return Action("dev-story", story_id, WORKFLOW_MAPPING["dev-story"])
    elif status == "review":
        return Action("code-review", story_id, WORKFLOW_MAPPING["code-review"])
    return None


def run_epic_to_completion(
    epic_id: str,
    project_path: str | Path = ".",
    yolo: bool = False,
) -> EpicResult:
    """
    Run all stories in an epic sequentially until done.

    For each story in the epic:
    1. Run story to completion
    2. Handle any interventions
    3. Continue to next story

    Args:
        epic_id: The epic to run
        project_path: Path to the project
        yolo: If True, skip prompts and auto-fix issues
    """
    project_path = Path(project_path).resolve()

    # Load status to get stories for this epic
    try:
        status = load_sprint_status(project_path)
    except (FileNotFoundError, ValueError) as e:
        return EpicResult(
            epic_id=epic_id,
            stories_failed=[f"Error loading status: {e}"],
        )

    # Find stories belonging to this epic
    epic_num = epic_id.replace("epic-", "")
    epic_stories = [
        sid for sid in sorted(status.stories.keys()) if sid.startswith(f"{epic_num}-")
    ]

    if not epic_stories:
        return EpicResult(
            epic_id=epic_id,
            stories_failed=[f"No stories found for {epic_id}"],
        )

    stories_completed: list[str] = []
    stories_failed: list[str] = []
    stories_skipped: list[str] = []

    for story_id in epic_stories:
        # Skip already completed stories
        if status.stories.get(story_id) == "done":
            stories_completed.append(story_id)
            continue

        # Run story to completion
        result = run_story_to_completion(
            story_id,
            project_path=project_path,
            yolo=yolo,
        )

        if result.final_status == "done":
            stories_completed.append(story_id)
        elif result.intervention_reason:
            stories_failed.append(f"{story_id}: {result.intervention_reason}")
            # For now, stop on first failure
            # Future: could prompt user for skip/retry/abort
            break
        else:
            stories_failed.append(story_id)
            break

    return EpicResult(
        epic_id=epic_id,
        stories_completed=stories_completed,
        stories_failed=stories_failed,
        stories_skipped=stories_skipped,
    )
