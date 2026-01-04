---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
status: complete
completedAt: '2026-01-04'
inputDocuments:
  - '_bmad-output/planning-artifacts/prd-bmad-dashboard.md'
  - '_bmad-output/planning-artifacts/research/technical-ai-dev-environment-tools-research-2026-01-03.md'
  - '_bmad-output/planning-artifacts/research/technical-nimbalyst-deep-dive-research-2026-01-03.md'
  - '_bmad-output/planning-artifacts/research/technical-claude-discord-integration-research-2026-01-03.md'
  - '_bmad-output/planning-artifacts/research/technical-state-management-devcontainers-research-2026-01-03.md'
  - '_bmad-output/planning-artifacts/research/prototype-decision.md'
  - '_bmad-output/planning-artifacts/research/auto-claude-patterns.md'
  - 'docs/project-context.md'
  - 'docs/architecture.md'
  - 'docs/technology-stack.md'
workflowType: 'architecture'
project_name: 'BMAD Dashboard'
user_name: 'Node'
date: '2026-01-04'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
35 FRs spanning DevPod discovery, story visibility, needs-input handling, stale detection, command generation, TUI dashboard, CLI commands, and configuration. Core value proposition: unified visibility across all DevPods with actionable next-step commands.

**Non-Functional Requirements:**
18 NFRs with emphasis on:
- Performance: <2s render, <1s refresh, <500ms CLI response
- Reliability: Zero false negatives on stale detection
- Platform: macOS + Linux (Intel + Apple Silicon)
- Maintainability: Clear separation, understandable without extensive docs

**Scale & Complexity:**
- Primary domain: CLI + TUI Developer Tool
- Complexity level: Medium
- Estimated architectural components: 6-8 core modules
- Target codebase: ~500 LOC (lean orchestration)

### Technical Constraints & Dependencies

| Constraint | Description |
|------------|-------------|
| Host-based execution | Dashboard runs on host machine, not inside containers |
| Read-only orchestrator | Aggregates state without modifying DevPod files |
| Brownfield integration | Extends existing claude-devcontainer monorepo |
| Git-native state | Uses existing YAML files, no new databases |
| DevPod CLI dependency | Relies on `devpod list` for container discovery |

### Pre-Validated Decisions (From Research)

| Component | Decision | Rationale |
|-----------|----------|-----------|
| Orchestration SDK | Claude Agent SDK | 4.94/5 score, <30 LOC wrapper |
| Container Layer | DevPod (coexist) | Full lifecycle, provider system |
| State Architecture | Git-native | Zero infrastructure, BMAD unchanged |
| Patterns | Job Tracking + Events | From Auto-Claude analysis |

### Cross-Cutting Concerns

1. **Error Resilience** - Partial failures (one DevPod unreachable) must not block other DevPods
2. **Heartbeat Management** - Consistent timeout thresholds across detection and display
3. **State Consistency** - Eventual consistency acceptable; git fetch for committed state
4. **Command Generation** - All generated commands must be copy-paste ready without editing

## Starter Template Evaluation

### Primary Technology Domain

CLI Tool + TUI (Developer Tooling) based on project requirements analysis.

### Starter Options Considered

#### TUI Frameworks

| Option | Status | Verdict |
|--------|--------|---------|
| **Ink** | Active, React-based | ✅ SELECTED - Used by Claude Code, Gemini CLI |
| **blessed-contrib** | Inactive since 2015 | ❌ REJECTED - Unmaintained, security risk |

#### CLI Frameworks

| Option | Weekly Downloads | Verdict |
|--------|-----------------|---------|
| **Commander** | 238M | ✅ SELECTED - Lightweight, fits ~500 LOC target |
| **Yargs** | 138M | ❌ Overkill for simple subcommands |
| **oclif** | 173K | ❌ Enterprise-scale, too heavy |

### Selected Stack

**TUI:** Ink (React for CLIs)
**CLI:** Commander (lightweight argument parsing)
**Scaffolding:** Manual setup (brownfield integration)

**Rationale:**
1. Ink is actively maintained and used by Claude Code itself
2. Commander is lightweight and sufficient for 5 subcommands
3. Manual setup preferred - integrates with existing monorepo patterns

### Initialization Approach

No scaffolding tool needed. Add package to existing monorepo:

```bash
mkdir -p packages/bmad-dashboard/src
cd packages/bmad-dashboard
pnpm init
pnpm add ink ink-spinner react commander
pnpm add -D typescript @types/react tsx
```

### Architectural Decisions Provided by Stack

**Language & Runtime:**
- TypeScript with strict mode (aligns with monorepo)
- Node.js 22 (from project context)
- ESM modules

**UI Rendering:**
- Ink for terminal rendering (Flexbox via Yoga)
- React functional components with hooks
- ink-spinner for loading states

**CLI Structure:**
- Commander for argument parsing
- Subcommand pattern: `bmad-dashboard [command] [options]`
- JSON output mode via `--json` flag

**Code Organization:**
```
packages/bmad-dashboard/
├── src/
│   ├── cli.ts           # Commander setup, entry point
│   ├── commands/        # Subcommand handlers
│   ├── components/      # Ink React components
│   ├── lib/             # Business logic
│   │   ├── discovery.ts # DevPod discovery
│   │   ├── state.ts     # YAML state reading
│   │   └── commands.ts  # Command generation
│   └── types.ts         # TypeScript interfaces
├── package.json
└── tsconfig.json
```

**Note:** Project initialization should be the first implementation story.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- State reading architecture (parallel with error isolation)
- DevPod integration method (CLI subprocess)
- CLI/TUI mode switching pattern

**Important Decisions (Shape Architecture):**
- Component architecture (feature-based)
- Output formatting (text + JSON flag)
- Error handling strategy (graceful degradation)

**Deferred Decisions (Post-MVP):**
- File watching for real-time updates (Phase 2)
- Retry with backoff for transient failures (Phase 2)
- Additional output formats (Phase 2)

### State Reading Architecture

| Aspect | Decision |
|--------|----------|
| **Pattern** | Parallel file reading with `Promise.allSettled` |
| **Error Isolation** | Per-DevPod - one failure doesn't block others |
| **Data Sources** | GitHub (git fetch) + DevPod filesystems |
| **Rationale** | Meets <2s render NFR, aligns with git-native research |

### Component Architecture

| Aspect | Decision |
|--------|----------|
| **Pattern** | Feature-based React components |
| **Structure** | Dashboard → WorkerList, WorkerDetail, StoryStatus, CommandPanel |
| **Shared** | StatusBadge, Spinner utilities |
| **Rationale** | Fits ~500 LOC target, clear separation of concerns |

### CLI/TUI Mode Switching

| Aspect | Decision |
|--------|----------|
| **Pattern** | Subcommand detection at entry point |
| **No args** | Launch persistent TUI dashboard |
| **With subcommand** | Execute CLI command and exit |
| **Rationale** | Matches PRD, intuitive UX (like htop, docker) |

### Output Formatting

| Aspect | Decision |
|--------|----------|
| **Default** | Human-readable plain text |
| **Flag** | `--json` for structured JSON output |
| **Use Case** | Scripting with jq, pipeline integration |
| **Rationale** | Covers both interactive and automation needs |

### DevPod Integration

| Aspect | Decision |
|--------|----------|
| **Discovery** | `devpod list --output json` subprocess |
| **State Reading** | Direct filesystem read from host |
| **Files** | `_bmad-output/sprint-status.yaml`, `.worker-state.yaml` |
| **Rationale** | Uses stable DevPod CLI interface, not internals |

### Error Handling & Resilience

| Aspect | Decision |
|--------|----------|
| **Pattern** | Graceful degradation with Promise.allSettled |
| **Isolation** | Errors contained per DevPod |
| **Display** | Show available data + error indicators for failures |
| **Rationale** | Required by NFR7-8, keeps dashboard functional |

### Decision Impact Analysis

**Implementation Sequence:**
1. DevPod discovery (foundation)
2. State reading with error isolation
3. CLI entry point with subcommand detection
4. Ink components (feature-based)
5. Output formatting (text + JSON)

**Cross-Component Dependencies:**
- State reading depends on DevPod discovery
- Components consume state reading output
- CLI/TUI switching gates component rendering
- Error handling spans all data-fetching code

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**6 critical conflict points identified** where AI agents could make different choices.

### Naming Patterns

**File Naming:**

| Type | Pattern | Example |
|------|---------|---------|
| React Components | PascalCase matching export | `WorkerList.tsx` → `export function WorkerList` |
| Utilities/Lib | lowercase with hyphens if needed | `discovery.ts`, `command-generator.ts` |
| Types file | lowercase | `types.ts` |
| Test files | `.test.ts` suffix | `discovery.test.ts` |

**TypeScript Naming:**

| Type | Pattern | Example |
|------|---------|---------|
| Interfaces | PascalCase, no prefix | `interface DevPod { ... }` |
| Types | PascalCase, no prefix | `type Status = 'running' \| 'idle'` |
| Enums | PascalCase | `enum WorkerPhase { ... }` |
| Constants | SCREAMING_SNAKE_CASE | `const DEFAULT_TIMEOUT = 5000` |

### Structure Patterns

**Test Organization:**
- Co-located tests next to source files
- Pattern: `src/lib/discovery.ts` → `src/lib/discovery.test.ts`
- Rationale: Easy to find, visible when browsing code

**Component Organization:**
```
src/
├── cli.ts                    # Entry point
├── commands/                 # CLI subcommand handlers
│   ├── status.ts
│   └── list.ts
├── components/               # Ink React components
│   ├── Dashboard.tsx
│   ├── WorkerList.tsx
│   └── shared/
│       └── StatusBadge.tsx
├── lib/                      # Business logic
│   ├── discovery.ts
│   ├── discovery.test.ts     # Co-located test
│   └── state.ts
└── types.ts                  # Shared type definitions
```

### Format Patterns

**JSON Output Structure:**

All `--json` output follows this wrapper:
```json
{
  "version": "1",
  "devpods": [
    {"name": "devpod-1", "status": "running", "story": "1-3-auth"}
  ],
  "errors": [
    {"devpod": "devpod-3", "error": "unreachable"}
  ]
}
```

| Field | Purpose |
|-------|---------|
| `version` | Schema version for future compatibility |
| `devpods` | Successfully read DevPod data |
| `errors` | Failed DevPods with error details |

**Date/Time Format:**
- All timestamps: ISO 8601 (`2026-01-04T10:30:00Z`)
- Relative times in TUI: Human-friendly (`2h ago`, `12m ago`)

### Communication Patterns

**Error Message Format:**
```
✗ {devpod}: {error message}
  Suggestion: {actionable recovery step}
```

Example:
```
✗ devpod-3: Connection timed out after 5s
  Suggestion: Check if DevPod is running with `devpod list`
```

**Status Indicators:**

| Symbol | Meaning |
|--------|---------|
| `✓` | Success/Complete |
| `●` | In progress/Running |
| `○` | Pending/Idle |
| `✗` | Error/Failed |
| `⚠` | Warning/Needs attention |

### Process Patterns

**React/Ink Components:**
- Use function components with hooks (not class components)
- Use `function ComponentName()` syntax (not arrow functions for top-level)
- Props interface defined inline or in `types.ts` for shared types

```typescript
// Correct pattern
interface WorkerListProps {
  devpods: DevPod[];
  onSelect: (devpod: DevPod) => void;
}

function WorkerList({ devpods, onSelect }: WorkerListProps) {
  const [selected, setSelected] = useState(0);
  return <Box>...</Box>;
}
```

**State Management:**
- Use React hooks (`useState`, `useEffect`) for component state
- No external state library needed for MVP scope
- Lift state to Dashboard component for cross-component coordination

### Enforcement Guidelines

**All AI Agents MUST:**
1. Follow file naming conventions exactly (PascalCase components, lowercase utilities)
2. Use the JSON wrapper format for all `--json` output
3. Include suggestions in all user-facing error messages
4. Co-locate tests with source files
5. Use function components with hooks pattern

**Anti-Patterns to Avoid:**

| Anti-Pattern | Correct Pattern |
|--------------|-----------------|
| `interface IDevPod` | `interface DevPod` |
| `workerList.tsx` | `WorkerList.tsx` |
| `__tests__/discovery.test.ts` | `lib/discovery.test.ts` |
| `Error: something failed` | `✗ context: message\n  Suggestion: ...` |
| Arrow function components | Function declaration components |

## Project Structure & Boundaries

### Complete Project Directory Structure

```
packages/bmad-dashboard/
├── README.md                         # Installation and usage docs
├── package.json                      # npm package configuration
├── tsconfig.json                     # TypeScript configuration
├── .gitignore                        # Git ignore patterns
│
├── src/
│   ├── cli.ts                        # Entry point: Commander setup + TUI/CLI switching
│   │
│   ├── commands/                     # CLI subcommand handlers
│   │   ├── index.ts                  # Command registration
│   │   ├── status.ts                 # `bmad-dashboard status [--json]`
│   │   ├── list.ts                   # `bmad-dashboard list [--json]`
│   │   ├── dispatch.ts               # `bmad-dashboard dispatch <devpod> <story>`
│   │   └── resume.ts                 # `bmad-dashboard resume <devpod>`
│   │
│   ├── components/                   # Ink React components
│   │   ├── Dashboard.tsx             # Main TUI container, state coordination
│   │   ├── WorkerList.tsx            # DevPod status rows
│   │   ├── WorkerDetail.tsx          # Drill-down view for selected DevPod
│   │   ├── StoryStatus.tsx           # Current story info display
│   │   ├── CommandPanel.tsx          # Copy-paste command generation
│   │   ├── Header.tsx                # Dashboard header with refresh indicator
│   │   └── shared/
│   │       ├── StatusBadge.tsx       # Reusable status indicator (✓ ● ○ ✗ ⚠)
│   │       ├── Spinner.tsx           # Loading state indicator
│   │       └── ErrorMessage.tsx      # Styled error with suggestion
│   │
│   ├── lib/                          # Business logic (pure functions)
│   │   ├── discovery.ts              # DevPod CLI integration
│   │   ├── discovery.test.ts         # Co-located tests
│   │   ├── state.ts                  # YAML state reading, aggregation
│   │   ├── state.test.ts             # Co-located tests
│   │   ├── heartbeat.ts              # Stale detection logic
│   │   ├── heartbeat.test.ts         # Co-located tests
│   │   ├── commands.ts               # Command string generation
│   │   ├── commands.test.ts          # Co-located tests
│   │   ├── formatters.ts             # Output formatting (text/JSON)
│   │   └── formatters.test.ts        # Co-located tests
│   │
│   └── types.ts                      # Shared TypeScript interfaces
│
└── bin/
    └── bmad-dashboard                # Executable entry script (shebang)
```

### Architectural Boundaries

**CLI Entry Point Boundary:**
```
cli.ts
├── No subcommand → render(<Dashboard />)  # TUI mode
└── With subcommand → program.parse()       # CLI mode, exit after
```

**Data Flow Boundary:**
```
DevPod CLI (external)
    ↓ subprocess
discovery.ts
    ↓ DevPod[]
state.ts (parallel reads)
    ↓ AggregatedState
components/ (React state)
    ↓ render
Terminal output
```

**Error Isolation Boundary:**
```
Promise.allSettled()
├── Fulfilled → devpods[]
└── Rejected → errors[]
     ↓
Both passed to components (graceful degradation)
```

### Requirements to Structure Mapping

**FR1-4: DevPod Discovery & Status**
- `lib/discovery.ts` - `devpod list --output json` subprocess
- `types.ts` - `DevPod` interface

**FR5-10: Story & Progress Visibility**
- `lib/state.ts` - YAML parsing, story status extraction
- `components/WorkerList.tsx` - Story display per worker
- `components/StoryStatus.tsx` - Detailed story view

**FR11-15: Needs-Input Handling**
- `lib/state.ts` - needs-input detection from YAML
- `components/StatusBadge.tsx` - Visual indicator
- `commands/resume.ts` - Resume command generation

**FR16-18: Stale Detection**
- `lib/heartbeat.ts` - Heartbeat timestamp comparison
- `lib/state.ts` - .worker-state.yaml reading
- `types.ts` - `STALE_THRESHOLD_MS` constant

**FR19-23: Command Generation**
- `lib/commands.ts` - Template-based command generation
- `components/CommandPanel.tsx` - Copy-paste display

**FR24-28: Dashboard Interface**
- `components/Dashboard.tsx` - Main TUI
- `components/WorkerList.tsx` - List view
- `components/WorkerDetail.tsx` - Detail view
- `components/Header.tsx` - Status bar

**FR29-32: CLI Commands**
- `commands/status.ts` - Status dump
- `commands/list.ts` - DevPod listing
- `commands/dispatch.ts` - Dispatch command
- `commands/resume.ts` - Resume command

**FR33-35: Installation**
- `package.json` - npm package with bin entry
- `README.md` - Installation instructions
- `bin/bmad-dashboard` - Executable script

### Integration Points

**External Integrations:**

| Integration | File | Method |
|-------------|------|--------|
| DevPod CLI | `lib/discovery.ts` | `execSync('devpod list --output json')` |
| DevPod Filesystem | `lib/state.ts` | `fs.readFile()` on mounted paths |
| Claude CLI (future) | `commands/dispatch.ts` | Command string generation |

**Internal Communication:**

| From | To | Method |
|------|-----|--------|
| `cli.ts` | `Dashboard` | React render |
| `Dashboard` | `WorkerList` | Props |
| `Dashboard` | `lib/*` | Function calls |
| `lib/discovery` | `lib/state` | DevPod paths |

### File Purpose Summary

| File | LOC Est. | Purpose |
|------|----------|---------|
| `cli.ts` | ~40 | Entry point, mode switching |
| `types.ts` | ~50 | All shared interfaces |
| `lib/discovery.ts` | ~30 | DevPod CLI integration |
| `lib/state.ts` | ~80 | YAML reading, aggregation |
| `lib/heartbeat.ts` | ~30 | Stale detection |
| `lib/commands.ts` | ~40 | Command generation |
| `lib/formatters.ts` | ~40 | Text/JSON output |
| `components/*.tsx` | ~150 | Ink UI components |
| `commands/*.ts` | ~60 | CLI handlers |
| **Total** | **~520** | Within ~500 LOC target |

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**
All technology choices verified compatible:
- Ink 5.x + Commander 12.x + TypeScript 5.x + Node.js 22
- All npm packages, no version conflicts
- ESM module system throughout

**Pattern Consistency:**
All patterns align with technology stack:
- React patterns (function components, hooks) match Ink usage
- File naming patterns match TypeScript/React conventions
- JSON output format supports graceful degradation pattern

**Structure Alignment:**
Project structure supports all architectural decisions:
- Feature-based components map to FR categories
- lib/ separation enables pure function testing
- commands/ structure supports Commander subcommands

### Requirements Coverage Validation ✅

**Functional Requirements Coverage:**
All 35 FRs mapped to specific files:
- FR1-4 (Discovery) → `lib/discovery.ts`
- FR5-10 (Visibility) → `lib/state.ts`, components
- FR11-15 (Needs-Input) → state + StatusBadge
- FR16-18 (Stale) → `lib/heartbeat.ts`
- FR19-23 (Commands) → `lib/commands.ts`
- FR24-28 (Dashboard) → `components/*`
- FR29-32 (CLI) → `commands/*`
- FR33-35 (Install) → package.json, README

**Non-Functional Requirements Coverage:**
All 18 NFRs architecturally supported:
- Performance: Parallel reads, React state management
- Reliability: Error isolation, graceful degradation
- Platform: Pure Node.js, no native dependencies
- Maintainability: ~500 LOC, clear boundaries

### Implementation Readiness Validation ✅

**Decision Completeness:**
- All critical technologies specified with versions
- All patterns documented with examples
- Anti-patterns explicitly listed

**Structure Completeness:**
- 22 source files defined with purposes
- All directories mapped to requirements
- LOC estimates within target

**Pattern Completeness:**
- 6 conflict points addressed
- 5 enforcement guidelines documented
- Examples provided for all major patterns

### Gap Analysis Results

**Critical Gaps:** None - architecture is complete

**Minor Recommendations (Optional, can decide during implementation):**
- YAML parsing library choice (js-yaml recommended)
- Default refresh interval constant (30s per PRD)
- TUI keyboard shortcut mappings

### Architecture Completeness Checklist

**✅ Requirements Analysis**
- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed (~500 LOC)
- [x] Technical constraints identified (5 constraints)
- [x] Cross-cutting concerns mapped (4 concerns)

**✅ Architectural Decisions**
- [x] Critical decisions documented (6 decisions)
- [x] Technology stack fully specified (Ink + Commander)
- [x] Integration patterns defined (DevPod CLI, filesystem)
- [x] Performance considerations addressed (parallel reads)

**✅ Implementation Patterns**
- [x] Naming conventions established (4 categories)
- [x] Structure patterns defined (co-located tests)
- [x] Communication patterns specified (status indicators)
- [x] Process patterns documented (error handling)

**✅ Project Structure**
- [x] Complete directory structure defined (22 files)
- [x] Component boundaries established
- [x] Integration points mapped (3 external, 4 internal)
- [x] Requirements to structure mapping complete (35 FRs)

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION ✅

**Confidence Level:** HIGH

**Key Strengths:**
1. Technology stack proven (Ink used by Claude Code itself)
2. Clear FR → file mapping enables parallel story development
3. ~500 LOC target achievable with defined structure
4. Research-validated decisions (Claude Agent SDK, git-native state)

**Areas for Future Enhancement:**
1. File watching for real-time updates (Phase 2)
2. Retry with backoff (Phase 2)
3. One-click dispatch integration (Phase 2)

### Implementation Handoff

**AI Agent Guidelines:**
1. Follow all architectural decisions exactly as documented
2. Use implementation patterns consistently across all components
3. Respect project structure and boundaries
4. Refer to this document for all architectural questions
5. When in doubt, check the Anti-Patterns table

**First Implementation Priority:**
```bash
mkdir -p packages/bmad-dashboard/src
cd packages/bmad-dashboard
pnpm init
pnpm add ink ink-spinner react commander
pnpm add -D typescript @types/react tsx
```

## Architecture Completion Summary

### Workflow Completion

**Architecture Decision Workflow:** COMPLETED ✅
**Total Steps Completed:** 8
**Date Completed:** 2026-01-04
**Document Location:** `_bmad-output/planning-artifacts/architecture.md`

### Final Architecture Deliverables

**Complete Architecture Document**
- All architectural decisions documented with specific versions
- Implementation patterns ensuring AI agent consistency
- Complete project structure with all files and directories
- Requirements to architecture mapping
- Validation confirming coherence and completeness

**Implementation Ready Foundation**
- 12 architectural decisions made
- 6 implementation pattern categories defined
- 22 source files specified
- 35 FRs + 18 NFRs fully supported

**AI Agent Implementation Guide**
- Technology stack with verified versions
- Consistency rules that prevent implementation conflicts
- Project structure with clear boundaries
- Integration patterns and communication standards

### Development Sequence

1. Initialize project using documented starter template
2. Set up development environment per architecture
3. Implement core architectural foundations (discovery, state)
4. Build features following established patterns
5. Maintain consistency with documented rules

### Quality Assurance Checklist

**✅ Architecture Coherence**
- [x] All decisions work together without conflicts
- [x] Technology choices are compatible
- [x] Patterns support the architectural decisions
- [x] Structure aligns with all choices

**✅ Requirements Coverage**
- [x] All functional requirements are supported
- [x] All non-functional requirements are addressed
- [x] Cross-cutting concerns are handled
- [x] Integration points are defined

**✅ Implementation Readiness**
- [x] Decisions are specific and actionable
- [x] Patterns prevent agent conflicts
- [x] Structure is complete and unambiguous
- [x] Examples are provided for clarity

---

**Architecture Status:** READY FOR IMPLEMENTATION ✅

**Next Phase:** Begin implementation using the architectural decisions and patterns documented herein.

**Document Maintenance:** Update this architecture when major technical decisions are made during implementation.

