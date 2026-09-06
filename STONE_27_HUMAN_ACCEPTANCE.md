# Stone 27 Human Acceptance

Run these checks from D:\Masters\Jarvis_Thesis_OS\18_JARVIS_HUD.

## Normal functional HUD

    D:\Masters\Jarvis_Thesis_OS\.venv\Scripts\python.exe -B -m app.main

1. Confirm the cosmic JARVIS Core and agent-stone visual identity appear.
2. Confirm **Runtime** and **Event Bus** report **ONLINE** after startup.
3. Enter status in the left input and confirm a real local response appears.
4. Enter enable autonomous mode; confirm a real proposal with an ID appears.
5. Select **CANCEL REAL REQUEST** and confirm the pending request disappears.
6. Close the window normally.

## Isolation and degraded truth

    D:\Masters\Jarvis_Thesis_OS\.venv\Scripts\python.exe -B -m app.main --prototype

Confirm the motion controls appear and no production Runtime/Event Bus health is
booted or used.

    D:\Masters\Jarvis_Thesis_OS\.venv\Scripts\python.exe -B -m app.main --no-runtime

Confirm the HUD remains usable and reports the runtime as unconfigured rather
than ONLINE.

## Acceptance record

Approve Stone 27 only if the checks above pass and the display remains readable
and responsive. Voice hardware acceptance is not part of this procedure; it is
deferred to Stone 30. The frozen runtime does not currently provide trusted
named-agent, handoff, or concurrency evidence, so those elements should not
appear as live production activity.

**Result: PASS — 2026-09-06.** The authorized human acceptance procedure was
completed successfully. Stone 27 is approved to enter its freeze workflow.
