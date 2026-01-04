---
stepsCompleted: [1, 2, 3, 4]
status: complete
completedAt: '2026-01-04'
inputDocuments:
  - '_bmad-output/planning-artifacts/prd-bmad-dashboard.md'
  - '_bmad-output/planning-artifacts/architecture.md'
totalEpics: 5
totalStories: 16
---

# BMAD Dashboard - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for BMAD Dashboard, decomposing the requirements from the PRD and Architecture into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: User can view all active DevPods in a single unified display
FR2: System can auto-discover DevPods via naming convention without manual configuration
FR3: User can optionally override auto-discovery with explicit configuration
FR4: User can see which project/workspace each DevPod is working on
FR5: User can see current story assignment for each DevPod
FR6: User can see story status (done, running, needs-input, stale)
FR7: User can see time since last activity/heartbeat per DevPod
FR8: User can see task progress within a story (e.g., "3/7 tasks completed")
FR9: User can see the backlog of unassigned stories
FR10: System can detect idle DevPods (completed story, no current assignment)
FR11: System can detect when Claude is waiting for user input
FR12: User can see the specific question Claude is asking
FR13: User can see the session ID for resume operations
FR14: User can provide an answer to resume a paused session
FR15: System can generate copy-paste resume command with answer
FR16: System can detect stale workers (no heartbeat within threshold)
FR17: User can see visual indication of stale status
FR18: User can see suggested diagnostic actions for stale DevPods
FR19: User can see copy-paste ready dispatch commands for idle DevPods
FR20: User can see suggested next story to assign
FR21: User can see copy-paste ready resume commands
FR22: User can see command to attach to interactive tmux session
FR23: All generated commands use JSON output mode by default
FR24: User can launch a persistent TUI dashboard
FR25: User can quit the dashboard gracefully
FR26: User can refresh dashboard state manually
FR27: User can drill into detail view for specific DevPod
FR28: User can navigate back from detail view to main view
FR29: User can get one-shot status dump via CLI command
FR30: User can list discovered DevPods via CLI command
FR31: User can get output in JSON format for any CLI command
FR32: User can use shell completion for DevPod names and commands
FR33: User can install via npm within monorepo
FR34: User can run dashboard from any directory on host machine
FR35: System can read BMAD state files from DevPod workspaces on host filesystem

### NonFunctional Requirements

NFR1: Dashboard initial render completes within 2 seconds of launch
NFR2: Status refresh completes within 1 second
NFR3: CLI commands return within 500ms for status queries
NFR4: DevPod discovery completes within 3 seconds for up to 10 DevPods
NFR5: Stale detection has zero false negatives (never misses a stale DevPod)
NFR6: False positive rate for stale detection is acceptable (may flag active DevPod briefly after network hiccup)
NFR7: Dashboard gracefully handles unreachable DevPods without crashing
NFR8: Partial failures (one DevPod unreachable) do not block display of other DevPods
NFR9: Runs on macOS (Intel and Apple Silicon)
NFR10: Runs on Linux (Ubuntu 22.04+, Debian-based)
NFR11: Works with DevPod CLI for container discovery
NFR12: Correctly parses BMAD state files (sprint-status.yaml, .worker-state.yaml)
NFR13: Works with Claude CLI `--output-format json` responses
NFR14: Compatible with existing claude-instance tmux session naming
NFR15: Codebase is understandable by owner without extensive documentation
NFR16: Clear separation between TUI rendering, state aggregation, and command generation
NFR17: No external runtime dependencies beyond Node.js and npm packages
NFR18: Configuration schema is self-documenting (YAML with comments)

### Additional Requirements

**From Architecture - Starter Template:**
- Manual project setup with Ink + Commander (no scaffolding tool)
- First implementation story: project initialization
- Package added to existing claude-devcontainer monorepo

**From Architecture - Technical Patterns:**
- Parallel file reading with `Promise.allSettled` for error isolation
- DevPod CLI subprocess for discovery (`devpod list --output json`)
- Direct filesystem read from host for BMAD state files
- React function components with hooks (Ink pattern)
- CLI entry point with subcommand detection for TUI/CLI mode switching
- JSON output wrapper format with version, devpods, and errors fields
- Co-located tests next to source files (e.g., `discovery.test.ts` next to `discovery.ts`)

**From Architecture - Code Organization:**
- ~500 LOC target codebase
- Clear separation: cli.ts (entry), commands/ (CLI handlers), components/ (Ink), lib/ (business logic), types.ts
- Feature-based React components: Dashboard, WorkerList, WorkerDetail, StoryStatus, CommandPanel

**From Architecture - Implementation Constraints:**
- Use function declarations for components (not arrow functions)
- Interface names without "I" prefix (e.g., `DevPod` not `IDevPod`)
- Status indicators: ✓ (success), ● (running), ○ (idle), ✗ (error), ⚠ (warning)
- Error messages must include actionable suggestions

### FR Coverage Map

| FR | Epic | Description |
|----|------|-------------|
| FR1 | Epic 2 | View all DevPods unified |
| FR2 | Epic 2 | Auto-discover DevPods |
| FR3 | Epic 2 | Config override for discovery |
| FR4 | Epic 2 | See project/workspace per DevPod |
| FR5 | Epic 2 | Current story assignment |
| FR6 | Epic 2 | Story status display |
| FR7 | Epic 2 | Time since last activity |
| FR8 | Epic 3 | Task progress within story |
| FR9 | Epic 3 | Backlog of unassigned stories |
| FR10 | Epic 3 | Idle DevPod detection |
| FR11 | Epic 3 | Detect needs-input state |
| FR12 | Epic 3 | Show Claude's question |
| FR13 | Epic 3 | Session ID for resume |
| FR14 | Epic 4 | Provide answer to resume |
| FR15 | Epic 4 | Generate resume command |
| FR16 | Epic 3 | Detect stale workers |
| FR17 | Epic 3 | Visual stale indication |
| FR18 | Epic 3 | Diagnostic suggestions |
| FR19 | Epic 4 | Dispatch commands |
| FR20 | Epic 4 | Suggested next story |
| FR21 | Epic 4 | Resume commands |
| FR22 | Epic 4 | Tmux attach command |
| FR23 | Epic 4 | JSON output mode default |
| FR24 | Epic 2 | Launch persistent TUI |
| FR25 | Epic 2 | Quit gracefully |
| FR26 | Epic 5 | Manual refresh |
| FR27 | Epic 5 | Drill into detail view |
| FR28 | Epic 5 | Navigate back to main |
| FR29 | Epic 5 | CLI status dump |
| FR30 | Epic 5 | CLI list DevPods |
| FR31 | Epic 5 | JSON output format |
| FR32 | Epic 5 | Shell completion |
| FR33 | Epic 1 | Install via npm |
| FR34 | Epic 1 | Run from any directory |
| FR35 | Epic 2 | Read BMAD state files |

## Epic List

### Epic 1: Project Foundation & Code Quality
User can install the dashboard tool with production-grade code quality standards enforced from the start.

**FRs covered:** FR33, FR34
**NFRs addressed:** NFR9, NFR10, NFR15, NFR17

**Scope (adapted from ZookAnalytics standards):**
- Project structure: Package init, src/ layout per Architecture
- ESLint: Flat config with TypeScript strict, Unicorn, SonarJS, Perfectionist
- Prettier: Single quotes, consistent formatting
- TypeScript: Strict mode, Node.js target
- Commitlint: Conventional commits with type/scope rules
- Husky + lint-staged: Pre-commit hooks for lint, format, type-check
- pnpm Scripts: `check`, `fix`, `format`, `type-check`, `pre-commit`
- CI Workflow: Code quality checks on PR/push
- cspell: Spell checking for code and docs

### Epic 2: DevPod Discovery & Status Dashboard
User sees all DevPods with current status at a glance.

**FRs covered:** FR1, FR2, FR3, FR4, FR5, FR6, FR7, FR24, FR25, FR35
**NFRs addressed:** NFR1, NFR4, NFR7, NFR8, NFR11, NFR12, NFR15, NFR16

After this epic, users can:
- Launch dashboard and see all DevPods
- See story assignment and basic status per DevPod
- Auto-discover or manually configure DevPods
- Quit gracefully

### Epic 3: Progress Tracking & Problem Detection
User understands progress and knows which DevPods need attention.

**FRs covered:** FR8, FR9, FR10, FR11, FR12, FR13, FR16, FR17, FR18
**NFRs addressed:** NFR2, NFR5, NFR6, NFR14

After this epic, users can:
- See task progress within stories (e.g., "3/7 tasks")
- View backlog of unassigned stories
- Detect idle, needs-input, and stale DevPods
- See Claude's question when waiting for input
- See diagnostic suggestions for stale workers

### Epic 4: Actionable Commands
User can act immediately with ready-to-run commands.

**FRs covered:** FR14, FR15, FR19, FR20, FR21, FR22, FR23
**NFRs addressed:** NFR13

After this epic, users can:
- Get copy-paste dispatch commands for idle DevPods
- See suggested next story to assign
- Provide answers to resume paused sessions
- Get tmux attach commands
- All commands use JSON mode by default

### Epic 5: Enhanced Navigation & CLI Automation
User can explore details and script workflows.

**FRs covered:** FR26, FR27, FR28, FR29, FR30, FR31, FR32
**NFRs addressed:** NFR3, NFR18

After this epic, users can:
- Manually refresh dashboard
- Drill into detail view for specific DevPod
- Navigate back from detail to main view
- Use CLI commands for scripting (`status`, `list`)
- Get JSON output for automation
- Use shell completion

---

## Epic 1: Project Foundation & Code Quality

User can install the dashboard tool with production-grade code quality standards enforced from the start.

### Story 1.1: Initialize Package with TypeScript Configuration

As a **developer**,
I want **a properly configured npm package with TypeScript strict mode**,
So that **I can start building the dashboard with type safety from the start**.

**Acceptance Criteria:**

**Given** the monorepo root exists at `/workspace`
**When** I run `pnpm install` from the monorepo root
**Then** the `packages/bmad-dashboard` package is installed with all dependencies
**And** the package has the directory structure defined in Architecture:
```
packages/bmad-dashboard/
├── src/
│   ├── cli.ts
│   ├── commands/
│   ├── components/
│   ├── lib/
│   └── types.ts
├── bin/bmad-dashboard
├── package.json
└── tsconfig.json
```

**Given** the package is initialized
**When** I run `pnpm type-check` from the package directory
**Then** TypeScript compiles successfully with strict mode enabled
**And** the tsconfig.json targets Node.js 22 with ESM modules

**Given** the bin script exists
**When** I run `bmad-dashboard --version` from the host
**Then** the version from package.json is displayed

### Story 1.2: Configure ESLint, Prettier, and Spell Checking

As a **developer**,
I want **consistent code formatting and linting rules enforced**,
So that **code quality is maintained across all contributions**.

**Acceptance Criteria:**

**Given** the package is initialized
**When** I run `pnpm check:lint`
**Then** ESLint runs with the flat config format
**And** TypeScript strict type checking rules are enforced
**And** Unicorn, SonarJS, and Perfectionist plugins are configured
**And** React/Ink-specific rules are applied to component files

**Given** source files exist
**When** I run `pnpm check:format`
**Then** Prettier checks formatting with single quotes enabled
**And** the check passes for properly formatted files

**Given** source files with code style issues exist
**When** I run `pnpm fix`
**Then** ESLint auto-fixes what it can
**And** Prettier reformats all files
**And** the codebase is consistent

**Given** source files with typos exist
**When** I run `pnpm check:spellcheck`
**Then** cspell identifies spelling errors
**And** project-specific terms are whitelisted in cspell.config.yaml

### Story 1.3: Configure Pre-commit Hooks and CI Workflow

As a **developer**,
I want **automated quality gates on commit and PR**,
So that **code quality issues are caught before merge**.

**Acceptance Criteria:**

**Given** Husky is installed
**When** I make a git commit
**Then** lint-staged runs ESLint, Prettier, and type-check on staged files
**And** the commit is blocked if checks fail

**Given** Commitlint is configured
**When** I make a commit with message "added feature"
**Then** the commit is rejected with an error about conventional commit format
**And** a commit with "feat(dashboard): add worker list component" succeeds

**Given** the CI workflow exists at `.github/workflows/code-quality.yml`
**When** a PR is opened
**Then** the workflow runs `pnpm check` (lint, format, spellcheck, type-check)
**And** the PR title is validated against conventional commit format
**And** the workflow fails if any check fails

**Given** pnpm scripts are configured
**When** I run `pnpm check`
**Then** all quality checks run in parallel (lint, format, spellcheck, type-check)
**And** the command exits with failure if any check fails

---

## Epic 2: DevPod Discovery & Status Dashboard

User sees all DevPods with current status at a glance.

### Story 2.1: DevPod Discovery via CLI Subprocess

As a **developer**,
I want **the dashboard to automatically discover my running DevPods**,
So that **I don't need to manually configure each DevPod**.

**Acceptance Criteria:**

**Given** DevPod CLI is installed on the host
**When** the discovery module runs
**Then** it executes `devpod list --output json` as a subprocess
**And** parses the JSON response into a `DevPod[]` array
**And** extracts name, status, and workspace path for each DevPod

**Given** DevPod CLI returns an error or is not installed
**When** the discovery module runs
**Then** it returns an empty array with an error object
**And** does not crash the application

**Given** an optional config file exists at `~/.bmad-dashboard.yaml`
**When** the discovery module runs
**Then** it applies include/exclude patterns from the config
**And** filters DevPods by naming convention (e.g., `devpod-*`)

**Given** no config file exists
**When** the discovery module runs
**Then** it uses default discovery (all DevPods from `devpod list`)
**And** operates in zero-config mode

### Story 2.2: BMAD State File Reading

As a **developer**,
I want **the dashboard to read BMAD state files from each DevPod workspace**,
So that **I can see the current story and status for each worker**.

**Acceptance Criteria:**

**Given** a DevPod with a valid workspace path
**When** the state reader runs
**Then** it reads `_bmad-output/sprint-status.yaml` from the workspace
**And** it reads `.worker-state.yaml` from the workspace root
**And** parses both files using a YAML parser

**Given** a state file does not exist
**When** the state reader runs
**Then** it returns a partial state with available data
**And** marks missing data as `unknown` status
**And** does not crash or block other DevPods

**Given** multiple DevPods exist
**When** the state aggregator runs
**Then** it reads all DevPod states in parallel using `Promise.allSettled`
**And** collects successful reads into `devpods[]` array
**And** collects failed reads into `errors[]` array
**And** completes within 2 seconds (NFR1)

**Given** a YAML file is malformed
**When** the state reader parses it
**Then** it catches the parse error
**And** returns error state for that DevPod
**And** continues processing other DevPods

### Story 2.3: Basic TUI Dashboard Shell

As a **developer**,
I want **to launch a persistent terminal dashboard**,
So that **I can monitor DevPods without running repeated commands**.

**Acceptance Criteria:**

**Given** the package is installed
**When** I run `bmad-dashboard` with no arguments
**Then** Ink renders a persistent TUI in the terminal
**And** the dashboard displays a header with project name
**And** the dashboard shows a loading spinner during initial data fetch

**Given** the TUI is running
**When** I press `q` or `Ctrl+C`
**Then** the dashboard exits gracefully
**And** the terminal is restored to normal state
**And** no error messages are displayed

**Given** the TUI is running
**When** I run `bmad-dashboard status` in another terminal
**Then** Commander routes to the CLI subcommand handler
**And** the subcommand executes without launching TUI
**And** returns text output and exits

**Given** the CLI entry point
**When** mode detection runs
**Then** no arguments → TUI mode (Ink render)
**And** with subcommand → CLI mode (execute and exit)

### Story 2.4: Worker List with Status Display

As a **developer**,
I want **to see all DevPods with their current story and status**,
So that **I know what each worker is doing at a glance**.

**Acceptance Criteria:**

**Given** the dashboard has loaded DevPod data
**When** the WorkerList component renders
**Then** each DevPod is displayed as a row
**And** each row shows: DevPod name, project/workspace, current story, status, last activity

**Given** DevPod status is one of: done, running, needs-input, stale, idle
**When** the StatusBadge component renders
**Then** it displays the appropriate symbol:
- `✓` for done
- `●` for running
- `⏸` for needs-input
- `⚠` for stale
- `○` for idle

**Given** a DevPod has last activity timestamp
**When** the row renders
**Then** it displays relative time (e.g., "2h ago", "12m ago")
**And** timestamps older than the stale threshold show warning styling

**Given** one DevPod is unreachable (error state)
**When** the WorkerList renders
**Then** it displays available DevPods normally
**And** shows error indicator for the unreachable DevPod
**And** includes error message with suggestion

**Given** the dashboard displays all DevPods
**When** the user views the list
**Then** the unified display satisfies FR1
**And** story assignment is visible (FR5)
**And** status is visible (FR6)
**And** time since activity is visible (FR7)

---

## Epic 3: Progress Tracking & Problem Detection

User understands progress and knows which DevPods need attention.

### Story 3.1: Task Progress, Backlog, and Idle Detection

As a **developer**,
I want **to see task progress within stories and the backlog of remaining work**,
So that **I understand how much work is done and what remains**.

**Acceptance Criteria:**

**Given** a DevPod is working on a story with tasks
**When** the state reader parses the worker state
**Then** it extracts task progress (e.g., "3/7 tasks completed")
**And** the WorkerList displays progress as "3/7" next to the story

**Given** the sprint-status.yaml contains stories
**When** the state aggregator runs
**Then** it identifies stories not assigned to any DevPod
**And** returns them as the backlog array

**Given** backlog stories exist
**When** the dashboard renders
**Then** it displays a "Backlog" section below the worker list
**And** shows story IDs of unassigned stories (e.g., "1-4-tests, 2-3-validation")

**Given** a DevPod has completed its story and has no current assignment
**When** the state reader evaluates status
**Then** it marks the DevPod as `idle`
**And** the StatusBadge shows `○` (idle indicator)

**Given** the dashboard shows idle DevPods and backlog
**When** the user views the display
**Then** they can identify which DevPods can take new work
**And** see which stories are available to assign

### Story 3.2: Needs-Input Detection and Question Display

As a **developer**,
I want **to see when Claude is waiting for my input and what question it's asking**,
So that **I can quickly unblock paused sessions**.

**Acceptance Criteria:**

**Given** a DevPod's worker state indicates `needs-input` status
**When** the state reader parses the state
**Then** it extracts the `needs-input` flag
**And** extracts the pending question text
**And** extracts the session ID for resume operations

**Given** a DevPod is in needs-input state
**When** the WorkerList renders
**Then** it displays `⏸` status indicator
**And** shows "needs-input" with time waiting (e.g., "needs-input (6h)")

**Given** a DevPod is in needs-input state
**When** the user views the worker row
**Then** they can see a preview of Claude's question
**And** the session ID is available for resume commands

**Given** Claude's question has multiple choice options
**When** the question is displayed
**Then** the options are shown (e.g., "(1) Mock database (2) Use test container")
**And** the user understands what input is expected

**Given** the dashboard detects needs-input state
**When** compared to other statuses
**Then** needs-input is prioritized for visibility (shown prominently)
**And** the user's attention is drawn to blocked workers

### Story 3.3: Stale Detection and Diagnostics

As a **developer**,
I want **to know when a DevPod has gone stale and what I can do about it**,
So that **I can investigate and recover stuck workers**.

**Acceptance Criteria:**

**Given** a DevPod has a heartbeat timestamp in worker state
**When** the heartbeat module evaluates staleness
**Then** it compares the timestamp to current time
**And** marks as stale if older than the threshold (default: 5 minutes)

**Given** a DevPod is marked stale
**When** the WorkerList renders
**Then** it displays `⚠` status indicator with warning styling
**And** shows "stale" with time since last activity

**Given** stale detection is running
**When** evaluating all DevPods
**Then** there are zero false negatives (NFR5)
**And** every actually-stale DevPod is detected

**Given** a DevPod is stale
**When** the dashboard displays the worker
**Then** it includes a diagnostic suggestion
**And** the suggestion is actionable (e.g., "Check if DevPod is running with `devpod list`")

**Given** diagnostic suggestions exist
**When** displayed to the user
**Then** they follow the error message format:
```
⚠ devpod-3: No heartbeat for 15m
  Suggestion: Check if DevPod is running with `devpod list`
```

**Given** a DevPod briefly loses connectivity then recovers
**When** the next state read succeeds
**Then** the stale status is cleared
**And** the DevPod shows its actual current status

---

## Epic 4: Actionable Commands

User can act immediately with ready-to-run commands.

### Story 4.1: Dispatch Command Generation

As a **developer**,
I want **copy-paste ready commands to dispatch work to idle DevPods**,
So that **I can assign new stories without manual command construction**.

**Acceptance Criteria:**

**Given** a DevPod is idle and backlog stories exist
**When** the CommandPanel renders for that DevPod
**Then** it displays a dispatch command in copy-paste format
**And** the command follows the pattern:
```
devpod ssh <devpod-name> -- claude -p "/bmad:bmm:workflows:dev-story <story-id>" --output-format json
```

**Given** multiple stories exist in the backlog
**When** the dashboard suggests next story
**Then** it recommends the highest-priority unassigned story
**And** displays "Next suggested: <devpod> is idle → assign <story-id>"

**Given** a dispatch command is generated
**When** the user copies and executes it
**Then** the command works without any manual editing
**And** uses `--output-format json` by default (FR23)

**Given** no backlog stories exist
**When** the CommandPanel renders for an idle DevPod
**Then** it shows "No stories in backlog"
**And** does not display a dispatch command

**Given** the command generator module
**When** generating any dispatch command
**Then** it escapes special characters properly
**And** handles DevPod names with hyphens correctly

### Story 4.2: Resume Command Generation

As a **developer**,
I want **to resume paused sessions with a single command**,
So that **I can quickly unblock workers waiting for input**.

**Acceptance Criteria:**

**Given** a DevPod is in needs-input state with a session ID
**When** the CommandPanel renders
**Then** it displays a resume command template:
```
devpod ssh <devpod-name> -- claude -p "<answer>" --resume "<session-id>" --output-format json
```

**Given** the user has an answer for Claude's question
**When** they want to provide input
**Then** they replace `<answer>` with their response (e.g., "1" for option 1)
**And** the command resumes the session with that answer

**Given** a simple choice question (e.g., "1, 2, or 3")
**When** the dashboard displays the resume command
**Then** it pre-fills common answers as options
**And** shows: "Resume with: [1] [2] [3]" with corresponding commands

**Given** a resume command is executed
**When** Claude receives the answer
**Then** the session continues from where it paused
**And** the dashboard can detect the status change on next refresh

**Given** the session ID is available
**When** the resume command is generated
**Then** the session ID is included in the `--resume` flag
**And** the command is copy-paste ready

### Story 4.3: Interactive Mode Command

As a **developer**,
I want **to attach to a DevPod's tmux session for complex conversations**,
So that **I can have back-and-forth dialogue when simple answers aren't enough**.

**Acceptance Criteria:**

**Given** a DevPod has an active tmux session
**When** the user wants interactive mode
**Then** the CommandPanel shows an "Interactive Mode" command:
```
devpod ssh <devpod-name> -- tmux attach -t <session-name>
```

**Given** the user executes the interactive command
**When** they attach to the tmux session
**Then** they see the full Claude conversation
**And** can type responses directly
**And** have full back-and-forth capability

**Given** a DevPod is in needs-input state
**When** the CommandPanel renders
**Then** it shows both options:
  - Quick resume command (for simple answers)
  - Interactive mode command (for complex situations)

**Given** the tmux session naming convention exists
**When** generating the attach command
**Then** it uses the correct session name format
**And** is compatible with existing claude-instance tmux integration (NFR14)

**Given** the user is in interactive mode
**When** they want to detach
**Then** standard tmux detach (Ctrl+B, D) works
**And** the session continues running

---

## Epic 5: Enhanced Navigation & CLI Automation

User can explore details and script workflows.

### Story 5.1: Manual Refresh and TUI Navigation

As a **developer**,
I want **to refresh the dashboard and drill into DevPod details**,
So that **I can explore specific workers and get updated information**.

**Acceptance Criteria:**

**Given** the TUI dashboard is running
**When** I press `r` or `R`
**Then** the dashboard triggers a manual refresh
**And** displays a refresh indicator while loading
**And** updates all DevPod states

**Given** the dashboard refresh completes
**When** new data is loaded
**Then** the display updates within 1 second (NFR2)
**And** the user sees current state

**Given** the WorkerList is displayed
**When** I use arrow keys to select a DevPod and press Enter
**Then** the view switches to WorkerDetail for that DevPod
**And** shows expanded information (full question, all commands, history)

**Given** the WorkerDetail view is displayed
**When** I press `Escape` or `Backspace`
**Then** the view returns to the main WorkerList
**And** my previous selection is preserved

**Given** the TUI navigation
**When** the user interacts with keyboard
**Then** navigation is intuitive (arrows, enter, escape)
**And** follows common TUI conventions

### Story 5.2: CLI Status and List Commands

As a **developer**,
I want **CLI commands that output status for scripting**,
So that **I can automate workflows and integrate with other tools**.

**Acceptance Criteria:**

**Given** the dashboard is installed
**When** I run `bmad-dashboard status`
**Then** it outputs a one-shot status dump of all DevPods
**And** exits immediately (no persistent TUI)
**And** returns within 500ms (NFR3)

**Given** I run `bmad-dashboard status`
**When** the command completes
**Then** output shows each DevPod with: name, story, status, last activity
**And** format is human-readable plain text by default

**Given** I run `bmad-dashboard list`
**When** the command completes
**Then** it outputs discovered DevPod names
**And** can be piped to other commands (e.g., `xargs`)

**Given** any CLI command
**When** I add the `--json` flag
**Then** output is structured JSON following the format:
```json
{
  "version": "1",
  "devpods": [...],
  "errors": [...]
}
```
**And** can be parsed with `jq` or similar tools

**Given** JSON output is requested
**When** there are errors for some DevPods
**Then** successful DevPods appear in `devpods` array
**And** failed DevPods appear in `errors` array with details

**Given** scripting use cases
**When** I run:
```bash
bmad-dashboard status --json | jq '.devpods[] | select(.status == "idle")'
```
**Then** I get filtered results for automation

### Story 5.3: Shell Completion

As a **developer**,
I want **shell completion for dashboard commands**,
So that **I can quickly tab-complete DevPod names and subcommands**.

**Acceptance Criteria:**

**Given** bash or zsh shell
**When** I run `bmad-dashboard completion`
**Then** it outputs shell completion script
**And** includes instructions for installation

**Given** completion is installed
**When** I type `bmad-dashboard <TAB>`
**Then** available subcommands are shown (status, list, dispatch, resume)

**Given** completion is installed
**When** I type `bmad-dashboard dispatch <TAB>`
**Then** discovered DevPod names are suggested
**And** completion queries current DevPod list dynamically

**Given** completion is installed
**When** I type `bmad-dashboard dispatch devpod-1 <TAB>`
**Then** available story IDs from backlog are suggested

**Given** the completion installation
**When** user runs `bmad-dashboard completion >> ~/.bashrc`
**Then** completion is installed for future sessions
**And** works after shell restart

**Given** Commander CLI framework
**When** implementing completion
**Then** use Commander's built-in completion support
**And** extend with dynamic DevPod/story completion
