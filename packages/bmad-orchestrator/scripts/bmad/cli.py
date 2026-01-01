"""
BMAD Orchestrator CLI.

Uses only Python stdlib (argparse instead of click).

Interactive menu:
- bmad            - Interactive menu with status, options, and smart defaults

Commands (environment-aware):
- bmad status     - Show current sprint status (works anywhere)
- bmad next       - Auto-dispatch to instance (host only)
- bmad run-story  - Run a single story (devcontainer only)
- bmad run-epic   - Run an entire epic (devcontainer only)
"""

import argparse
import atexit
import json
import os
import re
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from .executor import (
    dispatch_to_instance,
    run_epic_to_completion,
    run_story_to_completion,
)
from .status import (
    Action,
    SprintStatus,
    get_next_action,
    get_stories_by_status,
    load_sprint_status,
)


class UserAbort(Exception):
    """Raised when user wants to quit."""

    pass


def prompt(message: str, default: str = "") -> str:
    """
    Prompt user for input with clean abort handling.

    Supports:
    - 'q' to quit
    - Ctrl+C to quit
    - Empty input returns default

    Raises UserAbort on quit.
    """
    try:
        response = input(message).strip()
        if response.lower() == "q":
            raise UserAbort()
        return response if response else default
    except EOFError:
        raise UserAbort()


def confirm(message: str, default_yes: bool = False) -> bool:
    """
    Prompt for yes/no confirmation with clean abort handling.

    Supports 'q' to quit, Ctrl+C to quit.
    Returns True for yes, False for no.
    Raises UserAbort on quit.
    """
    hint = "[Y/n/q]" if default_yes else "[y/N/q]"
    response = prompt(f"{message} {hint} ").lower()

    if response == "":
        return default_yes
    return response == "y"


# Environment detection
def is_inside_devcontainer() -> bool:
    """Check if running inside a devcontainer."""
    return bool(os.environ.get("CLAUDE_INSTANCE"))


def get_instance_name() -> str | None:
    """Get current instance name if inside devcontainer."""
    return os.environ.get("CLAUDE_INSTANCE")


def get_running_instances() -> list[dict]:
    """
    Get list of running instances with their details.

    Returns list of dicts with: name, purpose, path.
    Only works outside devcontainer.
    """
    try:
        # Use absolute path based on this script's location
        scripts_dir = Path(__file__).parent.parent
        claude_instance = scripts_dir / "claude-instance"

        result = subprocess.run(
            [str(claude_instance), "list", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return []

        data = json.loads(result.stdout)
        instances = []
        for inst in data.get("instances", []):
            if inst.get("running", False):
                instances.append({
                    "name": inst.get("name", ""),
                    "purpose": inst.get("purpose", ""),
                    "path": inst.get("path", ""),
                })

        return instances
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
        return []


# Dispatch tracking - stored in .claude/ which is already partially gitignored
DISPATCH_FILE = ".claude/.bmad-dispatched.json"


def get_dispatch_file(project: Path) -> Path:
    """Get path to dispatch tracking file."""
    dispatch_file = project / DISPATCH_FILE
    dispatch_file.parent.mkdir(parents=True, exist_ok=True)
    return dispatch_file


def load_dispatched(project: Path) -> dict:
    """Load currently dispatched work."""
    dispatch_file = get_dispatch_file(project)
    if dispatch_file.exists():
        try:
            return json.loads(dispatch_file.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def save_dispatched(project: Path, dispatched: dict) -> None:
    """Save dispatched work tracking."""
    dispatch_file = get_dispatch_file(project)
    dispatch_file.write_text(json.dumps(dispatched, indent=2) + "\n")


def record_dispatch(
    project: Path, story_id: str, action: str, instance: str, instance_path: str
) -> None:
    """Record that work has been dispatched to an instance."""
    dispatched = load_dispatched(project)
    dispatched[story_id] = {
        "action": action,
        "instance": instance,
        "instance_path": instance_path,
        "started": datetime.now(timezone.utc).isoformat(),
    }
    save_dispatched(project, dispatched)


def clear_dispatch(project: Path, story_id: str) -> None:
    """Clear dispatch record for a story (called when work completes)."""
    dispatched = load_dispatched(project)
    if story_id in dispatched:
        del dispatched[story_id]
        save_dispatched(project, dispatched)


def is_dispatched(project: Path, story_id: str) -> tuple[bool, dict | None]:
    """Check if a story is currently dispatched."""
    dispatched = load_dispatched(project)
    if story_id in dispatched:
        return True, dispatched[story_id]
    return False, None


# Run lock management - tracks actively running commands
LOCK_DIR = ".claude/.bmad-running"


def get_lock_dir(project: Path) -> Path:
    """Get path to lock directory."""
    lock_dir = project / LOCK_DIR
    lock_dir.mkdir(parents=True, exist_ok=True)
    return lock_dir


def get_lock_file(project: Path, story_id: str) -> Path:
    """Get path to lock file for a story."""
    return get_lock_dir(project) / f"{story_id}.json"


def create_run_lock(
    project: Path, story_id: str, action: str, starting_status: str | None = None
) -> Path:
    """
    Create a lock file indicating work is actively running.

    Returns path to lock file for cleanup.
    """
    lock_file = get_lock_file(project, story_id)
    lock_data = {
        "story_id": story_id,
        "action": action,
        "starting_status": starting_status,
        "pid": os.getpid(),
        "started": datetime.now(timezone.utc).isoformat(),
        "instance": get_instance_name() or "local",
    }
    lock_file.write_text(json.dumps(lock_data, indent=2) + "\n")
    return lock_file


def update_lock_status(project: Path, story_id: str, starting_status: str) -> None:
    """
    Update the starting_status in an existing lock file.

    Called at the start of each phase so the Stop hook can detect phase completion.
    """
    lock_file = get_lock_file(project, story_id)
    if not lock_file.exists():
        return

    try:
        lock_data = json.loads(lock_file.read_text())
        lock_data["starting_status"] = starting_status
        lock_file.write_text(json.dumps(lock_data, indent=2) + "\n")
    except (json.JSONDecodeError, OSError):
        pass  # Lock file corrupted or inaccessible


def remove_run_lock(project: Path, story_id: str) -> None:
    """Remove lock file for a story."""
    lock_file = get_lock_file(project, story_id)
    if lock_file.exists():
        lock_file.unlink()

    # Clean up empty lock directory
    lock_dir = get_lock_dir(project)
    if lock_dir.exists() and not any(lock_dir.iterdir()):
        lock_dir.rmdir()


def load_run_locks(project: Path) -> dict[str, dict]:
    """Load all current run locks."""
    lock_dir = get_lock_dir(project)
    locks = {}

    if not lock_dir.exists():
        return locks

    for lock_file in lock_dir.glob("*.json"):
        try:
            data = json.loads(lock_file.read_text())
            story_id = lock_file.stem
            locks[story_id] = data
        except (json.JSONDecodeError, OSError):
            continue

    return locks


def is_process_running(pid: int) -> bool:
    """Check if a process with given PID is running locally."""
    try:
        os.kill(pid, 0)  # Signal 0 just checks if process exists
        return True
    except (OSError, ProcessLookupError):
        return False


def get_container_name_for_instance(instance_name: str) -> str | None:
    """
    Find the docker container name for a given instance.

    Uses claude-instance list --json to get accurate container info.
    Returns None if no matching container is found.
    """
    import subprocess

    try:
        result = subprocess.run(
            ["./scripts/claude-instance", "list", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)
        for instance in data.get("instances", []):
            if instance.get("name") == instance_name:
                container = instance.get("container", "")
                return container if container else None
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
        return None


def is_process_running_in_container(instance_name: str, pid: int) -> bool:
    """
    Check if a process with given PID is running inside a container.

    Uses docker exec to check the process table inside the container.
    Returns False if container doesn't exist or process isn't running.
    """
    import subprocess

    container_name = get_container_name_for_instance(instance_name)
    if not container_name:
        return False

    try:
        result = subprocess.run(
            ["docker", "exec", container_name, "kill", "-0", str(pid)],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def get_stale_dispatches(project: Path) -> list[dict]:
    """
    Find dispatched work that is no longer running.

    Returns list of stale dispatch info dicts.
    """
    dispatched = load_dispatched(project)
    stale = []

    for story_id, info in dispatched.items():
        instance_path = info.get("instance_path", "")
        instance_name = info.get("instance", "")

        # Check for lock file in instance path
        if instance_path:
            instance_locks = load_run_locks(Path(instance_path))
        else:
            instance_locks = load_run_locks(project)

        # Determine if process is running
        is_running = False
        if story_id in instance_locks:
            pid = instance_locks[story_id]["pid"]
            if is_inside_devcontainer():
                is_running = is_process_running(pid)
            else:
                is_running = is_process_running_in_container(instance_name, pid)

        if not is_running:
            stale.append({
                "story_id": story_id,
                "instance": instance_name,
                "instance_path": instance_path,
                "action": info.get("action", ""),
                "started": info.get("started", ""),
            })

    return stale


# ANSI color codes for terminal output
class Colors:
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    END = "\033[0m"


def colored(text: str, color: str, bold: bool = False) -> str:
    """Apply ANSI color to text."""
    prefix = Colors.BOLD if bold else ""
    return f"{prefix}{color}{text}{Colors.END}"


def format_counts(counts: dict[str, int]) -> str:
    """Format status counts for display."""
    parts = []
    order = ["done", "review", "in-progress", "ready-for-dev", "backlog"]
    for status in order:
        count = counts.get(status, 0)
        if count > 0:
            parts.append(f"{status}: {count}")
    return ", ".join(parts) if parts else "none"


def format_epic_counts(counts: dict[str, int]) -> str:
    """Format epic counts for display."""
    parts = []
    order = ["done", "in-progress", "backlog"]
    for status in order:
        count = counts.get(status, 0)
        if count > 0:
            parts.append(f"{status}: {count}")
    return ", ".join(parts) if parts else "none"


def display_status(status: SprintStatus, action: Action | None) -> None:
    """Display sprint status in a formatted way."""
    print()
    print(colored("=" * 60, Colors.BLUE))
    print(colored(f"  BMAD Sprint Status: {status.project}", Colors.BLUE, bold=True))
    print(colored("=" * 60, Colors.BLUE))
    print()

    # Story counts
    print(colored("Stories:", Colors.END, bold=True))
    print(f"  {format_counts(status.counts)}")
    print()

    # Epic counts
    print(colored("Epics:", Colors.END, bold=True))
    print(f"  {format_epic_counts(status.epic_counts)}")
    print()

    # Next action
    print(colored("Next Action:", Colors.END, bold=True))
    if action:
        print(f"  {action.type} → {colored(action.story_id, Colors.CYAN, bold=True)}")
        print(f"  Skill: /{action.skill}")
    else:
        print(colored("  All stories complete!", Colors.GREEN))

    print()


def display_stories_by_status(status: SprintStatus) -> None:
    """Display stories grouped by status."""
    by_status = get_stories_by_status(status)

    print()
    print(colored("Stories by Status:", Colors.END, bold=True))
    print()

    status_colors = {
        "done": Colors.GREEN,
        "review": Colors.YELLOW,
        "in-progress": Colors.CYAN,
        "ready-for-dev": Colors.BLUE,
        "backlog": Colors.END,
    }

    order = ["in-progress", "review", "ready-for-dev", "backlog", "done"]
    for s in order:
        stories = by_status.get(s, [])
        if stories:
            print(colored(f"  {s}:", status_colors.get(s, Colors.END), bold=True))
            for story in stories:
                print(f"    - {story}")
            print()


def do_restart_story(project: Path, story_id: str, instances: list[dict]) -> int:
    """
    Restart a stale dispatch - shared logic for menu and restart command.

    Returns 0 on success, 1 on failure.
    """
    dispatched = load_dispatched(project)
    info = dispatched.get(story_id, {})
    original_instance = info.get("instance", "")
    instance_path = info.get("instance_path", "")

    # Check if original instance is available
    original_available = any(i["name"] == original_instance for i in instances)

    # Show options
    print()
    print(colored("Running instances:", Colors.END, bold=True))
    for i, inst in enumerate(instances, 1):
        marker = " (original)" if inst["name"] == original_instance else ""
        print(f"  {i}. {inst['name']}{marker}")

    # Prompt for instance selection
    if original_available:
        default = str(next(i for i, inst in enumerate(instances, 1)
                          if inst["name"] == original_instance))
    else:
        default = "1"

    choice = prompt(f"\nSelect instance [1-{len(instances)}/q]: ", default=default)

    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(instances):
            raise ValueError()
    except ValueError:
        print(colored("Invalid selection.", Colors.RED))
        return 1

    selected = instances[idx]
    selected_name = selected["name"]
    selected_path = selected["path"]

    # Clean up stale lock
    if instance_path:
        try:
            remove_run_lock(Path(instance_path), story_id)
        except Exception:
            pass

    # Dispatch to selected instance
    print()
    print(f"Restarting {colored(story_id, Colors.CYAN)} on {colored(selected_name, Colors.GREEN)}...")

    cmd = f"./scripts/bmad-cli run-story {story_id}"

    # Record new dispatch
    record_dispatch(
        project, story_id,
        action="run-story",
        instance=selected_name,
        instance_path=selected_path,
    )

    sys.stdout.flush()
    sys.stderr.flush()

    # Replace process with claude-instance run
    os.execvp("./scripts/claude-instance", ["claude-instance", "run", selected_name, cmd])


def do_dispatch_next(project: Path, sprint_status: SprintStatus, instances: list[dict],
                     skip_stories: set[str] | None = None) -> int:
    """
    Dispatch the next available story - shared logic for menu and next command.

    Returns 0 on success, 1 on failure.
    """
    action = get_next_action(sprint_status, skip_stories=skip_stories or set())

    if action is None:
        print(colored("No more work to dispatch.", Colors.GREEN))
        return 0

    print()
    print(colored("Next action:", Colors.END, bold=True))
    print(f"  {action.type} → {colored(action.story_id, Colors.CYAN, bold=True)}")
    print(f"  Skill: /{action.skill}")
    print()

    # Show available instances
    print(colored("Running instances:", Colors.END, bold=True))
    for i, inst in enumerate(instances, 1):
        purpose_str = f" ({inst['purpose']})" if inst["purpose"] else ""
        print(f"  {i}. {inst['name']}{purpose_str}")
    print()

    # Prompt for instance selection
    if len(instances) == 1:
        selected_inst = instances[0]
        if not confirm(f"Dispatch to '{selected_inst['name']}'?", default_yes=True):
            print("Aborted.")
            return 0
    else:
        choice = prompt(f"Select instance [1-{len(instances)}/q]: ", default="1")
        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(instances):
                print(colored("Invalid selection.", Colors.RED))
                return 1
            selected_inst = instances[idx]
        except ValueError:
            print(colored("Invalid selection.", Colors.RED))
            return 1

    # Build the command
    cmd = f"./scripts/bmad-cli run-story {action.story_id}"

    # Dispatch
    print()
    print(colored(f"Dispatching to '{selected_inst['name']}'...", Colors.CYAN))
    sys.stdout.flush()
    sys.stderr.flush()

    result = subprocess.run(
        ["./scripts/claude-instance", "run", selected_inst["name"], cmd],
    )

    if result.returncode == 0:
        record_dispatch(
            project, action.story_id, action.type,
            selected_inst["name"], selected_inst["path"],
        )
        print()
        print(colored(f"✓ Started in instance '{selected_inst['name']}'", Colors.GREEN))
        print(f"  Attach with: claude-instance attach {selected_inst['name']}")
        return 0
    else:
        print(colored("✗ Failed to dispatch", Colors.RED))
        return 1


def cmd_menu(args: argparse.Namespace) -> int:
    """Handle interactive menu mode."""
    project = Path(args.project).resolve()

    # Environment check - menu behavior differs in devcontainer
    if is_inside_devcontainer():
        return cmd_menu_devcontainer(args)

    # Load sprint status
    try:
        sprint_status = load_sprint_status(project)
    except FileNotFoundError as e:
        print(colored(f"Error: {e}", Colors.RED))
        print("\nNo sprint-status.yaml found. Run sprint planning first.")
        return 1
    except ValueError as e:
        print(colored(f"Error: {e}", Colors.RED))
        return 1

    # Get stale dispatches
    stale = get_stale_dispatches(project)
    dispatched = load_dispatched(project)

    # Get running instances
    instances = get_running_instances()

    # Get next action (excluding dispatched work)
    next_action = get_next_action(sprint_status, skip_stories=set(dispatched.keys()))

    # Box drawing helpers - inner width is 54 chars (between ║ markers)
    W = 54

    def box_top():
        return colored("╔" + "═" * W + "╗", Colors.BLUE)

    def box_mid():
        return colored("╠" + "═" * W + "╣", Colors.BLUE)

    def box_bot():
        return colored("╚" + "═" * W + "╝", Colors.BLUE)

    def box_line(text: str, color=Colors.BLUE, bold: bool = False) -> str:
        # Truncate if too long, pad if too short
        if len(text) > W:
            text = text[:W-3] + "..."
        return colored(f"║{text:<{W}}║", color, bold=bold)

    def box_empty():
        return colored("║" + " " * W + "║", Colors.BLUE)

    # Build menu
    while True:
        # Display header
        print()
        print(box_top())
        print(box_line("  BMAD Orchestrator", bold=True))
        print(box_mid())

        # Status summary
        story_summary = format_counts(sprint_status.counts)
        print(box_line(f"  Stories: {story_summary}"))
        epic_summary = format_epic_counts(sprint_status.epic_counts)
        print(box_line(f"  Epics: {epic_summary}"))

        # Warnings section
        if stale:
            print(box_mid())
            for s in stale[:3]:  # Show max 3
                # Truncate story_id if needed to fit warning
                sid = s['story_id']
                inst = s['instance']
                max_sid = W - 15 - len(inst)  # "  ⚠  Stale:  @ " = ~15 chars
                if len(sid) > max_sid:
                    sid = sid[:max_sid-3] + "..."
                warn = f"  ⚠  Stale: {sid} @ {inst}"
                print(box_line(warn, Colors.YELLOW))
            if len(stale) > 3:
                print(box_line(f"  ... and {len(stale) - 3} more stale dispatch(es)", Colors.YELLOW))

        # Options section
        print(box_mid())

        options = []
        default_option = "1"

        # Option: Restart stale dispatches (priority if any exist)
        if stale:
            if len(stale) == 1:
                sid = stale[0]['story_id']
                if len(sid) > 30:
                    sid = sid[:27] + "..."
                opt_text = f"Restart stale: {sid}"
            else:
                opt_text = f"Restart {len(stale)} stale dispatch(es)"
            options.append(("restart_stale", opt_text))
            default_option = "1"  # Stale restarts take priority

        # Option: Dispatch next
        if next_action and instances:
            sid = next_action.story_id
            if len(sid) > 20:
                sid = sid[:17] + "..."
            opt_text = f"Next story: {sid} ({next_action.type})"
            options.append(("next", opt_text))
            if not stale:
                default_option = str(len(options))
        elif next_action and not instances:
            sid = next_action.story_id
            if len(sid) > 20:
                sid = sid[:17] + "..."
            opt_text = f"Next story: {sid} (no instances)"
            options.append(("next_no_inst", opt_text))

        # Option: View stories
        options.append(("stories", "View stories by status"))

        # Option: Audit
        options.append(("audit", "Audit dispatch state"))

        # Option: Help
        options.append(("help", "Show help"))

        # Display options
        print(box_empty())
        for i, (_, text) in enumerate(options, 1):
            print(box_line(f"  {i}) {text}"))
        print(box_line("  q) Quit"))
        print(box_empty())
        print(box_bot())

        # Prompt
        try:
            choice = prompt(f"\nSelect [{default_option}]: ", default=default_option)
        except UserAbort:
            return 0

        # Handle choice
        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(options):
                print(colored("Invalid selection.", Colors.RED))
                continue
        except ValueError:
            print(colored("Invalid selection.", Colors.RED))
            continue

        action_key = options[idx][0]

        if action_key == "restart_stale":
            if not instances:
                print(colored("\nNo running instances to restart on.", Colors.RED))
                print("Start an instance with: claude-instance open <name>")
                print()
                if confirm("Clear stale dispatch(es) instead?", default_yes=False):
                    for s in stale:
                        clear_dispatch(project, s["story_id"])
                        if s["instance_path"]:
                            try:
                                remove_run_lock(Path(s["instance_path"]), s["story_id"])
                            except Exception:
                                pass
                    print(colored(f"✓ Cleared {len(stale)} stale dispatch(es).", Colors.GREEN))
                    stale = []
                continue

            if len(stale) == 1:
                # Single stale - restart directly
                return do_restart_story(project, stale[0]["story_id"], instances)
            else:
                # Multiple stale - show submenu
                print()
                print(colored("Stale dispatches to restart:", Colors.YELLOW, bold=True))
                for i, s in enumerate(stale, 1):
                    print(f"  {i}. {s['story_id']} @ {s['instance']}")
                print()
                print("  c) Clear all (abandon work)")
                print()

                sub_choice = prompt(f"Select to restart [1-{len(stale)}/c/q]: ", default="1")
                if sub_choice.lower() == "c":
                    if confirm("Clear all stale dispatches? Work will be lost.", default_yes=False):
                        for s in stale:
                            clear_dispatch(project, s["story_id"])
                            if s["instance_path"]:
                                try:
                                    remove_run_lock(Path(s["instance_path"]), s["story_id"])
                                except Exception:
                                    pass
                        print(colored(f"✓ Cleared {len(stale)} stale dispatch(es).", Colors.GREEN))
                        stale = []
                    continue
                else:
                    try:
                        sub_idx = int(sub_choice) - 1
                        if sub_idx < 0 or sub_idx >= len(stale):
                            raise ValueError()
                        return do_restart_story(project, stale[sub_idx]["story_id"], instances)
                    except ValueError:
                        print(colored("Invalid selection.", Colors.RED))
                        continue

        elif action_key == "next":
            return do_dispatch_next(project, sprint_status, instances, set(dispatched.keys()))

        elif action_key == "next_no_inst":
            print()
            print(colored("No running instances.", Colors.YELLOW))
            print("Start an instance with:")
            print("  claude-instance create <name>")
            print("  claude-instance open <name>")
            continue

        elif action_key == "stories":
            display_stories_by_status(sprint_status)
            input("\nPress Enter to continue...")
            continue

        elif action_key == "audit":
            # Run audit inline
            print()
            args_ns = argparse.Namespace(project=str(project), fix=False)
            cmd_audit(args_ns)
            input("\nPress Enter to continue...")
            continue

        elif action_key == "help":
            print()
            print(colored("BMAD Orchestrator Commands:", Colors.END, bold=True))
            print()
            print("  bmad              Interactive menu (this screen)")
            print("  bmad status       Show sprint status")
            print("  bmad next         Dispatch next work to an instance")
            print("  bmad audit        Check for stale dispatches")
            print("  bmad restart ID   Restart a stale dispatch")
            print()
            print(colored("Inside devcontainer:", Colors.END, bold=True))
            print()
            print("  bmad run-story ID   Run a story to completion")
            print("  bmad run-epic ID    Run an epic to completion")
            print()
            input("Press Enter to continue...")
            continue

    return 0


def cmd_menu_devcontainer(args: argparse.Namespace) -> int:
    """Handle menu mode inside devcontainer."""
    project = Path(args.project).resolve()
    instance_name = get_instance_name()

    # Load sprint status
    try:
        sprint_status = load_sprint_status(project)
    except FileNotFoundError as e:
        print(colored(f"Error: {e}", Colors.RED))
        return 1
    except ValueError as e:
        print(colored(f"Error: {e}", Colors.RED))
        return 1

    # Get next action
    next_action = get_next_action(sprint_status)

    # Box drawing helpers - inner width is 54 chars
    W = 54

    def box_top():
        return colored("╔" + "═" * W + "╗", Colors.BLUE)

    def box_mid():
        return colored("╠" + "═" * W + "╣", Colors.BLUE)

    def box_bot():
        return colored("╚" + "═" * W + "╝", Colors.BLUE)

    def box_line(text: str, color=Colors.BLUE, bold: bool = False) -> str:
        if len(text) > W:
            text = text[:W-3] + "..."
        return colored(f"║{text:<{W}}║", color, bold=bold)

    def box_empty():
        return colored("║" + " " * W + "║", Colors.BLUE)

    # Show simplified menu for devcontainer
    while True:
        print()
        print(box_top())
        print(box_line(f"  BMAD - {instance_name or 'devcontainer'}", bold=True))
        print(box_mid())

        # Status summary
        story_summary = format_counts(sprint_status.counts)
        print(box_line(f"  Stories: {story_summary}"))

        # Options
        print(box_mid())
        print(box_empty())

        options = []

        if next_action:
            # Truncate long story IDs to fit in menu
            sid = next_action.story_id
            if len(sid) > 22:
                sid = sid[:19] + "..."
            opt_text = f"Run next: {sid} ({next_action.type})"
            options.append(("run_next", opt_text, next_action.story_id))
        else:
            options.append(("done", "All stories complete!", None))

        options.append(("run_story", "Run specific story", None))
        options.append(("run_epic", "Run specific epic", None))
        options.append(("stories", "View stories by status", None))

        for i, (_, text, _) in enumerate(options, 1):
            print(box_line(f"  {i}) {text}"))
        print(box_line("  q) Quit"))
        print(box_empty())
        print(box_bot())

        try:
            choice = prompt("\nSelect [1]: ", default="1")
        except UserAbort:
            return 0

        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(options):
                print(colored("Invalid selection.", Colors.RED))
                continue
        except ValueError:
            print(colored("Invalid selection.", Colors.RED))
            continue

        action_key, _, story_id = options[idx]

        if action_key == "run_next":
            # Create namespace and call run-story
            run_args = argparse.Namespace(
                project=str(project),
                story_id=story_id,
                dry_run=False,
            )
            return cmd_run_story(run_args)

        elif action_key == "done":
            print(colored("\n✓ All stories complete!", Colors.GREEN))
            return 0

        elif action_key == "run_story":
            story_id = prompt("\nEnter story ID: ")
            if not story_id:
                continue
            run_args = argparse.Namespace(
                project=str(project),
                story_id=story_id,
                dry_run=False,
            )
            return cmd_run_story(run_args)

        elif action_key == "run_epic":
            epic_id = prompt("\nEnter epic ID (e.g., epic-1): ")
            if not epic_id:
                continue
            run_args = argparse.Namespace(
                project=str(project),
                epic_id=epic_id,
                dry_run=False,
            )
            return cmd_run_epic(run_args)

        elif action_key == "stories":
            display_stories_by_status(sprint_status)
            input("\nPress Enter to continue...")
            continue

    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Handle 'status' command."""
    project = Path(args.project).resolve()

    try:
        sprint_status = load_sprint_status(project)
    except FileNotFoundError as e:
        print(colored(f"Error: {e}", Colors.RED))
        return 1
    except ValueError as e:
        print(colored(f"Error: {e}", Colors.RED))
        return 1

    action = get_next_action(sprint_status)
    display_status(sprint_status, action)

    if args.stories:
        display_stories_by_status(sprint_status)

    return 0


def cmd_next(args: argparse.Namespace) -> int:
    """Handle 'next' command. Auto-dispatches to instance when on host."""
    project = Path(args.project).resolve()

    # Environment check - next is for dispatching from host
    if is_inside_devcontainer():
        print(colored("Error: 'next' is for dispatching from the host", Colors.RED))
        print()
        print("Inside devcontainer, use:")
        print("  bmad              # Interactive menu")
        print("  bmad run-story ID # Run a specific story")
        print("  bmad run-epic ID  # Run an entire epic")
        return 1

    try:
        sprint_status = load_sprint_status(project)
    except FileNotFoundError as e:
        print(colored(f"Error: {e}", Colors.RED))
        return 1

    # Auto-audit: Check for stale dispatches first
    stale = get_stale_dispatches(project)
    dispatched = load_dispatched(project)
    instances = get_running_instances()

    if stale:
        print()
        print(colored("⚠  Stale dispatch(es) detected:", Colors.YELLOW, bold=True))
        for s in stale:
            print(f"   {s['story_id']} @ {s['instance']}")
        print()

        # Offer to fix
        if instances:
            if len(stale) == 1:
                if confirm(f"Restart {stale[0]['story_id']}?", default_yes=True):
                    return do_restart_story(project, stale[0]["story_id"], instances)
                elif confirm("Clear stale dispatch and continue?", default_yes=False):
                    clear_dispatch(project, stale[0]["story_id"])
                    if stale[0]["instance_path"]:
                        try:
                            remove_run_lock(Path(stale[0]["instance_path"]), stale[0]["story_id"])
                        except Exception:
                            pass
                    print(colored("✓ Cleared.", Colors.GREEN))
                    # Refresh dispatched after clearing
                    dispatched = load_dispatched(project)
                else:
                    print("\nContinuing to next available story...")
            else:
                print("Options:")
                print("  1) Fix stale dispatches first (recommended)")
                print("  2) Clear all stale and continue")
                print("  3) Ignore and continue to next story")
                choice = prompt("\nSelect [1]: ", default="1")

                if choice == "1":
                    print("\nUse: bmad menu  (for interactive fix)")
                    print("  or: bmad restart <story-id>")
                    return 0
                elif choice == "2":
                    for s in stale:
                        clear_dispatch(project, s["story_id"])
                        if s["instance_path"]:
                            try:
                                remove_run_lock(Path(s["instance_path"]), s["story_id"])
                            except Exception:
                                pass
                    print(colored(f"✓ Cleared {len(stale)} stale dispatch(es).", Colors.GREEN))
                    dispatched = load_dispatched(project)
                # choice == "3" or default: continue
        else:
            print("No running instances available to restart on.")
            if confirm("Clear stale dispatches?", default_yes=True):
                for s in stale:
                    clear_dispatch(project, s["story_id"])
                    if s["instance_path"]:
                        try:
                            remove_run_lock(Path(s["instance_path"]), s["story_id"])
                        except Exception:
                            pass
                print(colored(f"✓ Cleared {len(stale)} stale dispatch(es).", Colors.GREEN))
                dispatched = load_dispatched(project)

    # Show any active (non-stale) dispatched work
    active_dispatched = {k: v for k, v in dispatched.items()
                         if k not in [s["story_id"] for s in stale]}
    if active_dispatched:
        print()
        print(colored("In-progress (active):", Colors.CYAN, bold=True))
        for story_id, info in active_dispatched.items():
            print(f"  {info['action']} → {story_id} @ {info['instance']}")
        print()

    # Find next action that isn't already dispatched
    action = get_next_action(sprint_status, skip_stories=set(dispatched.keys()))

    if action is None:
        if dispatched:
            print(colored("All remaining work is dispatched. Waiting for completion.", Colors.GREEN))
        else:
            print(colored("All stories complete! Nothing to do.", Colors.GREEN))
        return 0

    # Get running instances if not already fetched
    if not instances:
        instances = get_running_instances()

    if not instances:
        print()
        print(colored("Next action:", Colors.END, bold=True))
        print(f"  {action.type} → {colored(action.story_id, Colors.CYAN, bold=True)}")
        print()
        print(colored("No running instances found.", Colors.YELLOW))
        print()
        print("Create an instance with:")
        print("  claude-instance create <name>")
        print("  claude-instance open <name>")
        return 1

    # Use shared dispatch function
    return do_dispatch_next(project, sprint_status, instances, set(dispatched.keys()))


def cmd_run_story(args: argparse.Namespace) -> int:
    """Handle 'run-story' command. Must run inside devcontainer."""
    # Environment check
    if not is_inside_devcontainer():
        print(colored("Error: 'run-story' must run inside a devcontainer", Colors.RED))
        print()
        print("From the host, use:")
        print(f"  bmad next                    # Auto-dispatch to an instance")
        print(f"  claude-instance run <name> ./scripts/bmad-cli run-story <id>")
        return 1

    project = Path(args.project).resolve()
    story_id = args.story_id

    try:
        sprint_status = load_sprint_status(project)
    except FileNotFoundError as e:
        print(colored(f"Error: {e}", Colors.RED))
        return 1

    if story_id not in sprint_status.stories:
        print(colored(f"Error: Story '{story_id}' not found", Colors.RED))
        return 1

    current_status = sprint_status.stories[story_id]
    print()
    print(colored(f"Story: {story_id}", Colors.END, bold=True))
    print(f"Current status: {current_status}")
    print()

    if current_status == "done":
        print(colored("Story already complete!", Colors.GREEN))
        return 0

    # Show the phases this story will go through
    phases = []
    if current_status == "backlog":
        phases = ["create-story", "dev-story", "code-review"]
    elif current_status == "ready-for-dev":
        phases = ["dev-story", "code-review"]
    elif current_status == "in-progress":
        phases = ["dev-story (continue)", "code-review"]
    elif current_status == "review":
        phases = ["code-review"]

    print(colored("Phases to complete:", Colors.END, bold=True))
    for i, phase in enumerate(phases, 1):
        print(f"  {i}. {phase}")

    if args.dry_run:
        print()
        print(colored("Dry run - no actions taken.", Colors.YELLOW))
        return 0

    interactive = getattr(args, "interactive", False)
    yolo = not interactive  # yolo is now the default

    # Confirm before running (only in interactive mode)
    if interactive and not confirm("\nRun story to completion?", default_yes=False):
        print("Aborted.")
        return 0

    # Execute story automation with lock file for state tracking
    print()
    mode_str = " (interactive)" if interactive else ""
    print(colored(f"Running story...{mode_str}", Colors.CYAN))

    # Create lock file and set up cleanup
    create_run_lock(project, story_id, "run-story")

    def cleanup_lock(signum=None, frame=None):
        remove_run_lock(project, story_id)
        if signum:
            sys.exit(128 + signum)

    # Register cleanup for signals and normal exit
    signal.signal(signal.SIGTERM, cleanup_lock)
    signal.signal(signal.SIGINT, cleanup_lock)
    atexit.register(remove_run_lock, project, story_id)

    try:
        result = run_story_to_completion(story_id, project_path=project, yolo=yolo)
    finally:
        # Clean up lock file
        remove_run_lock(project, story_id)

    # Clear dispatch record - work is no longer in-flight
    clear_dispatch(project, story_id)

    if result.final_status == "done":
        print(colored(f"✓ Story completed!", Colors.GREEN))
        if result.phases_completed:
            print(f"  Phases: {', '.join(result.phases_completed)}")
        return 0
    elif result.intervention_reason:
        print(colored(f"✗ Intervention needed: {result.intervention_reason}", Colors.YELLOW))
        return 1
    else:
        print(colored(f"✗ Story ended with status: {result.final_status}", Colors.RED))
        return 1


def cmd_run_epic(args: argparse.Namespace) -> int:
    """Handle 'run-epic' command. Must run inside devcontainer."""
    # Environment check
    if not is_inside_devcontainer():
        print(colored("Error: 'run-epic' must run inside a devcontainer", Colors.RED))
        print()
        print("From the host, use:")
        print(f"  claude-instance run <name> ./scripts/bmad-cli run-epic <id>")
        return 1

    project = Path(args.project).resolve()
    epic_id = args.epic_id

    try:
        sprint_status = load_sprint_status(project)
    except FileNotFoundError as e:
        print(colored(f"Error: {e}", Colors.RED))
        return 1

    if epic_id not in sprint_status.epics:
        print(colored(f"Error: Epic '{epic_id}' not found", Colors.RED))
        return 1

    # Find all stories for this epic
    epic_num = epic_id.replace("epic-", "")
    epic_stories = {
        sid: status
        for sid, status in sprint_status.stories.items()
        if sid.startswith(f"{epic_num}-")
    }

    if not epic_stories:
        print(colored(f"No stories found for {epic_id}", Colors.YELLOW))
        return 0

    print()
    print(colored(f"Epic: {epic_id}", Colors.END, bold=True))
    print(f"Stories: {len(epic_stories)}")
    print()

    # Count by status
    by_status: dict[str, list[str]] = {}
    for sid, s in sorted(epic_stories.items()):
        by_status.setdefault(s, []).append(sid)

    for s in ["done", "review", "in-progress", "ready-for-dev", "backlog"]:
        if s in by_status:
            print(f"  {s}: {', '.join(by_status[s])}")

    remaining = [sid for sid, s in epic_stories.items() if s != "done"]

    if not remaining:
        print(colored("\nAll stories in epic complete!", Colors.GREEN))
        return 0

    print()
    print(colored(f"Stories to complete: {len(remaining)}", Colors.END, bold=True))
    for sid in sorted(remaining):
        print(f"  - {sid} ({epic_stories[sid]})")

    if args.dry_run:
        print()
        print(colored("Dry run - no actions taken.", Colors.YELLOW))
        return 0

    interactive = getattr(args, "interactive", False)
    yolo = not interactive  # yolo is now the default

    # Confirm before running (only in interactive mode)
    if interactive and not confirm("\nRun epic to completion?", default_yes=False):
        print("Aborted.")
        return 0

    # Execute epic automation
    print()
    mode_str = " (interactive)" if interactive else ""
    print(colored(f"Running epic...{mode_str}", Colors.CYAN))
    result = run_epic_to_completion(epic_id, project_path=project, yolo=yolo)

    # Clear dispatch records for all stories that finished (completed or failed)
    for sid in result.stories_completed:
        clear_dispatch(project, sid)
    for msg in result.stories_failed:
        # stories_failed contains "story_id: reason" format
        sid = msg.split(":")[0].strip()
        clear_dispatch(project, sid)

    # Display results
    print()
    if result.stories_completed:
        print(colored(f"✓ Completed: {len(result.stories_completed)}", Colors.GREEN))
        for sid in result.stories_completed:
            print(f"    {sid}")

    if result.stories_failed:
        print(colored(f"✗ Failed: {len(result.stories_failed)}", Colors.RED))
        for msg in result.stories_failed:
            print(f"    {msg}")
        return 1

    if result.stories_skipped:
        print(colored(f"○ Skipped: {len(result.stories_skipped)}", Colors.YELLOW))
        for sid in result.stories_skipped:
            print(f"    {sid}")

    if not result.stories_failed:
        print(colored("\n✓ Epic complete!", Colors.GREEN))
        return 0

    return 1


def cmd_clear_dispatch(args: argparse.Namespace) -> int:
    """Handle 'clear-dispatch' command to fix stuck dispatch state."""
    project = Path(args.project).resolve()
    dispatched = load_dispatched(project)

    if not dispatched:
        print("No dispatched work to clear.")
        return 0

    if args.all:
        # Clear all dispatches
        print(colored("Clearing all dispatched work:", Colors.YELLOW))
        for story_id, info in dispatched.items():
            print(f"  {info['action']} → {story_id} @ {info['instance']}")
        save_dispatched(project, {})
        print(colored("✓ All dispatches cleared.", Colors.GREEN))
        return 0

    if args.story_id:
        # Clear specific story
        if args.story_id not in dispatched:
            print(colored(f"Story '{args.story_id}' not in dispatched list.", Colors.YELLOW))
            print("Currently dispatched:")
            for story_id in dispatched:
                print(f"  - {story_id}")
            return 1

        info = dispatched[args.story_id]
        clear_dispatch(project, args.story_id)
        print(colored(f"✓ Cleared: {info['action']} → {args.story_id}", Colors.GREEN))
        return 0

    # No args - show usage
    print("Usage: bmad clear-dispatch <story-id> | --all")
    print()
    print("Currently dispatched:")
    for story_id, info in dispatched.items():
        print(f"  - {story_id}")
    return 1


def cmd_audit(args: argparse.Namespace) -> int:
    """Handle 'audit' command to verify dispatch state."""
    project = Path(args.project).resolve()

    dispatched = load_dispatched(project)
    local_locks = load_run_locks(project)

    print()
    print(colored("BMAD State Audit", Colors.END, bold=True))
    print("=" * 40)

    issues_found = 0

    # Check dispatched work against lock files in each instance's path
    print()
    print(colored("Dispatched (sent to instances):", Colors.CYAN))
    if not dispatched:
        print("  (none)")
    else:
        for story_id, info in dispatched.items():
            # Look for lock file in the instance's path
            instance_path = info.get("instance_path", "")
            if instance_path:
                instance_locks = load_run_locks(Path(instance_path))
            else:
                # Fallback to local locks for old dispatch records
                instance_locks = local_locks

            if story_id in instance_locks:
                lock = instance_locks[story_id]
                instance_name = info.get("instance", "")
                # Check process inside the container, not locally
                if is_inside_devcontainer():
                    # Inside container: check locally
                    is_running = is_process_running(lock["pid"])
                else:
                    # On host: check inside the target container
                    is_running = is_process_running_in_container(
                        instance_name, lock["pid"]
                    )
                if is_running:
                    status = colored("✓ running", Colors.GREEN)
                else:
                    status = colored("✗ stale (process dead)", Colors.RED)
                    issues_found += 1
            else:
                # No lock = command never started or already finished
                status = colored("✗ not running (no lock)", Colors.RED)
                issues_found += 1
            print(f"  {story_id} @ {info['instance']} - {status}")

    # Check local lock files (for runs started in this instance)
    print()
    print(colored("Local lock files:", Colors.CYAN))
    if not local_locks:
        print("  (none)")
    else:
        for story_id, lock in local_locks.items():
            pid = lock["pid"]
            if is_process_running(pid):
                status = colored(f"✓ running (pid {pid})", Colors.GREEN)
            else:
                status = colored(f"✗ stale (pid {pid} dead)", Colors.RED)
                issues_found += 1
            print(f"  {story_id} - {status}")

    # Summary
    print()
    if issues_found == 0:
        print(colored("✓ No issues found.", Colors.GREEN))
    else:
        print(colored(f"✗ {issues_found} issue(s) found.", Colors.RED))
        print()
        print("To fix: bmad audit --fix")

    # Auto-fix if requested
    if args.fix and issues_found > 0:
        print()
        print(colored("Fixing issues...", Colors.YELLOW))

        # Clear stale local locks
        for story_id, lock in local_locks.items():
            if not is_process_running(lock["pid"]):
                remove_run_lock(project, story_id)
                print(f"  Removed stale local lock: {story_id}")

        # Clear dispatches with no active lock (check in instance path)
        for story_id, info in list(dispatched.items()):
            instance_path = info.get("instance_path", "")
            instance_name = info.get("instance", "")
            if instance_path:
                instance_locks = load_run_locks(Path(instance_path))
            else:
                instance_locks = local_locks

            # Check if process is running (container-aware)
            if story_id in instance_locks:
                pid = instance_locks[story_id]["pid"]
                if is_inside_devcontainer():
                    is_running = is_process_running(pid)
                else:
                    is_running = is_process_running_in_container(instance_name, pid)
            else:
                is_running = False

            if not is_running:
                # Also try to clean up lock in instance path
                if instance_path and story_id in instance_locks:
                    remove_run_lock(Path(instance_path), story_id)
                    print(f"  Removed stale instance lock: {story_id}")
                clear_dispatch(project, story_id)
                print(f"  Cleared stale dispatch: {story_id}")

        print(colored("✓ Fixed.", Colors.GREEN))

    return 1 if issues_found > 0 else 0


def cmd_restart(args: argparse.Namespace) -> int:
    """Handle 'restart' command to resume a stale dispatch."""
    if is_inside_devcontainer():
        print(colored("Error: 'restart' is for dispatching from the host", Colors.RED))
        print("\nInside devcontainer, use:")
        print("  bmad run-story <id>    # Run a specific story")
        return 1

    project = Path(args.project).resolve()
    story_id = args.story_id
    dispatched = load_dispatched(project)

    if story_id not in dispatched:
        print(colored(f"Story '{story_id}' not in dispatched list.", Colors.YELLOW))
        if dispatched:
            print("\nCurrently dispatched:")
            for sid in dispatched:
                print(f"  - {sid}")
        return 1

    info = dispatched[story_id]
    original_instance = info.get("instance", "")
    instance_path = info.get("instance_path", "")

    print(f"Story: {colored(story_id, Colors.CYAN)}")
    print(f"Originally dispatched to: {original_instance}")
    print()

    # Get available instances
    instances = get_running_instances()
    if not instances:
        print(colored("No running instances found.", Colors.RED))
        print("Create one with: claude-instance create <name>")
        return 1

    # Check if original instance is still available
    original_available = any(i["name"] == original_instance for i in instances)

    # Show options
    print("Running instances:")
    for i, inst in enumerate(instances, 1):
        marker = " (original)" if inst["name"] == original_instance else ""
        print(f"  {i}. {inst['name']}{marker}")

    # Prompt for instance selection
    if original_available and not args.different:
        default = str(next(i for i, inst in enumerate(instances, 1)
                          if inst["name"] == original_instance))
    else:
        default = "1"

    choice = prompt(f"\nSelect instance [1-{len(instances)}/q]: ", default=default)

    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(instances):
            raise ValueError()
    except ValueError:
        print(colored("Invalid selection.", Colors.RED))
        return 1

    selected = instances[idx]
    selected_name = selected["name"]
    selected_path = selected["path"]

    # Clean up any stale lock in the original instance
    if instance_path:
        try:
            remove_run_lock(Path(instance_path), story_id)
        except Exception:
            pass  # Lock may not exist

    # Dispatch to selected instance
    print()
    print(f"Restarting {colored(story_id, Colors.CYAN)} on {colored(selected_name, Colors.GREEN)}...")

    # Build command - use run-story to resume from current state
    cmd = f"./scripts/bmad-cli run-story {story_id}"

    # Record new dispatch (overwrites old entry - no need to clear first)
    record_dispatch(
        project,
        story_id,
        action="run-story",
        instance=selected_name,
        instance_path=selected_path,
    )

    # Flush output before exec
    sys.stdout.flush()
    sys.stderr.flush()

    # Replace this process with claude-instance run (fully transparent)
    os.execvp("./scripts/claude-instance", ["claude-instance", "run", selected_name, cmd])


def main() -> int:
    """Entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog="bmad",
        description="BMAD Orchestrator - Workflow automation for AI-driven development",
    )
    parser.add_argument(
        "-p",
        "--project",
        default=".",
        help="Project root directory (default: current directory)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # menu command (also the default)
    subparsers.add_parser(
        "menu", help="Interactive menu with status and smart options (default)"
    )

    # status command
    status_parser = subparsers.add_parser(
        "status", help="Show current sprint status and next recommended action"
    )
    status_parser.add_argument(
        "-s", "--stories", action="store_true", help="Show stories grouped by status"
    )

    # next command
    next_parser = subparsers.add_parser("next", help="Execute the next recommended action")
    next_parser.add_argument(
        "-y", "--yes", action="store_true", help="Skip confirmation"
    )

    # run-story command
    run_story_parser = subparsers.add_parser(
        "run-story", help="Run a single story through to completion"
    )
    run_story_parser.add_argument("story_id", help="Story ID to run")
    run_story_parser.add_argument(
        "--dry-run", action="store_true", help="Show plan without executing"
    )
    run_story_parser.add_argument(
        "--interactive", "-i", action="store_true",
        help="Prompt for confirmations (default: yolo mode, auto-fix)"
    )

    # run-epic command
    run_epic_parser = subparsers.add_parser(
        "run-epic", help="Run an entire epic through all stories to completion"
    )
    run_epic_parser.add_argument("epic_id", help="Epic ID to run")
    run_epic_parser.add_argument(
        "--dry-run", action="store_true", help="Show plan without executing"
    )
    run_epic_parser.add_argument(
        "--interactive", "-i", action="store_true",
        help="Prompt for confirmations (default: yolo mode, auto-fix)"
    )

    # clear-dispatch command
    clear_dispatch_parser = subparsers.add_parser(
        "clear-dispatch", help="Clear stuck dispatch records"
    )
    clear_dispatch_parser.add_argument(
        "story_id", nargs="?", help="Story ID to clear (omit to list all)"
    )
    clear_dispatch_parser.add_argument(
        "--all", action="store_true", help="Clear all dispatched work"
    )

    # audit command
    audit_parser = subparsers.add_parser(
        "audit", help="Verify dispatch state and detect stale records"
    )
    audit_parser.add_argument(
        "--fix", action="store_true", help="Automatically fix stale records"
    )

    # restart command
    restart_parser = subparsers.add_parser(
        "restart", help="Resume a stale/dead dispatch on the same or different instance"
    )
    restart_parser.add_argument("story_id", help="Story ID to restart")
    restart_parser.add_argument(
        "-d", "--different", action="store_true",
        help="Default to a different instance than original"
    )

    args = parser.parse_args()

    # Default to menu when no command given
    if args.command is None:
        args.command = "menu"

    if args.command == "menu":
        return cmd_menu(args)
    elif args.command == "status":
        return cmd_status(args)
    elif args.command == "next":
        return cmd_next(args)
    elif args.command == "run-story":
        return cmd_run_story(args)
    elif args.command == "run-epic":
        return cmd_run_epic(args)
    elif args.command == "clear-dispatch":
        return cmd_clear_dispatch(args)
    elif args.command == "audit":
        return cmd_audit(args)
    elif args.command == "restart":
        return cmd_restart(args)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(130)  # Standard exit code for Ctrl+C
    except UserAbort:
        print("\nAborted.")
        sys.exit(0)
