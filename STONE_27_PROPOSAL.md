# Stone 27 — JARVIS HUD / Desktop Experience proposal

**Status:** architecture proposal only. No desktop framework, UI code, or
frontend dependency is installed by this proposal.

## 1. Executive experience vision

Stone 27 turns JARVIS into an original Windows command environment: a calm
space-time field centred on a living JARVIS Core. It should feel like directing
real intelligence through a controlled cosmic instrument, never like a generic
chat dashboard or game menu. The visual system serves state, causality, and
human control; it never invents work for spectacle.

## 2. Design principles

- **Visual truth:** visible activity originates in real backend events.
- **Command first:** text, approvals, and readable results remain primary.
- **Calm depth:** motion communicates attention without visual fatigue.
- **Python authority:** presentation requests actions; Python validates and
  executes them through existing boundaries.
- **Accessible equivalence:** every color/motion state has text, glyph, and
  keyboard-accessible controls.
- **Original identity:** cosmic geometry, glyphs, and energy language are
  original; no franchise branding, logos, or copied HUD assets.

## 3. Experience journey

| Moment | Experience | Backend truth |
|---|---|---|
| Launch | calm core, health ring, thesis context, command transmission | restored safe session only |
| Request | command enters the core; request is shown in active-task layer | CommandCenter accepted input |
| Plan | structured arcs appear around the core | planner/workflow emitted a real plan |
| Approval | motion settles; scope/consequence dominates | Stone 25 authorization is waiting |
| Work | active agent nodes connect along actual handoffs | workflow/agent events are active |
| Result | convergence pulse then readable artifact/result workspace | terminal event and result exist |

## 4. Visual system and motion language

The Core is a faceted, layered energy object with thin orbital rings, sparse
stars, low-density dust, and bounded trajectory lines. A conventional desktop
frame holds all controls. The cosmic canvas communicates relationships only.

| Motion | Meaning |
|---|---|
| Calm orbit/breath | idle, healthy system |
| Inward particles | confirmed listening |
| Faster inner rings | thinking/processing |
| Structured arcs | planning |
| Directed trail | handoff or transfer |
| Connected constellation | real orchestration |
| Brief convergence | completed result |
| Contained discontinuity | degraded/error |

No flashing, shaking, or timer-driven fake progress is allowed. Minimized,
unfocused, low-power, or reduced-motion modes lower effects immediately.

## 5. JARVIS Core state machine

| State | Core behavior | Source |
|---|---|---|
| IDLE | slow stable orbit | no active request |
| LISTENING | incoming particles, explicit microphone label | confirmed VoiceSession capture |
| THINKING | modest internal acceleration | accepted request awaiting plan/result |
| PLANNING | rings/nodes assemble | planner/workflow planning state |
| WAITING_FOR_APPROVAL | stable core, dominant approval panel | authorization proposal exists |
| EXECUTING | directed trail to owner node | active task/agent event |
| ORCHESTRATING | multiple connected active nodes | real workflow handoffs |
| SPEAKING | controlled radial waveform | confirmed voice playback |
| COMPLETED | single convergence, then idle | terminal completed event |
| DEGRADED / ERROR | contained fault geometry and recovery action | health/bridge/backend fault |

## 6. Real agent inventory and agent-stone mapping

Primary visible identities are actual academic production agents: `PlannerAgent`,
`WriterAgent`, `ReviewerAgent`, and `BuilderAgent`. Legacy Literature, Citation,
LaTeX, Diagram, and Presentation roles appear as specialist capability satellites
only when real runtime evidence invokes them.

| Real identity/family | Role | Hue + glyph | Orbit / active behavior |
|---|---|---|---|
| PlannerAgent | decomposes and sequences work | violet, compass | wide orbit; structured plan arcs |
| WriterAgent | drafts structured thesis content | gold, quill-grid | focused inner orbit; outward creation trail |
| ReviewerAgent | evaluates quality/revisions | red, lens | counter-orbit; inspection pulse |
| BuilderAgent | assembles/builds outputs | amber, prism | grounded orbit; artifact trajectory |
| Research/Literature capability | source gathering | blue, beacon | satellite; inbound evidence stream |
| Citation capability | reference checking | cyan, linked mark | paired orbit; verification links |
| LaTeX capability | typesetting/build | orange, brackets | execution track to build artifact |
| Memory/context capability | session chronology | green, archive ring | quiet outer ring; contextual recall |

Color is never identity alone: label, glyph, role, and state are always present.
Dormant nodes remain quiet; no agent appears active without a matching event.

## 7. Single and multi-agent orchestration

A single agent moves from its resting orbit to a focused position, receives a
visible request trajectory, and exposes owner, task, state, and next outcome.
For a real workflow, only participating agents connect. A handoff is an
event-derived directed path with source, destination, dependency, and status.
Completion returns a result/artifact to the Core and then settles all nodes.

The trajectory model is: **request → understand → plan → approve → execute /
handoff → verify → complete**. It is a navigable constellation timeline, not a
generic progress bar. Users can expand each node for why it joined, what it did,
what it produced, and what is waiting.

## 8. Information architecture and layout

| Depth | Content |
|---|---|
| Ambient | Core, current state, active agent, thesis context, system health, voice qualification |
| Active task | request, transcript, plan, approvals, agent ownership, milestones, warnings |
| Expanded detail | research, citations, diffs, logs, provenance, diagnostics, event history |

**Full Command Center:** central core/canvas; top thesis and health strip;
left command/history rail; right active-task and approval rail; bottom readable
result/artifact drawer. **Compact mode:** small core, state label, PTT,
quick-command, active-agent indicator, expand control. Compact mode is a
future concept, not an implementation commitment.

## 9. Conversation, approval, autonomy, thesis, and health

Text is a persistent command transmission, with responses rendered as readable
HUD communications and expandable long-form academic content. History is
available, never dominant.

Approval is a high-priority state with exact request, target, scope,
consequence, expiry, **Approve**, **Edit Plan**, and **Cancel**. QML never
derives or grants approval. Scoped autonomy shows CONTROLLED/AUTONOMOUS,
authorized scope, TTL, permissions, and revocation; restart is always shown as
CONTROLLED until Python verifies otherwise.

Peripheral context shows current thesis/chapter/file, bibliography/build/Git
state, research/memory availability, and health for conversation, agents,
thesis, LaTeX, memory, and voice. Errors explain what failed, what still works,
and the recovery action; raw details live in an expandable diagnostics view.

## 10. Voice experience

PTT is explicit and backend-confirmed. The HUD includes device selectors,
mute/cancel, microphone activity, transcript, playback, and a visible
**UNQUALIFIED / DEGRADED** voice indicator. It must preserve text parity.
`DEFERRED_VOICE_HARDWARE_ACCEPTANCE` remains visible in diagnostics. Wake is
disabled/experimental, never automatic, and must not be represented as
qualified or as authorization.

## 11. Technology decision matrix

Weights: Python compatibility 30%, cinematic rendering 25%, desktop input and
accessibility 15%, packaging/security surface 15%, performance footprint 15%.

| Stack | Python | Visual | Input | Security | Footprint | Weighted | Decision |
|---|---:|---:|---:|---:|---:|---:|---|
| PySide6 + QML/Qt Quick | 9 | 7 | 8 | 8 | 8 | **8.1** | Primary |
| Electron + React + Three.js | 5 | 10 | 8 | 6 | 6 | **7.1** | Fallback |
| Tauri + React + Three.js | 4 | 9 | 8 | 6 | 9 | **7.0** | Do not select now |
| Local web/pywebview | 6 | 6 | 6 | 5 | 7 | **6.1** | Reject |

### Final recommendation

Use **PySide6 + QML/Qt Quick**. Qt Quick provides a native Windows scene graph,
custom geometry, shader-capable 2D effects, optional Qt Quick 3D, high-DPI
controls, and the smallest new boundary for an all-Python system. Keep the
cosmic field primarily 2D/procedural; 3D is decorative and bounded.

### Fallback

Use **Electron + React + Three.js** only if Gate 3 or Gate 11 demonstrates a
specific, essential, measured visual requirement that Qt Quick cannot meet.
Electron introduces Node/Chromium packaging and a hardened Python IPC boundary;
it is not a parallel implementation.

## 12. Rendering, event bridge, and frontend/backend contract

Python retains `UIManager → CommandCenter → JarvisKernel`, existing EventBus,
authorization, agents, subprocesses, DPAPI, and voice worker. A Stone 27
presentation adapter subscribes to `jarvis_core` and cognitive UI buses, then
creates immutable, versioned view snapshots for QML.

| Existing source | Normalized presentation event |
|---|---|
| `workflow.started/paused/completed/failed` | WORKFLOW_* |
| `agent.started/completed/failed` | AGENT_* |
| `build.*`, `session.*`, quality events | THESIS/BUILD/SYSTEM context |
| VoiceSession `state/transcript/response/playback/error` | VOICE_STATE, USER_TRANSCRIPT, JARVIS_RESPONSE, ERROR |
| Stone 25 proposal/approval/scope state | PLAN_CREATED, APPROVAL_REQUIRED, APPROVAL_GRANTED, AUTONOMY_CHANGED |

The normalized envelope contains version, sequence, timestamp, session ID,
workflow ID, agent ID, event type, provenance, and redacted payload. Python
coalesces progress at 10–30 Hz with latest-state wins; approvals, cancellations,
terminal events, and errors bypass coalescing. Qt queued signals marshal every
update to the GUI thread. QML owns only selection, expansion, and animation
phase. Every consequential QML action becomes a typed, correlated Python
request; QML receives a result, never a privileged object.

## 13. Security boundaries

- Never expose raw EventBus, kernel objects, filesystem/process APIs, secrets,
  DPAPI data, or authorization control keys to QML.
- Render transcripts, agents, file names, and diagnostics as plain untrusted
  text; never evaluate event content as QML/JavaScript.
- Python validates command, proposal, session, target, scope, and expiry using
  existing Stone 25/25.5 rules.
- Approval cards disable after submission and reject stale state.
- Bridge validation failure produces DEGRADED and blocks consequential UI state.
- Voice state cannot bypass command validation or authority controls.

## 14. Performance, Windows, and accessibility budgets

| Area | Target |
|---|---|
| Visible feedback | next 60 Hz frame where possible |
| User-visible event latency | p95 under 100 ms |
| Core rendering | 60 FPS active; 30 FPS under load/low power |
| Decorative GPU cost | about 4–6 ms/frame at 60 FPS tier |
| Idle mode | sparse particles, slow orbit, reduced GPU/CPU |
| Startup | interactive shell before noncritical history loads |

Throttle or pause effects when minimized, occluded, on battery, or behind frame
budget. Support Intel integrated graphics, static fallback, mixed-DPI monitors,
custom chrome only after native window behavior works, tray/compact mode later,
and deterministic shutdown/recovery. Test 100/125/150/200% scaling.

Keyboard navigation, visible focus, high contrast, screen-reader labels,
reduced motion/animation-off, text equivalents, touch-sized controls, long-form
reading, and a flat list alternative are release requirements.

## 15. Packaging, testing, and visual acceptance

Packaging is a future Qt Windows package with local Python assets and existing
voice-model policy preserved. It must not bundle prohibited models or claim
hardware-qualified voice. Tests will include view-model reducers, bridge schema
and ordering/coalescing, command/approval authority, recorded-event replay,
thread marshalling, accessibility/navigation, DPI, GPU tiers, degraded mode,
and real-agent orchestration truth.

Visual acceptance follows: architecture approval → static visual concept →
motion prototype → functional HUD → final validation. The static and motion
gates prevent building the wrong experience.

## 16. Implementation checkpoints and model plan

| Checkpoint | Scope | Primary model |
|---|---|---|
| 27A | desktop shell, bridge contracts | Terra medium |
| 27B | Core and state renderer | Terra; Sol only for hard rendering |
| 27C | cosmic environment and quality tiers | Terra |
| 27D | ambient/active/detail HUD layers | Terra + Luna mechanical work |
| 27E | real agent-stone view models | Terra |
| 27F | orchestration trajectories | Terra; Sol for complex concurrency |
| 27G | conversation and voice state | Terra |
| 27H | approval/autonomy presentation | Terra |
| 27I | thesis/system health | Terra |
| 27J | performance/accessibility polish | Luna/Terra |
| 27K | validation and gate evidence | Luna/Terra |

Luna handles inventories, repetitive styling/tests, and reports; Terra handles
ordinary implementation; Sol is reserved for demonstrably difficult rendering,
IPC, or concurrency failures. Astra is not used for Stone 27 implementation.

## 17. Risks and required user decisions

| Risk | Response |
|---|---|
| Visual spectacle obscures productivity | conventional controls, text equivalents, reduced motion |
| UI drifts from runtime truth | event-derived state and no simulated progress |
| Event bursts freeze GUI | queued signals, bounded queues, coalescing, virtualization |
| GPU variation | quality tiers and static fallback |
| QML acquires business rules | typed Python bridge; QML presentation only |
| Experimental voice misleads | explicit unqualified/degraded indicator |

Decisions requested at Gate 1:

1. Approve PySide6 + QML/Qt Quick as the primary stack and Electron + React +
   Three.js as the evidence-triggered fallback.
2. Approve the original cosmic agent-stone identity and the primary agent
   mapping above.
3. Choose whether the initial visual concept should use a **minimal orbital
   2D Core** or a **restrained 3D faceted Core** for Gate 2.
4. Confirm that voice remains visibly unqualified until Stone 30 hardware
   acceptance.

## 18. Final recommendation

Approve the architecture, then produce a static visual concept before any
motion or functional HUD implementation. The immediate-launch test is simple:
the user should perceive a living space-time intelligence environment while
still finding command, approval, status, and thesis results instantly.
