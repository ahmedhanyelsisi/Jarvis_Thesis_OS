# Stone 27 Validation Audit

**Verdict: PASS.** Software validation and the authorized human acceptance
procedure passed on 2026-09-06. Stone 27 is approved for freeze, commit, tag,
and push.

## Capability matrix

| Capability | Status | Evidence / reason |
|---|---|---|
| Desktop shell, Core, cosmic environment, agent stones | REAL presentation | PySide6/QML Stone 27 module |
| Motion prototype | PROTOTYPE | Explicit --prototype mode only |
| Text conversation | REAL | Frozen ChatManager through RuntimeBridge |
| Approval, autonomy display, cancel | REAL | Frozen authorization/session authority |
| Runtime and EventBus health | REAL | Frozen bootloader/HealthMonitor |
| Workflow started/paused/completed/failed | REAL where emitted | Frozen EventBus adapter |
| Named live agent stone | UNAVAILABLE on observed frozen path | Agent topic has task ID, not trusted identity |
| Handoff / parallel visualization | UNAVAILABLE | No source/destination or concurrency evidence |
| Voice software / wake | AVAILABLE / DISABLED | Voice software present; wake disabled |
| Voice hardware | DEFERRED | Stone 30 acceptance requirement |
| Thesis context | UNCONFIGURED | No configured thesis root in HUD launch |
| Workspace, VS Code, Codex, LaTeX controls | DEFERRED | Stone 28 boundary |

## Security and isolation verdict

QML remains non-authoritative. It has no kernel, EventBus, filesystem, shell,
LaTeX, authorization-manager, audit-secret, or agent-runtime access. It submits
typed text, proposal ID, and cancellation requests to the Python bridge only.

Normal functional mode does not expose Gate 3 controls. Prototype mode does not
start the live runtime. Invalid, foreign-session, malformed, unknown-topic, and
unknown-agent runtime data cannot create trusted activity. Late workflow starts
cannot revive a terminal workflow. A post-terminal cancel does not claim
cancellation.

## Validation evidence

| Scope | Result |
|---|---|
| Stone 27 targeted HUD/hostile suite | 19 passed, 1 Chroma/Python deprecation warning |
| Complete regression: frozen, conversation/security, voice, Stone 27 | 426 passed, 1 skipped, 1 warning |

The one skip is the existing Windows symbolic-link privilege limitation in the
voice workspace test. It is not counted as a pass; reparse/junction, UNC,
drive-relative, containment, and traversal protections remain covered by tests.

The one warning is the existing Chroma telemetry use of a Python API deprecated
for Python 3.16. It does not fail the runtime or HUD.

## Performance and accessibility observation

The normal frozen-runtime boot reached live health in the targeted test. The
HUD uses one bridge worker, bounded event queue, terminal-event preservation,
Qt signal delivery, static Canvas geometry, and reduced-motion mode. No visible
UI stall, queue runaway, or shutdown mutation was observed in targeted checks.

Keyboard-native text input and buttons remain focusable. Labels/glyphs accompany
color states, error text is readable, and reduced motion is available in the
isolated prototype. Full assistive-technology validation remains a later
hardening task.

## Frozen boundary and freeze recommendation

Stone 27 changed only its HUD module and Stone 27 reports. Frozen Stones 1–26.5
were not modified. The external thesis repository retained its pre-existing
dirty state and was not modified by Stone 27.

**Freeze recommendation:** approved. Deferred items are voice hardware, wake
qualification, workspace/VS Code/Codex integration, and unavailable rich live
agent/handoff/concurrency signals.
