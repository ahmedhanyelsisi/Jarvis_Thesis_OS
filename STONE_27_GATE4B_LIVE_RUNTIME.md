# Stone 27 Gate 4B — Live Runtime

**Status:** ready for live-runtime approval.
**Boundary:** the HUD consumes the frozen runtime as a presentation client; it
does not add authority, agents, workspace access, or workflow capabilities.

## Live integration

Normal HUD mode now boots the proven frozen Stone 24 composition through
JarvisBootloader, reads its HealthMonitor, and subscribes through its existing
core EventBus. The bridge boots on one worker and delivers state to QML through
Qt signals. The --no-runtime mode retains a safe degraded functional HUD, while
--prototype remains isolated from runtime startup.

The subscribed frozen topics are:

- workflow.started, workflow.paused, workflow.completed, workflow.failed
- agent.started, agent.completed, agent.failed

Workflow topics carry workflow ID and drive only the supported Core/mission
states: executing, waiting, completed, and error.

## Agent, handoff, and parallel truth

The frozen workflow agent topics currently contain task ID only; they do not
include a trustworthy agent identity. The HUD therefore does **not** light a
named stone for those events. The adapter supports a named stone only when an
actual event supplies an explicit supported agent ID. Unknown IDs are not mapped.

No frozen handoff topic or source/destination payload was found, so live energy
handoffs are unavailable. No frozen evidence for concurrent agent activity was
found, so live parallel orchestration is unavailable. Both remain visually
dormant rather than simulated.

## Health and safety

The real composition reports Runtime, EventBus, AgentSandbox, and ResearchLayer
health. Terminal/security presentation events use a preserved drain lane when
the normal bounded queue is full. Foreign-session events, unknown topics,
malformed payloads, and unsupported agent identities cannot mutate HUD state.

The frozen EventBus has no unsubscribe API. On shutdown, the Stone 27 adapter
disables itself; retained frozen callbacks can no longer update the closed HUD.

## Launch and acceptance procedure

From D:\Masters\Jarvis_Thesis_OS\18_JARVIS_HUD:

    D:\Masters\Jarvis_Thesis_OS\.venv\Scripts\python.exe -B -m app.main

Verify Runtime and Event Bus report ONLINE, then send status through the left
local text input. Use --no-runtime to exercise degraded launch and --prototype
to inspect the separate non-production motion demo.

## Files changed

- 18_JARVIS_HUD/bridge/runtime_composition.py
- 18_JARVIS_HUD/bridge/runtime_event_adapter.py
- 18_JARVIS_HUD/bridge/runtime_bridge.py
- 18_JARVIS_HUD/app/main.py
- 18_JARVIS_HUD/tests/test_gate4_bridge.py
- STONE_27_GATE4B_LIVE_RUNTIME.md

## Validation

- Targeted HUD suite: **15 passed**.
- Included successful live boot, EventBus health, adapter validation, explicit
  agent-ID mapping, foreign-session rejection, bounded terminal events, normal
  functional bridge tests, approval, and cancellation.
- One existing Chroma/Python deprecation warning appears during frozen runtime
  startup; it does not block the HUD.

## Model routing

This Gate was completed by the current agent because model-specific delegation
capacity was unavailable. No Sol escalation was required and no Astra was used.
