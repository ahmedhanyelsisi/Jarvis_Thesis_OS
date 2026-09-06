# Stone 27 Gate 3 — Motion Prototype

**Status:** ready for Gate 3 motion approval.
**Boundary:** a QML-only development prototype. It has no production runtime,
authorization, real-agent, voice, filesystem, or workflow connection.

## Motion grammar and states

The isolated motion controller provides semantic visual states: calm/idle,
attention, thinking, planning, waiting for approval, executing, orchestrating,
speaking, completed, and contained error. The Core responds through restrained
rotation, singularity breathing, scale and intensity changes, while the scene
continues to use the approved static space-time composition.

Agent stones support dormant, awakening, waiting, receiving, active, verifying,
completed, and returning visual states. Their aura, faceted body, glyph
brightness, scale, and gentle predictable orbital offset communicate state.

## Demonstrations

- **Single agent:** a mock Chapter 3 literature request moves from attention and
  planning, through mock approval, Core → Research transfer, research activity,
  return transfer, completion, and idle.
- **Sequential orchestration:** Research → Writer → Reviewer → Builder is
  displayed with one active handoff at a time. The Core remains the conductor.
- **Parallel orchestration:** Research and Citation activate together, receive
  distinct transfers, then converge into Writer and return to the Core. This
  visibly differs from the sequential chain.
- **Mission trajectory:** REQUEST through COMPLETE advances with the active mock
  scenario; approval pauses at APPROVE without execution flow.

Directed energy handoffs use a thin curved route and one controlled luminous
packet. Slow stone offsets, Core rotation, and parallax-like clock offsets add
depth without a particle engine. Reduced Motion stops the orbit rotation and
breathing while retaining all readable states.

## Local demonstration

From D:\Masters\Jarvis_Thesis_OS\18_JARVIS_HUD:

    D:\Masters\Jarvis_Thesis_OS\.venv\Scripts\python.exe -B -m app.main

Use the panel labelled **MOTION PROTOTYPE / DEVELOPMENT ONLY**. It exposes
Idle, Thinking, Wait Approval, Single Agent, Sequential, Parallel, Speaking,
Completed, Reduced Motion, and Error demonstrations. **APPROVE MOCK PLAN**
only starts the visual sequential demo; it does not make an authorization call.

Supplementary preview:
C:\Users\user\Documents\Codex\2026-09-05\hi\outputs\STONE_27_GATE3_MOTION_PREVIEW.png

## Files changed

- 18_JARVIS_HUD/qml/Main.qml
- 18_JARVIS_HUD/app/main.py
- 18_JARVIS_HUD/tests/test_gate2_shell.py
- STONE_27_GATE3_MOTION_PROTOTYPE.md

## Validation and observation

- Focused QML/controller tests: **5 passed**.
- The tests cover QML load, motion-controller state change, reduced-motion
  presence, representative scenarios, and textual isolation from production
  authority interfaces.
- Normal Windows launch and preview capture succeeded. The active scene uses
  Qt item transforms plus one lightweight transfer Canvas; no obvious UI stall,
  runaway allocation, or rendering warning was observed during the review.

## Model routing

This Gate was completed by the current agent after model-specific delegation
capacity was unavailable. No Sol escalation was needed, and no Astra was used.

## Remaining Gate 3 limits

This is not a production state machine or performance campaign. It does not
include recorded video, live event integration, compact layouts, sound,
advanced shaders, or full error/degraded choreography. Those remain outside
the approved Gate 3 motion prototype.
