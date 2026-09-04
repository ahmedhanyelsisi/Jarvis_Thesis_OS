# Stone 6: Memory Evolution Architecture

## Purpose

Stone 6 gives Jarvis durable, local memory across process and session boundaries. It
adds a separate `memory` package and integrates it at the boundary of the Stone 5
workflow. The existing `process_request()`, `process_workflow()`, `AgentManager`,
agent implementations, task planner, and orchestrator interfaces remain compatible.
The subsystem uses only the Python standard library and does not call an external API.

## Architecture

The subsystem has four layers:

- `memory_models.py` defines the five valid memory categories and the immutable
  `MemoryRecord` transfer model.
- `memory_store.py` owns the SQLite connection, schema, transactions, indexes, CRUD,
  and access-statistic updates.
- `memory_retriever.py` performs deterministic local relevance scoring and combines
  it with importance, recency, and access frequency.
- `memory_manager.py` is the public facade. It validates inputs, applies configured
  defaults, coordinates storage and retrieval, and exposes the required API.

`memory/__init__.py` exports the supported public types. Callers should normally use
`MemoryManager` rather than operate on `MemoryStore` directly.

## Memory categories

| Category | Intended lifetime and use |
| --- | --- |
| `session_memory` | Temporary working context; removed by `clear_session_memory()` |
| `project_memory` | Durable facts and constraints about a project |
| `user_preference_memory` | Explicit user preferences such as format or style |
| `decision_memory` | Decisions and the context needed to apply them later |
| `experience_memory` | Reusable outcomes and lessons from successful workflows |

The category is validated in both Python and the database `CHECK` constraint, so an
unknown category cannot silently enter persistent state.

## Database design

The configured default database is `memory_database.sqlite`. SQLite supplies local,
transactional persistence without a service dependency. The runtime database and its
WAL sidecar files are ignored by Git because they contain machine-specific assistant
state rather than source code.

The `memories` table contains:

| Column | SQLite type | Meaning |
| --- | --- | --- |
| `memory_id` | `TEXT PRIMARY KEY` | UUID assigned when the memory is created |
| `memory_type` | `TEXT` | One of the five validated categories |
| `content` | `TEXT` | Searchable memory text |
| `metadata` | `TEXT` | JSON-encoded structured metadata inside SQLite |
| `importance_score` | `REAL` | Caller-assigned value in the inclusive range 0–1 |
| `created_at` | `TEXT` | ISO 8601 UTC creation time |
| `updated_at` | `TEXT` | ISO 8601 UTC last content/metadata update time |
| `last_accessed` | `TEXT` | ISO 8601 UTC last retrieval time |
| `access_count` | `INTEGER` | Number of direct or search-result retrievals |

Indexes support category filtering, importance filtering, and recency ordering.
Writes use explicit transactions guarded by a process-local reentrant lock, and the
connection uses WAL mode plus a busy timeout. JSON is used only as an encoding for the
`metadata` column; no JSON file is used by the Stone 6 persistent memory store.

## Public API

`MemoryManager` provides:

- `store_memory()` to validate and create a memory;
- `retrieve_memory()` to fetch one ID and update its access statistics;
- `update_memory()` to change selected fields without changing identity or creation
  time;
- `delete_memory()` to remove one memory;
- `search_memory()` to filter and rank memories;
- `clear_session_memory()` to delete only `session_memory` records; and
- `close()` plus context-manager support for deterministic resource cleanup.

The manager accepts either the database path plus keyword options or the complete
`memory` configuration mapping, which keeps standalone and Jarvis construction simple.

All returned records have attributes and `to_dict()` output. Disabled managers avoid
creating a database and return neutral values (`None`, `False`, `[]`, or `0`).

## Retrieval ranking

Search is deterministic and local. Query tokens are compared with memory content and
metadata values. Each candidate receives a normalized score:

```text
ranking = 0.50 × relevance
        + 0.25 × importance
        + 0.15 × recency
        + 0.10 × access frequency
```

Relevance uses token overlap with an exact-phrase bonus. Recency applies exponential
decay with a 30-day half-life. Access frequency is log-normalized against the most
frequently accessed candidate, preventing a large historical count from dominating
all other signals. Results are filtered by category and importance threshold before
ranking, limited by `max_results`, then marked as accessed.

## Workflow and reasoning data flow

```text
request
  -> search_memory(request)
  -> ReasoningEngine.analyze(request)
  -> TaskPlanner.create_plan(strategy)
  -> attach ranked memory context to first task
  -> WorkflowOrchestrator.execute(tasks)
  -> optional Stone 5 evaluation/improvement
  -> if every task succeeded: store experience_memory
  -> response (including memory_context for inspection)
```

Retrieval occurs before `ReasoningEngine.analyze()`, satisfying the pre-reasoning
boundary while leaving request classification deterministic. The retrieved records
are added to the first planned task, so agents can act on prior project facts,
preferences, decisions, and experience without changing any agent API.

An experience is stored only when every planned task completed and none failed or was
skipped. It contains a compact final-output summary and metadata with workflow ID,
task type, and completed task IDs. A failed workflow does not become positive
experience. Stone 5's existing `ReasoningMemory` remains available for its original
workflow-history API; Stone 6 owns the categorized cross-session memory contract.

`process_request()` remains the unchanged single-agent compatibility path. Memory is
integrated into `process_workflow()`, where the Stone 5 reasoning lifecycle exists.

## Configuration

```yaml
memory:
  enabled: true
  database_path: "memory_database.sqlite"
  max_results: 10
  importance_threshold: 0.2
```

- `enabled` switches Stone 6 integration on or off.
- `database_path` may be absolute or relative to the project root when Jarvis loads it.
- `max_results` limits context size and must be at least one.
- `importance_threshold` filters candidates before ranking and must be between 0 and 1.

When a caller supplies a custom configuration mapping with no `memory` section,
memory integration stays disabled. This preserves the behavior of Stone 5 callers
that predate the new configuration. The repository configuration enables it.

## Operational considerations

- Call `Jarvis.close()` or `MemoryManager.close()` before moving or backing up a live
  database.
- SQLite is appropriate for local Jarvis processes. Multi-host shared memory would
  require a later storage adapter and coordination design.
- Ranking is lexical and intentionally has no embedding or OpenAI dependency. Semantic
  retrieval can be added later behind `MemoryRetriever` without changing the manager
  API.
- Memory retention beyond explicit deletion and session clearing is not automated in
  Stone 6. Long-running installations should define archival and privacy policies in
  a later stone.
