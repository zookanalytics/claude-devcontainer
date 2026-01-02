# BMAD Orchestrator

A Claude Code plugin that automates BMAD (Breakthrough Method for Agile AI-Driven Development) workflow orchestration for AI-driven software development.

## What It Does

- **Phase Detection**: Automatically detects when Claude completes a workflow phase (story creation, development, code review)
- **Story Progression**: Advances stories through the BMAD lifecycle (backlog → ready-for-dev → in-progress → review → done)
- **Multi-Instance Coordination**: Dispatches work to devcontainer instances and tracks progress
- **Status Dashboard**: Terminal-based view of sprint progress and next actions

## Architecture

bmad-cli has two operating modes with different installation requirements:

| Commands | Runs Where | Purpose |
|----------|------------|---------|
| `next`, `restart`, `menu` (dispatch) | **Host only** | Orchestrate work across multiple containers |
| `run-story`, `run-epic`, `menu` (execute) | **Container only** | Execute workflows inside devcontainer |
| `status`, `audit` | Either | View status, check health |

The orchestrator commands require Docker access to discover and dispatch to containers. The executor commands require being inside a devcontainer with Claude Code installed.

## Installation

### Host Installation (for orchestration)

Install globally on your host machine to dispatch work to containers:

```bash
npm install -g @zookanalytics/bmad-orchestrator
```

This provides the `bmad-cli` command with orchestration capabilities:
- `bmad-cli next` - Dispatch next story to an available container
- `bmad-cli restart <id>` - Resume a stale dispatch
- `bmad-cli menu` - Interactive orchestration menu

### Container Installation (for execution)

When using the `claude-devcontainer` Docker image, bmad-cli is pre-installed at `/usr/local/bin/bmad-cli`.

To enable the Stop hook for phase detection, add to your `.devcontainer/devcontainer.json`:

```json
{
  "image": "ghcr.io/zookanalytics/claude-devcontainer:latest",
  "containerEnv": {
    "ENABLE_BMAD_ORCHESTRATOR": "true"
  }
}
```

This enables:
- `bmad-cli run-story <id>` - Run a story through all phases
- `bmad-cli run-epic <id>` - Run all stories in an epic
- Phase completion detection via Stop hook

### As a Claude Code Plugin (alternative)

If not using the devcontainer image, add to your project's `.claude/settings.json`:

```json
{
  "enabledPlugins": {
    "bmad-orchestrator@claude-devcontainer": true
  },
  "extraKnownMarketplaces": {
    "claude-devcontainer": {
      "source": {
        "source": "directory",
        "path": "/path/to/claude-devcontainer"
      }
    }
  }
}
```

## Usage

### Interactive Menu (Recommended)

```bash
bmad-cli              # Opens interactive menu with smart defaults
```

The menu adapts based on environment:
- **On host**: Shows orchestration options (dispatch, restart, audit)
- **In container**: Shows execution options (run story, run epic)

### Host Commands (Orchestration)

Run these on your host machine to manage work across containers:

```bash
bmad-cli              # Interactive orchestration menu
bmad-cli next         # Dispatch next story to an available container
bmad-cli restart ID   # Resume a stale/dead dispatch
bmad-cli audit        # Check for stale dispatches, optionally fix
bmad-cli status       # Show sprint status and next action
```

### Container Commands (Execution)

Run these inside a devcontainer to execute workflows:

```bash
bmad-cli              # Interactive execution menu
bmad-cli run-story ID # Run a story through all phases to completion
bmad-cli run-epic ID  # Run all stories in an epic sequentially
bmad-cli status       # Show sprint status
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
