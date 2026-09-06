# Stone 27 Gate 2 — Static visual concept

**Gate:** 2 — awaiting user visual approval.
**Boundary:** mock-only presentation; no JARVIS runtime, EventBus,
authorization, agent, or voice control is connected.

## Environment

| Dependency | Version | Purpose |
|---|---:|---|
| PySide6 | 6.11.2 | Windows desktop shell, QML, Qt Quick, Qt Quick 3D runtime |
| pytest-qt | 4.5.0 | focused Qt/QML smoke testing |

The dependencies are installed in the existing project `.venv` and pinned in
`18_JARVIS_HUD/requirements-hud.in`. Qt 6.11.2, QML, Qt Quick, and Qt Quick 3D
imports were verified.

## Gate 2 composition

The launchable static command center has a deep-space gradient and sparse star
field, an original faceted luminous Core with orbital rings, six labelled agent
stones, a mission trajectory, command/history and thesis-health rail, and an
active-task/approval rail. The static example deliberately says **VISUAL
CONCEPT / MOCK STATE** and states that no approval request is sent.

The primary nodes map to the approved real agent families: Planner (violet),
Writer (gold), Reviewer (red), Builder (amber), Research (blue), and Memory
(green). Each has a glyph and label; color is supplementary.

Voice remains visibly **UNQUALIFIED**. Wake is not offered. The panel is a
static approval presentation, not an authorization implementation.

## Files

- `18_JARVIS_HUD/app/main.py` — local launch and preview capture.
- `18_JARVIS_HUD/qml/Main.qml` — static QML visual concept.
- `18_JARVIS_HUD/tests/test_gate2_shell.py` — QML/runtime smoke checks.
- `18_JARVIS_HUD/requirements-hud.in` — pinned Gate 2 dependencies.

## Launch and preview

```powershell
D:\Masters\Jarvis_Thesis_OS\.venv\Scripts\python.exe -B -m app.main
```

Run that command from `D:\Masters\Jarvis_Thesis_OS\18_JARVIS_HUD`.

The Windows-rendered preview is `stone27_gate2_preview_windows.png`. An
off-screen preview may not resolve the desktop font atlas correctly, so it is
not the visual-review artifact.

## Verification and performance

Focused checks cover Qt imports, QML static boundary, and QML loading. The
normal Windows capture launched and exited successfully. The composition uses
Canvas/vector drawing and a sparse static field; no continuous particle system,
backend stream, or heavy 3D scene runs at Gate 2.

## Unresolved decisions / Gate 3 scope

User approval is required before work begins on motion. Gate 3 will add only
the restrained Core/agent-stone/orchestration motion prototype, measured quality
tiers, and state-transition visuals. It will not begin functional HUD or backend
integration.
