# Stone 12 — Academic Workflow Orchestration Layer

**Status:** COMPLETE  
**Package:** `academic_workflow/`  
**Classification:** Pure orchestration layer

---

## 1. Purpose

Stone 12 is a **stateless orchestration layer** that converts outputs from
Stones 9–11 into controlled workflow states. It produces deterministic
action queues and structured reports.

**Stone 12 owns workflow state representation only.**  
**The Kernel owns all execution decisions.**

## 2. Boundaries

### Allowed
- Python standard library only
- `hashlib` for deterministic action IDs
- `threading.RLock` for lifecycle thread safety
- `uuid` for pipeline/report identifiers
- Read-only consumption of Stone 9, 10, 11 public APIs

### Forbidden
- No LLM or AI model calls
- No agent creation or management
- No memory implementation (no SQLite, no persistence)
- No network access (no socket, requests, urllib, httpx)
- No subprocess execution
- No filesystem ownership (no file I/O)
- No UI or voice dependencies
- No reasoning engine duplication

## 3. Modules

| Module | Responsibility |
|--------|---------------|
| `models.py` | Frozen dataclass models and enums |
| `lifecycle.py` | Per-chapter lifecycle state machine |
| `action_queue.py` | Deterministic finding-to-action conversion |
| `workflow.py` | Workflow step collection and state representation |
| `milestone_tracker.py` | Milestone snapshot computation (no persistence) |
| `report_builder.py` | Report assembly from components |
| `__init__.py` | `AcademicWorkflow` facade — sole Kernel integration point |

## 4. Lifecycle State Machine

```
PLANNING → DRAFTING → ANALYSIS → REVISION ↔ ANALYSIS
                         ↓
                       REVIEW → REVISION (regression)
                         ↓
                    FINALIZATION → COMPLETE
```

### Valid Transitions

| From | Allowed Targets |
|------|----------------|
| PLANNING | DRAFTING |
| DRAFTING | ANALYSIS |
| ANALYSIS | REVISION, REVIEW |
| REVISION | ANALYSIS |
| REVIEW | FINALIZATION, REVISION |
| FINALIZATION | COMPLETE |
| COMPLETE | (none — terminal) |

Invalid transitions raise `InvalidTransitionError`.

## 5. Action Priority Rules

All priorities are fixed mappings from finding type to severity level.
No AI scoring. No heuristics.

| Finding Type | Priority | Source |
|-------------|----------|--------|
| Missing `.bib` files | CRITICAL | Stone 10 |
| Duplicate labels | CRITICAL | Stone 10 |
| Missing bibliography entries | HIGH | Stone 10 |
| Duplicate citation keys | HIGH | Stone 10 |
| Unresolved references | HIGH | Stone 10 |
| Terminology inconsistencies | HIGH | Stone 11 |
| Citation reference issues | HIGH | Stone 11 |
| Missing evidence | HIGH | Stone 11 |
| Malformed bibliography | MEDIUM | Stone 10 |
| Chapter alignment issues | MEDIUM | Stone 11 |
| Research question misalignment | MEDIUM | Stone 11 |
| Underrepresented research areas | MEDIUM | Stone 11 |
| Missing connections | MEDIUM | Stone 11 |
| Reviewer weaknesses | MEDIUM | Stone 11 |
| Unused bibliography entries | LOW | Stone 10 |
| Possible contribution areas | LOW | Stone 11 |
| Improvement suggestions | LOW | Stone 11 |

## 6. Kernel Integration

Only `01_CORE_KERNEL/jarvis.py` imports `AcademicWorkflow`:

```python
from academic_workflow import AcademicWorkflow

self.academic_workflow = AcademicWorkflow(
    copilot=self.academic_copilot,
    workspace=self.thesis_workspace,
    router=self.academic_router,
)
```

## 7. Public API

```python
class AcademicWorkflow:
    run_workflow(*, chapter, chapter_texts, ...) -> WorkflowReport
    get_lifecycle(chapter) -> ChapterLifecycle
    advance_stage(chapter, target_stage, reason) -> ChapterLifecycle
    list_lifecycles() -> tuple[ChapterLifecycle, ...]
    get_milestones() -> MilestoneSnapshot
    get_actions(report=None) -> ActionQueue
```

## 8. Security

Enforced by AST scanning in `test_academic_workflow.py`:
- Zero imports of `socket`, `requests`, `urllib`, `httpx`, `subprocess`, `sqlite3`
- Zero imports from `memory`, `reasoning`, `voice`, `cognitive_ui`, `knowledge_system`
- Zero usage of `exec`, `eval`, `open`
