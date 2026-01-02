# BMAD Orchestrator

A Claude Code plugin that automates BMAD (Breakthrough Method for Agile AI-Driven Development) workflow orchestration for AI-driven software development.

## What It Does

- **Phase Detection**: Automatically detects when Claude completes a workflow phase (story creation, development, code review)
- **Story Progression**: Advances stories through the BMAD lifecycle (backlog → ready-for-dev → in-progress → review → done)
- **Multi-Instance Coordination**: Dispatches work to devcontainer instances and tracks progress
- **Status Dashboard**: Terminal-based view of sprint progress and next actions

## Installation

### As a Claude Code Plugin

Add to your project's `.claude/settings.json`:

```json
{
  "enabledPlugins": {
    "bmad-orchestrator@your-marketplace": true
  },
  "extraKnownMarketplaces": {
    "your-marketplace": {
      "source": {
        "source": "github",
        "repo": "yourorg/bmad-orchestrator"
      }
    }
  }
}
```

### Manual Installation

1. Clone this repository
2. Add the hook to your project's `.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/bmad-orchestrator/hooks/scripts/bmad-phase-complete.sh"
          }
        ]
      }
    ]
  }
}
```

3. Add `scripts/` to your PATH or create a symlink to `scripts/bmad-cli`

## Usage

### Interactive Menu (Recommended)

```bash
bmad-cli              # Opens interactive menu with smart defaults
```

### Commands

```bash
bmad-cli status       # Show sprint status and next action
bmad-cli next         # Dispatch next work to an instance (host only)
bmad-cli run-story ID # Run a story to completion (devcontainer only)
bmad-cli run-epic ID  # Run an epic to completion (devcontainer only)
bmad-cli audit        # Check for stale dispatches
bmad-cli restart ID   # Resume a stale dispatch
```

## How It Works

### Phase Completion Detection

1. When a BMAD workflow runs, the orchestrator creates a lock file tracking the story and starting status
2. A Stop hook fires when Claude stops responding
3. The hook compares the starting status against current `sprint-status.yaml`
4. If status changed, a signal file is written
5. The executor detects the signal and terminates Claude gracefully to proceed to the next phase

### Story Lifecycle

```
backlog → ready-for-dev → in-progress → review → done
```

Each transition triggers the appropriate BMAD workflow:
- `backlog → ready-for-dev`: create-story
- `ready-for-dev → in-progress`: dev-story
- `in-progress → review`: dev-story completion
- `review → done`: code-review

## Requirements

- Python 3.10+
- Claude Code CLI
- BMAD Method installed in your project
- `jq` for JSON parsing in hooks (fallback to grep if unavailable)

## Project Structure

```
bmad-orchestrator/
├── plugin.json           # Claude Code plugin metadata
├── marketplace.json      # Plugin marketplace entry
├── hooks/
│   ├── hooks.json        # Hook definitions
│   └── scripts/
│       └── bmad-phase-complete.sh
├── scripts/
│   ├── bmad-cli          # CLI entry point
│   └── bmad/
│       ├── __init__.py
│       ├── cli.py        # Command implementations
│       ├── status.py     # Sprint status reader
│       └── executor.py   # Workflow execution
└── docs/
    ├── research/         # Design research and proposals
    └── implementation/   # Technical specifications
```

## License

MIT
