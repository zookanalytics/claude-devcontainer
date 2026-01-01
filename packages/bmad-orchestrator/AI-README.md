# AI-README.md

This file provides guidance to AI Agents (Claude Code, Gemini CLI) when working with code in this repository.

## About This Project

**BMAD Orchestrator** is a Claude Code plugin that automates BMAD workflow orchestration. It provides:

- Phase completion detection via Stop hooks
- Story lifecycle management
- Multi-instance dispatch coordination
- Sprint status tracking

## Project Structure

```
scripts/bmad/           # Core Python module
  cli.py                # CLI commands (menu, status, next, run-story, run-epic)
  status.py             # Sprint status parsing and priority logic
  executor.py           # Workflow execution with PTY and signal detection
hooks/scripts/          # Shell scripts for Claude Code hooks
  bmad-phase-complete.sh  # Stop hook for phase detection
docs/                   # Documentation
  research/             # Design documents and research
  implementation/       # Technical specifications
```

## Key Concepts

### Lock Files (`.claude/.bmad-running/*.json`)
Track actively running story work. Contains:
- `story_id`: Which story is being worked on
- `starting_status`: Status when phase began (for completion detection)
- `pid`: Process ID of the running command

### Signal File (`.claude/.bmad-phase-signal.json`)
Written by Stop hook when phase completes. Contains:
- `story_id`: Which story
- `from_status` / `to_status`: Status transition
- `timestamp`: When detected

### Dispatch File (`.claude/.bmad-dispatched.json`)
Tracks work sent to devcontainer instances. Used for:
- Preventing duplicate dispatches
- Detecting stale/dead work
- Enabling restart functionality

## Development Commands

This project uses only Python stdlib (no external dependencies).

```bash
# Run CLI directly
./scripts/bmad-cli status

# Run tests (when added)
python -m pytest tests/
```

## Key Design Decisions

1. **No YAML Library**: Uses simple custom parser to avoid dependencies
2. **PTY Execution**: Full terminal transparency for interactive Claude sessions
3. **Signal-Based Termination**: Stop hook + signal file for clean phase transitions
4. **Status-Based Detection**: Compares status file changes rather than LLM output parsing

## Files to Modify

| Task | Files |
|------|-------|
| Add CLI command | `scripts/bmad/cli.py` |
| Change priority logic | `scripts/bmad/status.py` |
| Modify execution flow | `scripts/bmad/executor.py` |
| Update hook behavior | `hooks/scripts/bmad-phase-complete.sh` |

## Status File Locations

The orchestrator checks these locations for `sprint-status.yaml`:
1. `_bmad-output/implementation-artifacts/sprint-status.yaml`
2. `docs/sprint-status.yaml`
