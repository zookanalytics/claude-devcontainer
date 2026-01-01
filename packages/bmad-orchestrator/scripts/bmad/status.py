"""
Status reader for BMAD orchestrator.

Reads sprint-status.yaml directly and computes next action using BMAD's priority logic.
Uses only Python stdlib (no external dependencies).
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class SprintStatus:
    """Parsed sprint status with computed metrics."""

    epics: dict[str, str]  # {"epic-1": "in-progress", ...}
    stories: dict[str, str]  # {"1-1-project-setup": "review", ...}
    counts: dict[str, int]  # {"backlog": 3, "done": 2, ...}
    epic_counts: dict[str, int]  # {"backlog": 1, "in-progress": 1, ...}
    project: str  # Project name
    generated: str  # Generation date


@dataclass
class Action:
    """Represents the next action to take."""

    type: str  # "create-story", "dev-story", "code-review"
    story_id: str  # Target story
    skill: str  # Full BMAD skill path

    def __str__(self) -> str:
        return f"{self.type} for {self.story_id}"


# Valid status values
STORY_STATUSES = {"backlog", "ready-for-dev", "in-progress", "review", "done"}
EPIC_STATUSES = {"backlog", "in-progress", "done"}


def parse_simple_yaml(content: str) -> dict[str, Any]:
    """
    Parse a simple YAML file (enough for sprint-status.yaml).

    Handles:
    - Top-level key: value pairs
    - Simple nested dictionaries (one level with indentation)
    - Comments (lines starting with #)

    Does NOT handle:
    - Lists
    - Multi-line values
    - Complex nesting
    """
    result: dict[str, Any] = {}
    current_section: str | None = None
    current_dict: dict[str, str] = {}

    for line in content.split("\n"):
        # Skip empty lines and comments
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Check indentation
        indent = len(line) - len(line.lstrip())

        # Parse key: value
        if ":" in stripped:
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            if indent == 0:
                # Top-level key
                if current_section and current_dict:
                    result[current_section] = current_dict
                    current_dict = {}

                if value:
                    result[key] = value
                    current_section = None
                else:
                    # Start of a section
                    current_section = key
                    current_dict = {}
            elif current_section:
                # Nested key under current section
                current_dict[key] = value

    # Don't forget the last section
    if current_section and current_dict:
        result[current_section] = current_dict

    return result


def find_sprint_status_file(project_path: str | Path) -> Path | None:
    """
    Find sprint-status.yaml in the project.

    Checks common locations:
    - _bmad-output/implementation-artifacts/sprint-status.yaml
    - docs/sprint-status.yaml
    """
    project_path = Path(project_path)

    locations = [
        project_path / "_bmad-output" / "implementation-artifacts" / "sprint-status.yaml",
        project_path / "docs" / "sprint-status.yaml",
    ]

    for loc in locations:
        if loc.exists():
            return loc

    return None


def load_sprint_status(project_path: str | Path) -> SprintStatus:
    """
    Read and parse sprint-status.yaml directly.

    Handles flat dict format:
        development_status:
          epic-1: in-progress
          1-1-project-setup: review

    Raises:
        FileNotFoundError: If sprint-status.yaml not found
        ValueError: If file format is invalid
    """
    project_path = Path(project_path)
    yaml_path = find_sprint_status_file(project_path)

    if yaml_path is None:
        raise FileNotFoundError(
            f"sprint-status.yaml not found in {project_path}. "
            "Run /bmad:bmm:workflows:sprint-planning to create it."
        )

    with open(yaml_path) as f:
        content = f.read()

    data = parse_simple_yaml(content)

    if not data:
        raise ValueError(f"Empty or invalid YAML in {yaml_path}")

    dev_status = data.get("development_status", {})

    if not dev_status or not isinstance(dev_status, dict):
        raise ValueError(f"No development_status section in {yaml_path}")

    # Separate epics, stories, and retrospectives
    epics: dict[str, str] = {}
    stories: dict[str, str] = {}

    for key, value in dev_status.items():
        if key.startswith("epic-") and not key.endswith("-retrospective"):
            epics[key] = value
        elif key.endswith("-retrospective"):
            # Skip retrospectives for now
            continue
        else:
            stories[key] = value

    # Count story statuses
    counts = {status: 0 for status in STORY_STATUSES}
    for status in stories.values():
        if status in counts:
            counts[status] += 1

    # Count epic statuses
    epic_counts = {status: 0 for status in EPIC_STATUSES}
    for status in epics.values():
        if status in epic_counts:
            epic_counts[status] += 1

    return SprintStatus(
        epics=epics,
        stories=stories,
        counts=counts,
        epic_counts=epic_counts,
        project=data.get("project", "Unknown"),
        generated=data.get("generated", "Unknown"),
    )


def get_next_action(
    status: SprintStatus, skip_stories: set[str] | None = None
) -> Action | None:
    """
    Compute next action using BMAD's priority logic.

    Priority (from BMAD sprint-status Step 3):
    1. in-progress → continue with dev-story
    2. review → code-review
    3. ready-for-dev → dev-story
    4. backlog → create-story
    5. All done → None

    Args:
        status: Sprint status data
        skip_stories: Set of story IDs to skip (e.g., already dispatched)
    """
    skip = skip_stories or set()

    # Sort stories by ID for consistent ordering
    sorted_stories = sorted(status.stories.items(), key=lambda x: x[0])

    # Priority 1: Continue in-progress stories
    for story_id, story_status in sorted_stories:
        if story_id in skip:
            continue
        if story_status == "in-progress":
            return Action("dev-story", story_id, "bmad:bmm:workflows:dev-story")

    # Priority 2: Review completed stories
    for story_id, story_status in sorted_stories:
        if story_id in skip:
            continue
        if story_status == "review":
            return Action("code-review", story_id, "bmad:bmm:workflows:code-review")

    # Priority 3: Start ready-for-dev stories
    for story_id, story_status in sorted_stories:
        if story_id in skip:
            continue
        if story_status == "ready-for-dev":
            return Action("dev-story", story_id, "bmad:bmm:workflows:dev-story")

    # Priority 4: Create stories from backlog
    for story_id, story_status in sorted_stories:
        if story_id in skip:
            continue
        if story_status == "backlog":
            return Action("create-story", story_id, "bmad:bmm:workflows:create-story")

    # All complete
    return None


def get_stories_by_status(status: SprintStatus) -> dict[str, list[str]]:
    """Group stories by their status for display."""
    by_status: dict[str, list[str]] = {s: [] for s in STORY_STATUSES}

    for story_id, story_status in sorted(status.stories.items()):
        if story_status in by_status:
            by_status[story_status].append(story_id)

    return by_status


def get_epic_for_story(story_id: str) -> str:
    """
    Derive epic ID from story ID.

    Example: "1-2-user-registration" → "epic-1"
    """
    parts = story_id.split("-")
    if parts and parts[0].isdigit():
        return f"epic-{parts[0]}"
    return "unknown"
