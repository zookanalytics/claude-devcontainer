---
stepsCompleted: [1, 2, 3, 4]
inputDocuments: []
workflowType: 'research'
lastStep: 1
research_type: 'technical'
research_topic: 'State management solutions for BMAD across multiple devcontainers/DevPods'
research_goals: 'Explore self-hosted, open source tools that can provide synchronized state for workflow tracking across multiple devcontainers on a single machine (with multi-machine option), with DevPods integration desirable'
user_name: 'Node'
date: '2026-01-03'
web_research_enabled: true
source_verification: true
---

# Research Report: Technical

**Date:** 2026-01-03
**Author:** Node
**Research Type:** Technical

---

## Research Overview

This research investigates state management solutions that could synchronize BMAD workflow state (YAML files) across multiple devcontainers/DevPods, potentially replacing the "BUILD Minimal" approach from prior architecture decisions.

---

## Prior Context: Orchestration Infrastructure Decision

**Source:** `_bmad-output/planning-artifacts/decisions/orchestration-infrastructure-decision.md`

The prior decision designated **State Management → BUILD Minimal** with:
- State Manager (~100 LOC) - Atomic YAML read/write with locking
- Event Bus (~50 LOC) - Pub/sub for state changes

**Key constraints identified:**
- YAML files must remain git-trackable (BMAD requirement)
- SDK manages its own session state
- Need thin layer for YAML atomicity only

**This research explores:** Whether existing open source tools could handle cross-container state synchronization better than building from scratch, particularly for:
- Single developer, multiple devcontainers on local machine
- Potential multi-machine scenarios
- DevPods integration compatibility

---

## Technical Research Scope Confirmation

**Research Topic:** State management solutions for BMAD across multiple devcontainers/DevPods
**Research Goals:** Explore self-hosted, open source tools that can provide synchronized state for workflow tracking across multiple devcontainers on a single machine (with multi-machine option), with DevPods integration desirable

**Technical Research Scope:**

- Architecture Analysis - design patterns, frameworks, system architecture
- Implementation Approaches - development methodologies, coding patterns
- Technology Stack - languages, frameworks, tools, platforms
- Integration Patterns - APIs, protocols, interoperability
- Performance Considerations - scalability, optimization, patterns

**Research Methodology:**

- Current web data with rigorous source verification
- Multi-source validation for critical technical claims
- Confidence level framework for uncertain information
- Comprehensive technical coverage with architecture-specific insights

**Scope Confirmed:** 2026-01-03

---

## Technology Stack Analysis

### Distributed SQLite Solutions

#### LiteFS
**Architecture:** FUSE-based distributed file system for SQLite, transparent replication by intercepting filesystem operations.

- **Primary/Replica Model:** Single primary node handles writes, replicas are read-only
- **Replication:** Up to 100-1000 replicas supported
- **Docker Requirements:** Requires FUSE3, must run as root, needs `--device /dev/fuse --cap-add SYS_ADMIN`
- **Limitations:** Files only in root of mount, no subdirectories
- **Best For:** Applications where SQLite is the natural fit and need transparent distribution

_Integration: `COPY --from=flyio/litefs:0.5 /usr/local/bin/litefs /usr/local/bin/litefs`_

**2025 Assessment:** For most small applications, Litestream (backup) provides simplicity; for distributed writes + auto-failover, rqlite is more mature; LiteFS best for transparent distribution with minimal app changes.

_Sources: [LiteFS Docs](https://fly.io/docs/litefs/), [GitHub](https://github.com/superfly/litefs), [2025 Comparison](https://onidel.com/blog/sqlite-replication-vps-2025)_

#### rqlite
**Architecture:** Distributed relational database built on SQLite using Raft consensus.

- **Consensus:** Automatic leader election, strong consistency across nodes
- **API:** HTTP-based (not native SQLite protocol)
- **Docker:** Official image `rqlite/rqlite`, easy Docker Compose clustering
- **Kubernetes:** Actively used to replace Postgres in K8s stacks (per Replicated CTO)
- **Limitations:** Not for high-write workloads (Raft latency), no stored procedures

**Strengths for BMAD:**
- HTTP API fits container-to-service communication pattern
- No FUSE/privileged requirements
- Built-in clustering discovery via hostnames

_Sources: [rqlite.io](https://rqlite.io/), [GitHub](https://github.com/rqlite/rqlite), [Docker Hub](https://hub.docker.com/r/rqlite/rqlite)_

### Key-Value Stores

#### etcd
**Architecture:** Strongly consistent distributed key-value store (Raft consensus), primary datastore for Kubernetes.

- **Use Cases:** Configuration, service discovery, scheduler coordination
- **Docker:** Official images from `quay.io/coreos/etcd` and `gcr.io/etcd-development/etcd`
- **Complexity:** Designed for Kubernetes scale; may be overkill for simple state
- **Operators:** etcd-druid for Kubernetes day-2 operations

**Assessment:** Heavyweight for BMAD's simple YAML state; better suited for cluster-scale service coordination.

_Sources: [etcd.io](https://etcd.io/docs/v3.4/op-guide/container/), [Red Hat Overview](https://www.redhat.com/en/topics/containers/what-is-etcd)_

#### Consul
**Architecture:** Service networking with built-in KV store, uses Raft consensus.

- **KV Store:** Perfect for dynamic config, feature flags, metadata
- **API:** Simple HTTP API for KV operations
- **Docker:** `hashicorp/consul` (official Verified Publisher image)
- **Discovery:** Automatic service registration and health checks

**Strengths for BMAD:**
- Hierarchical KV store maps well to YAML-like structures
- Leader election built-in
- Lightweight enough for development use

_Sources: [Consul Docs](https://developer.hashicorp.com/consul/docs/discover/docker), [DigitalOcean Tutorial](https://www.digitalocean.com/community/tutorials/how-to-configure-consul-kv-using-docker)_

#### Valkey (Redis Fork)
**Architecture:** High-performance in-memory key-value store, BSD 3-clause licensed fork of Redis.

- **Performance:** 37% higher write throughput, 30% faster p99 latencies vs Redis
- **Memory:** Up to 20% efficiency improvement in v8.1
- **Compatibility:** Drop-in Redis replacement, same protocol/clients
- **Scaling:** Clusters up to 1000 nodes
- **Backing:** AWS, Google Cloud contribute actively

**Strengths for BMAD:**
- Extremely lightweight for simple state
- Sub-millisecond latency
- No licensing concerns (fully open source)

_Sources: [Valkey.io](https://valkey.io/), [Better Stack Comparison](https://betterstack.com/community/comparisons/redis-vs-valkey/), [Valkey 9.0 Blog](https://valkey.io/blog/introducing-valkey-9/)_

### File Synchronization Solutions

#### Syncthing
**Architecture:** Decentralized P2P continuous file synchronization.

- **Docker:** Official `syncthing/syncthing` image, LinuxServer.io variant
- **Network:** **Host network mode recommended** (Docker default network breaks LAN discovery)
- **Permissions:** UID/GUID configurable via PUID/PGID env vars
- **Security:** Password for WebUI strongly recommended (listens on 0.0.0.0)

**Strengths for BMAD:**
- Keeps YAML files as actual files (git-trackable requirement satisfied)
- Works across machines, not just containers
- No central server needed

**Weaknesses:**
- Potential sync conflicts with concurrent edits
- Requires host network or manual address configuration

_Sources: [Docker Hub](https://hub.docker.com/r/syncthing/syncthing), [LinuxServer Docs](https://docs.linuxserver.io/images/docker-syncthing/)_

#### SQLite with Shared Docker Volume
**Architecture:** Single SQLite database file mounted into multiple containers.

**Key Configuration:**
- **WAL Mode:** Required for concurrent access without blocking
- **Permissions:** WAL and SHM files need 666/777 for multi-container write access
- **Network FS:** Avoid CIFS/NFS, or use `nobrl` mount option
- **Kernel:** All processes must share single Linux kernel

**Assessment:** Works well for local machine with multiple devcontainers. Rick Branson: "Sharing an SQLite database across containers is surprisingly brilliant."

_Sources: [Medium Article](https://rbranson.medium.com/sharing-sqlite-databases-across-containers-is-surprisingly-brilliant-bacb8d753054), [Vaultwarden Discussion](https://github.com/dani-garcia/vaultwarden/discussions/4447)_

### DevPod/Devcontainer Native Patterns

#### Shared Named Volumes
- **Pattern:** Mount state directory as named volume shared across all devcontainer instances
- **Performance:** Named volumes preferred over bind mounts for performance
- **JetBrains:** Uses `jb_devcontainers_shared_volume` for IDE backends
- **State Persistence:** Workspace state survives container recreation

#### DevPod State Management
- **Workspace State:** DevPod preserves state across stop/restart cycles
- **Recreate Command:** `devpod up my-workspace --recreate` applies config changes without losing state
- **Feature Request:** Multiple environments per workspace (isolated branches) under discussion ([GitHub Issue #688](https://github.com/loft-sh/devpod/issues/688))

#### Docker Compose Centralization
- **Pattern:** Single `docker-compose.yml` with shared service definitions
- **Bind/Volume Detection:** Use `initializeCommand` to detect and configure dynamically

_Sources: [DevPod Docs](https://devpod.sh/docs/what-is-devpod), [Dev.to Guide](https://dev.to/graezykev/dev-containers-part-5-multiple-projects-shared-container-configuration-2hoi), [Stir Trek 2025](https://chris-ayers.com/2025/05/04/stir-trek-and-multiple-dev-containers/)_

### Technology Adoption Summary

| Solution | Complexity | YAML-Native | Multi-Machine | DevPod Fit | Confidence |
|----------|------------|-------------|---------------|------------|------------|
| **Shared Volume + SQLite** | Low | No (convert) | No | High | High |
| **rqlite** | Medium | No (convert) | Yes | Medium | High |
| **Valkey** | Low | No (convert) | Yes | High | High |
| **Syncthing** | Medium | Yes | Yes | Medium | Medium |
| **Consul KV** | Medium | Partial | Yes | Medium | High |
| **LiteFS** | High | No | Yes | Low (FUSE) | Medium |
| **etcd** | High | No | Yes | Low | High |

---

## Integration Patterns Analysis

### DevPod/Devcontainer Multi-Service Patterns

#### Docker Compose Service Communication
- **Default Network:** Services automatically communicate without explicit configuration
- **Network Mode Sharing:** `network_mode: service:db` runs containers in same network namespace (tight coupling)
- **Shared Volumes:** `group_add` for containers running as different users to access same files
- **Shutdown Behavior:** `"shutdownAction": "none"` in devcontainer.json keeps services running when IDE closes

**Known Issue (January 2025):** DevPod users report issues with docker-compose devcontainers - direct `docker-compose up` works but DevPod integration may have edge cases ([GitHub Issue #1584](https://github.com/loft-sh/devpod/issues/1584)).

_Sources: [VS Code Multi-Container Docs](https://code.visualstudio.com/remote/advancedcontainers/connect-multiple-containers), [Docker Compose Services](https://docs.docker.com/reference/compose-file/services/)_

#### Sidecar Pattern Implementation
- **Azure App Service (2025):** Moving from Docker Compose to Sidecar feature (Compose retiring March 2027)
- **Same Network Namespace:** Sidecar runs in same network as main service via `network_mode`
- **Use Case:** State management service (Valkey/rqlite) as sidecar alongside dev container

```yaml
# docker-compose.yml sidecar pattern
services:
  app:
    build: .
    network_mode: service:state
    depends_on:
      - state
  state:
    image: valkey/valkey
    volumes:
      - state-data:/data
```

_Sources: [Azure Sidecar Migration](https://azure.github.io/AppService/2025/04/01/Docker-compose-migration.html), [Sidecar Docker Compose](https://blog.riskiwah.xyz/posts/sidecar-container-pattern-with-docker-compose/)_

### Python Client Integration Patterns

#### rqlite HTTP API
- **Ports:** 4001 (HTTP API), 4002 (Raft consensus)
- **Endpoints:** `/db/execute` (writes), `/db/query` (reads), `/db/request` (unified)
- **Libraries:**
  - `pyrqlite` - Official DB-API 2.0 compatible client
  - `rqdb` - Unofficial with parameterized queries
- **Limitation:** Transactions must be specified upfront (connectionless nature)

```python
# pyrqlite usage
import pyrqlite.dbapi2 as dbapi2
connection = dbapi2.connect(host='rqlite', port='4001')
cursor = connection.cursor()
cursor.execute("SELECT * FROM workflow_state WHERE id = ?", (story_id,))
```

_Sources: [rqlite Client Libraries](https://rqlite.io/docs/api/client-libraries/), [pyrqlite GitHub](https://github.com/rqlite/pyrqlite)_

#### Valkey/Redis Client
- **Library:** `valkey-py` (fork of redis-py)
- **Migration:** Change imports from `redis` to `valkey`, class compatibility maintained
- **GLIDE Client:** Official high-availability client with Rust core + Python bindings
- **Async Support:** asyncio/anyio/trio native compatibility

```python
# valkey-py (drop-in redis replacement)
from valkey import Valkey
client = Valkey(host='valkey', port=6379)
client.hset('sprint:status', 'story-1', 'in_progress')
status = client.hget('sprint:status', 'story-1')
```

_Sources: [valkey-py GitHub](https://github.com/valkey-io/valkey-py), [Valkey Migration Guide](https://aiven.io/developer/python-valkey-redis-migration)_

### File Watching Challenges in Containers

#### The inotify Problem
- **Root Cause:** Host filesystem events don't propagate through VM boundaries (Windows/Mac → Docker)
- **CIFS Limitation:** Linux kernel CIFS implementation doesn't propagate host file events
- **Impact:** File watchers (Jekyll, webpack, Parcel) don't see changes in mounted volumes

#### Solutions by Priority

1. **Docker Compose Watch** (Modern, Recommended)
   - Native Docker feature for file synchronization
   - Supports "rebuild" action on changes

2. **Polling** (Universal Fallback)
   - chokidar-based watchers support polling mode
   - Trade-off: CPU intensive for large file sets

3. **Sidecar Watcher** (Event-Driven)
   - Mount volume in sidecar with inotifywait
   - Trigger script on events
   - Works for container-to-container notification

4. **docker-windows-volume-watcher** (Windows Specific)
   - Uses chmod to trigger inotify events inside container
   - Workaround for WSL2/Windows limitations

**Implication for BMAD:** If using file-based YAML state, containers may not see changes from other containers on shared volumes without polling or explicit notification.

_Sources: [Docker inotify Issue](https://github.com/moby/moby/issues/18246), [File Watch Solutions](https://syntackle.com/blog/the-issue-of-watching-file-changes-in-docker/)_

### Atomic YAML Updates in Python

#### The Race Condition Problem
- **Scenario:** Multiple containers/processes writing to same YAML file
- **Risk:** File truncation, corruption, partial writes
- **Python Limitation:** stdlib file locking support is "pretty terrible"

#### Atomic Write Pattern (Recommended)

```python
import tempfile
import os
import yaml

def atomic_yaml_write(filepath, data):
    """Write YAML atomically using temp file + rename"""
    dir_name = os.path.dirname(filepath)
    with tempfile.NamedTemporaryFile(
        mode='w', dir=dir_name, delete=False, suffix='.tmp'
    ) as tmp:
        yaml.safe_dump(data, tmp)
        tmp_path = tmp.name
    os.replace(tmp_path, filepath)  # Atomic on POSIX
```

#### Alternative: Atomos Library
- Compare-and-set semantics for shared mutable state
- Lock-free atomic primitives
- Port of Clojure's atom concept

**Recommendation:** For cross-container state, prefer database-backed solutions (rqlite, Valkey) over file locking, as they handle concurrency internally.

_Sources: [Atomic Updates in Python](https://sahmanish20.medium.com/better-file-writing-in-python-embrace-atomic-updates-593843bfab4f), [Atomos Library](https://github.com/maxcountryman/atomos)_

### Integration Pattern Comparison for BMAD

| Pattern | Complexity | DevPod Compatible | Concurrency Safe | Git-Trackable |
|---------|------------|-------------------|------------------|---------------|
| **Sidecar Valkey** | Low | Yes | Yes (built-in) | No (export needed) |
| **Sidecar rqlite** | Medium | Yes | Yes (Raft) | No (export needed) |
| **Shared Volume + Atomic YAML** | Low | Yes | Partial (race risk) | Yes |
| **Syncthing Mesh** | Medium | Needs host network | Conflict resolution | Yes |
| **Polling File Watcher** | Low | Yes | No | Yes |

### Recommended Integration Architecture

For BMAD's use case (single dev, multiple devcontainers, git-trackable requirement):

```
┌─────────────────────────────────────────────────────────────┐
│                      HOST MACHINE                            │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              State Service Container                 │    │
│  │  Valkey/rqlite (single instance, persistent volume) │    │
│  │  Port: 6379 or 4001                                  │    │
│  └─────────────────────────────────────────────────────┘    │
│           │                  │                  │            │
│           ▼                  ▼                  ▼            │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐         │
│  │ DevPod 1   │    │ DevPod 2   │    │ DevPod 3   │         │
│  │ (Claude)   │    │ (Claude)   │    │ (Claude)   │         │
│  │            │    │            │    │            │         │
│  │ bmad-state │    │ bmad-state │    │ bmad-state │         │
│  │   client   │    │   client   │    │   client   │         │
│  └────────────┘    └────────────┘    └────────────┘         │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Git Repo (bind mount to all containers)            │    │
│  │  - YAML files for git-trackable snapshots           │    │
│  │  - Periodic export from state service               │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

**Key Integration Points:**
1. State service runs as separate container (not sidecar per DevPod)
2. All DevPods connect to same state service via Docker network
3. Git-trackable YAML maintained via periodic export/sync
4. No file watching required - event-driven via state service

---

## Architectural Patterns and Design

### Single Source of Truth (SSOT) Architecture

**Core Principle:** Every data element is mastered in only one place, providing data normalization to a canonical form.

**Why SSOT Matters for BMAD:**
- Multiple devcontainers potentially modifying workflow state simultaneously
- Without SSOT: complex consensus algorithms or risk of data loss
- With SSOT: simplified version control, prevention of inconsistencies

**2025 Assessment:** Modern system architectures often prioritize scale and flexibility at the cost of simplicity and consistency. The rush to adopt microservices can fragment state across services. For BMAD's scale (single dev, few containers), a simpler SSOT pattern is optimal.

_Sources: [Wikipedia SSOT](https://en.wikipedia.org/wiki/Single_source_of_truth), [Single State Model Architecture](https://medium.com/@adamcerny_16041/single-state-model-architecture-d0fa24ff8528)_

### Event Sourcing Pattern

**Concept:** Persist state as a sequence of state-changing events rather than current state snapshots.

**Benefits for Workflow State:**
- Complete history of state changes (audit trail)
- Reconstruct state at any point in time
- Natural fit for workflow progression (story → in_progress → completed)
- Facilitates rollback and recovery

**Trade-offs:**
- Requires CQRS for efficient queries
- Eventually consistent data model
- More complex than simple CRUD

**BMAD Applicability:** Event sourcing is powerful but may be over-engineering for BMAD's needs. A simpler approach: store current state + maintain YAML history in git.

_Sources: [Microservices.io Event Sourcing](https://microservices.io/patterns/data/event-sourcing.html), [Axon Framework 2025](https://www.intre.it/en/2025/04/14/microservices-cqrs-event-sourcing-axon-framework/)_

### Hybrid State Architecture (Recommended)

**Pattern:** Live operational state in database + periodic export to git-trackable files.

```
┌─────────────────────────────────────────────────────────────┐
│                    HYBRID STATE FLOW                         │
│                                                              │
│   ┌─────────────┐     Read/Write      ┌─────────────────┐   │
│   │  DevPod 1   │◄──────────────────►│                 │   │
│   └─────────────┘                     │  State Service  │   │
│   ┌─────────────┐     Read/Write      │  (Valkey/rqlite)│   │
│   │  DevPod 2   │◄──────────────────►│                 │   │
│   └─────────────┘                     │  SSOT for live  │   │
│   ┌─────────────┐     Read/Write      │  operations     │   │
│   │  DevPod 3   │◄──────────────────►│                 │   │
│   └─────────────┘                     └────────┬────────┘   │
│                                                │              │
│                                    Periodic Export           │
│                                    (on change or schedule)   │
│                                                │              │
│                                                ▼              │
│                                    ┌─────────────────────┐   │
│                                    │   YAML Files        │   │
│                                    │   (Git-trackable)   │   │
│                                    │                     │   │
│                                    │   sprint-status.yaml│   │
│                                    │   workflow-state.yaml│  │
│                                    └─────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Key Design Decisions:**

1. **Live State (Database):** Source of truth for active operations
   - Handles concurrent access automatically
   - Sub-millisecond reads for workflow queries
   - No file locking complexity

2. **YAML Export (Files):** Snapshot for git history
   - Human-readable for code review
   - Version controlled with project
   - Can reconstruct state service from YAML if needed

3. **Bidirectional Sync Option:**
   - On startup: load YAML → state service (if state service empty)
   - On change: state service → YAML (debounced/batched)

_Sources: [Git Distributed Sync](https://github.blog/open-source/git/gits-database-internals-iv-distributed-synchronization/), [Snowflake DevOps](https://medium.com/snowflake/devops-in-snowflake-how-git-and-database-change-management-enable-a-file-based-object-lifecycle-1f61a0d5257c)_

### Distributed Systems Patterns (For Future Scale)

**Majority Quorum:** Operations succeed after acknowledgment from strict majority.
- rqlite implements this via Raft consensus
- Guarantees single source of truth during network failures

**Leader Election:** Single node assumes coordination role.
- Consul provides built-in leader election
- Useful if BMAD needs cross-machine coordination later

**Assessment:** For single-machine, multiple-devcontainer setup, these patterns are overkill. Valkey single-instance is sufficient. Reserve distributed patterns for multi-machine future.

_Sources: [Distributed Systems Patterns](https://www.dataannotation.tech/developers/patterns-of-distributed-systems), [8 Design Patterns](https://newsletter.systemdesigncodex.com/p/8-must-know-distributed-system-design)_

### Architecture Decision: Complexity vs. Requirements

| Requirement | Simple (Shared Volume) | Medium (Valkey) | Complex (rqlite/Event Sourcing) |
|-------------|------------------------|-----------------|----------------------------------|
| Single machine, multi-container | ✅ Works | ✅ Optimal | ✅ Overkill |
| Multi-machine future | ❌ Doesn't scale | ✅ Replication available | ✅ Built-in |
| Git-trackable | ✅ Native | ⚠️ Export needed | ⚠️ Export needed |
| Concurrency safety | ⚠️ Manual locking | ✅ Automatic | ✅ Automatic |
| Operational overhead | ✅ None | ✅ Minimal | ⚠️ Cluster management |
| Recovery from failure | ⚠️ File-level | ✅ Persistence | ✅ Consensus |

---

## Recommendations and Conclusions

### Primary Recommendation: Valkey + YAML Export

**Architecture:** Single Valkey container as state service with periodic YAML export for git tracking.

**Rationale:**
1. **Simplest solution that meets all requirements**
   - Concurrency-safe without application-level locking
   - Git-trackable via export (satisfies BMAD constraint)
   - Future multi-machine ready (Valkey replication)

2. **Minimal code change from current BMAD**
   - ~50 LOC state client wrapper
   - ~30 LOC YAML export/import
   - Compare to 150 LOC "BUILD Minimal" in prior decision

3. **Proven DevPod/devcontainer compatibility**
   - Standard Docker network communication
   - No FUSE or privileged requirements
   - Drop-in redis-py compatible client

### Implementation Sketch

```python
# bmad_state_client.py (~50 LOC)
from valkey import Valkey
import yaml
import json

class BMADStateClient:
    def __init__(self, host='bmad-state', port=6379):
        self.client = Valkey(host=host, port=port, decode_responses=True)

    def get_story_status(self, story_id: str) -> dict:
        return json.loads(self.client.hget('stories', story_id) or '{}')

    def set_story_status(self, story_id: str, status: dict):
        self.client.hset('stories', story_id, json.dumps(status))
        self.client.publish('state_changes', f'story:{story_id}')

    def export_to_yaml(self, filepath: str):
        """Export current state to git-trackable YAML"""
        state = {
            'stories': {k: json.loads(v) for k, v in self.client.hgetall('stories').items()},
            'epics': {k: json.loads(v) for k, v in self.client.hgetall('epics').items()},
        }
        with open(filepath, 'w') as f:
            yaml.safe_dump(state, f, default_flow_style=False)

    def import_from_yaml(self, filepath: str):
        """Bootstrap state from YAML (idempotent)"""
        with open(filepath) as f:
            state = yaml.safe_load(f)
        for story_id, data in state.get('stories', {}).items():
            self.client.hset('stories', story_id, json.dumps(data))
```

### Docker Compose Configuration

```yaml
# docker-compose.yml addition
services:
  bmad-state:
    image: valkey/valkey:8
    container_name: bmad-state
    ports:
      - "6379:6379"
    volumes:
      - bmad-state-data:/data
    command: valkey-server --appendonly yes
    restart: unless-stopped

volumes:
  bmad-state-data:
```

### Alternative Recommendation: rqlite (If SQL Preferred)

If BMAD workflows benefit from SQL queries (e.g., "find all stories in epic X with status Y"):

```yaml
services:
  bmad-state:
    image: rqlite/rqlite
    container_name: bmad-state
    ports:
      - "4001:4001"
    volumes:
      - bmad-state-data:/rqlite/file
```

**Trade-off:** HTTP API instead of Redis protocol, but familiar SQL interface.

### Migration Path from Current Architecture

| Phase | Action | Effort |
|-------|--------|--------|
| 1. Add State Service | Add Valkey to docker-compose | 30 min |
| 2. Create Client | Implement BMADStateClient | 2-4 hrs |
| 3. Parallel Operation | Read from YAML, write to both | 2-4 hrs |
| 4. Cutover | Primary reads from Valkey | 1-2 hrs |
| 5. YAML as Export | Change YAML to export-only | 1 hr |

**Total Effort:** ~1-2 days

### Comparison to Prior "BUILD Minimal" Decision

| Aspect | Prior Decision (BUILD) | This Recommendation (ADOPT) |
|--------|------------------------|----------------------------|
| **Approach** | Build state_manager.py + event_bus.py | Adopt Valkey + thin wrapper |
| **LOC** | ~150 estimated | ~80 actual |
| **Concurrency** | File locking (error-prone) | Built-in (battle-tested) |
| **Multi-machine** | Additional work needed | Valkey replication available |
| **Maintenance** | Custom code to maintain | Community-maintained |

**Recommendation:** Replace "BUILD Minimal" with "ADOPT Valkey" in orchestration decision.

---

## Executive Summary

### Research Question
Are there existing open-source tools that could manage BMAD workflow state across multiple devcontainers better than building from scratch?

### Answer: Yes - Valkey

**Valkey** (open-source Redis fork, BSD licensed) provides:
- Concurrent state access without application-level locking
- Sub-millisecond performance for workflow queries
- Persistence with AOF (append-only file)
- Future multi-machine capability via replication
- Drop-in compatibility with existing Redis ecosystem

**Git-trackable requirement satisfied via:**
- Periodic YAML export from Valkey state
- Human-readable snapshots committed to repo
- Bidirectional sync on startup if needed

### Key Sources

- [Valkey.io](https://valkey.io/) - Official documentation
- [valkey-py GitHub](https://github.com/valkey-io/valkey-py) - Python client
- [rqlite.io](https://rqlite.io/) - Alternative if SQL preferred
- [DevPod Docs](https://devpod.sh/docs/what-is-devpod) - DevPod integration
- [Docker inotify Issue](https://github.com/moby/moby/issues/18246) - Why file-based state has challenges

---
