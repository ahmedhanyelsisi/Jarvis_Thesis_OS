# Stone 27 Gate 4 — Functional HUD

**Status:** ready for human functional HUD approval.
**Boundary:** Stone 27 is a presentation client. QML submits typed requests to a
Python bridge; the frozen Conversation Engine and Authorization Manager remain
the authority chain.

## Architecture

RuntimeBridge is a Qt-facing view model over the frozen local ChatManager. It
owns a single worker, bounded normalized presentation-event queue, correlated
request handling, and immutable QML-friendly snapshots. QML has no import or
reference to the Conversation Engine, Authorization Manager, filesystem,
kernel, voice worker, or command execution interfaces.

The bridge forwards local text to ChatManager.handle_text. Approval submits only
the currently displayed proposal ID; Python verifies the bridge session before
forwarding the exact local confirmation to the frozen manager. The manager
continues to enforce proposal liveness, one-time use, scope, and authorization
ledger behavior.

## Connected real functions

- Local text conversation through the real Stone 25 ChatManager.
- Read-only status conversation response.
- Real scope-enable proposal presentation, exact-ID local approval, rejection,
  cancellation, and authoritative scoped-autonomy display.
- Correlated, bounded presentation event envelopes with sequence, timestamp,
  session, provenance, correlation ID, and redacted payload.
- Real functional/controlled state and safe error presentation.
- Voice software availability, wake-disabled configuration, and hardware
  qualification status are shown honestly.

## Intentionally unavailable in this local launch

No live Stone 24 kernel composition, thesis root, workflow executor, or agent
event source is configured by this HUD module. The HUD therefore shows
UNCONFIGURED / EVENTS UNAVAILABLE / ROOT NOT CONFIGURED rather than fabricating
runtime, agent, workflow, thesis, or handoff activity. Agent stones remain
dormant without real events.

VS Code, workspace indexing, new Git integration, and new LaTeX controls remain
Stone 28 responsibility. Microphone qualification and wake enablement remain
deferred.

## Launch and use

From D:\Masters\Jarvis_Thesis_OS\18_JARVIS_HUD:

    D:\Masters\Jarvis_Thesis_OS\.venv\Scripts\python.exe -B -m app.main

Enter status or Jarvis, show system status in the left input and select
**SEND LOCAL REQUEST**. The actual reply is shown in the conversation/history
area. A request for enable autonomous mode creates a real session-bound
proposal; its real ID, scope, operation, and target appear in the approval
panel. Approve only with **APPROVE REAL REQUEST**, or use **CANCEL REAL
REQUEST**.

The Gate 3 choreography controls are excluded from the functional HUD. To view
them separately:

    D:\Masters\Jarvis_Thesis_OS\.venv\Scripts\python.exe -B -m app.main --prototype

## Files changed

- 18_JARVIS_HUD/bridge/runtime_bridge.py
- 18_JARVIS_HUD/bridge/__init__.py
- 18_JARVIS_HUD/app/main.py
- 18_JARVIS_HUD/qml/Main.qml
- 18_JARVIS_HUD/tests/test_gate4_bridge.py
- 18_JARVIS_HUD/tests/test_gate2_shell.py
- STONE_27_GATE4_FUNCTIONAL_HUD.md

## Validation and observation

- Targeted HUD tests: **11 passed**.
- Covered QML load, real local conversation, authoritative proposal flow,
  wrong/stale-session/duplicate approval rejection, cancellation, malformed
  input, QML isolation, mock separation, and bounded event behavior.
- Normal Windows functional launch and screenshot capture succeeded without QML
  warnings after a local layout correction.
- The bridge uses one background worker and Qt signal delivery; no visible UI
  stall or queue-growth symptom was observed during the targeted review.

## Model routing

This Gate was completed by the current agent because model-specific delegation
capacity was unavailable. No Sol escalation was required and no Astra was used.
