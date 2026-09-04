# Stone 8: Cognitive Command Center Architecture

## Purpose

Stone 8 adds a lightweight, transport-neutral control layer above Jarvis. It gives
text clients and future visual interfaces one entry point for commands, structured
responses, session state, workflow visibility, agent activity, and internal events.
It contains no reasoning or agent-selection logic and does not replace any API from
Stones 4 through 7.

## Architecture

```text
User / future GUI / future avatar
              |
              v
+---------------------- cognitive_ui ----------------------+
| UIManager                                               |
|   |                                                     |
|   +--> CommandCenter --> SessionState                    |
|            |                |                            |
|            +------------> EventBus --> UI subscribers    |
|            |                                             |
+------------|---------------------------------------------+
             v
       Jarvis Kernel public API
       |-- process_request()
       |-- process_workflow()
       `-- get_system_status()
             |
             +--> existing AgentManager / agents
             +--> existing MemoryManager
             +--> existing KnowledgeManager
             +--> existing reasoning orchestration
             `--> existing VoiceManager
```

The dependency direction is always `Cognitive UI -> Jarvis Kernel`. The cognitive
UI does not import, route to, or execute specialist agents directly.

## Components

| Component | Responsibility |
| --- | --- |
| `ui_manager.py` | Top-level UI controller and dashboard snapshot facade |
| `command_center.py` | Validates commands, calls the public kernel, and returns structured responses |
| `session_state.py` | Tracks the active session, current task, workflow, last response, and observed agents |
| `dashboard_models.py` | Typed `UIEvent`, `AgentStatus`, `WorkflowStatus`, and `SystemStatus` models |
| `event_bus.py` | Synchronous, in-process publish/subscribe communication with retained event history |

## Data flow

1. A caller passes a command such as `Jarvis write my thesis introduction` to
   `UIManager.handle_command()` or `CommandCenter.send_command()`.
2. The command center validates the text, begins the session task, and emits
   `command_received`. Workflow calls also emit `workflow_started`.
3. The command is sent only to `Jarvis.process_request()` or
   `Jarvis.process_workflow()`. Existing kernel routing, reasoning, knowledge,
   memory, and agents perform the work unchanged.
4. The command center projects the returned kernel metadata into typed workflow and
   agent statuses. It emits `agent_started`, `agent_completed`, and, after a
   successful persistent workflow, `memory_updated`.
5. Session state stores the raw kernel response, the active task is cleared, and
   `response_ready` is emitted.
6. The caller receives a structured envelope containing `status`, `command`,
   `mode`, the unmodified kernel `response`, a serialized `session`, and
   `system_status`.

The initial kernel is synchronous. Consequently, agent events are an observational
projection of metadata in the completed kernel response. The event and model
boundaries allow a future streaming kernel to publish live transitions without
changing interface clients.

## Events

The internal event bus defines these Stone 8 events:

- `command_received`
- `workflow_started`
- `agent_started`
- `agent_completed`
- `memory_updated`
- `response_ready`

Subscribers can listen to one event type or to `*`. Event history is exposed as an
immutable tuple so a renderer can replay the current session safely.

## Integration points

`Jarvis.get_system_status()` is the only addition to the kernel. It returns:

```python
{
    "kernel": "active",
    "agents": 6,
    "memory": "active",
    "voice": "ready",
    "workflow": "ready",
}
```

The values reflect subsystem availability; live command and workflow execution is
tracked by `SessionState`. Existing `process_request()`, `process_workflow()`, voice,
memory, agent, and knowledge APIs retain their signatures and behavior.

## Future expansion

- **GUI:** bind widgets to `UIManager.get_dashboard()` and EventBus subscriptions.
- **Holographic interface:** transform the same typed snapshots and events into a
  spatial renderer without coupling it to kernel internals.
- **Voice avatar:** combine the existing VoiceManager adapter with command-center
  events for listening, thinking, agent, and response animation states.
- **Visualization layer:** render workflow task graphs, agent timelines, memory
  updates, and routing history from the transport-neutral models.

These additions should remain consumers of the command center and event contracts;
they should not gain direct access to agents or reasoning implementation details.

## Session lifecycle

`SessionState` remains the in-process, thread-safe view used by existing callers.
When durable state is needed, an application injects `SessionStore`, which writes
serialized UI snapshots to its own SQLite database (`ui_sessions`). `save_session`
upserts a snapshot, `load_session` restores a `SessionState`, `update_session` merges
an update, and `clear_session` removes one or all UI sessions. This store is separate
from Stone 6 `MemoryManager` and never changes memory retrieval or retention.

## Event architecture

Each `UIEvent` has a UUID `event_id`, UTC `timestamp`, `source`, `event_type`, legacy
`data`, canonical `payload`, and arbitrary `metadata`. `EventBus.publish`/`emit`
records events in memory, supports typed or wildcard subscribers, and exposes
filtered immutable history through `get_history`. The synchronous implementation is
deliberately dependency-free; a future renderer can replace the transport while
keeping the event model.

## Metrics architecture

`DashboardMetrics` tracks request count, successful and failed workflows, active
agent count, the last execution timestamp, and a running average execution duration.
`CommandCenter` updates metrics at every command boundary and includes a typed
`DashboardMetricsSnapshot` in structured responses and dashboard snapshots. Metrics
are operational UI telemetry only; they do not alter Stone 5 reasoning or Stone 6
memory.

## Command processing flow

Before dispatch, the command center validates text, extracts a deterministic intent,
target, and likely agent, and emits `command_received`. For example, “Jarvis continue
thesis chapter 3” maps to `continue_writing`, `chapter 3`, and `latex_agent`. The
original command is still sent unchanged to the kernel. Workflow calls additionally
emit `workflow_started`, project task metadata into agent events, and finish with
`response_ready`.

## Security model

`security.py` applies local lexical validation before any kernel call. Empty or
malformed commands are rejected; destructive verbs (`delete`, `remove`, `drop`,
`truncate`, and similar shell/system actions) are marked as requiring confirmation.
`CommandCenter.send_command(..., confirmed=False)` returns a blocked structured
response and does not invoke Jarvis for those commands. An application must pass
`confirmed=True` after its own user confirmation. This is a safety gate, not a
permission system or sandbox, and it does not modify the existing kernel APIs.
