# Stone 26.5 validation audit

**Validation date:** 6 September 2026  
**Verdict:** approved for software freeze with explicit deferred hardware acceptance.

## Final software/security evidence

| Validation scope | Result |
|---|---|
| Targeted voice, authorization, PTT, path, and asset checks | 89 passed; 1 environment-limited symlink skip |
| Frozen Stones 1–24 regression | 294 passed; 1 third-party Chroma deprecation warning |
| Stone 25/25.5 conversation/security regression | 12 passed |
| Stone 26/26.5 voice regression | 101 passed; 1 environment-limited symlink skip |
| Final total | 407 passed; 2 documented skips; 1 warning |

The skipped symlink test is `test_linked_file_refused`. This Windows account
cannot create a symbolic link. It is recorded as **ENVIRONMENT-LIMITED / NOT
EXECUTED**, not a pass. Compensating tests cover junction/reparse attributes,
drive-relative and UNC root rejection, canonical containment, and traversal
rejection.

## Hostile validation

The completed suites cover unactivated voice, non-finite/missing confidence,
voice approval attempts, fake/replayed proposals, agent/memory provenance,
voice autonomy escalation, stale transcripts, cancellation, unsafe routes,
workspace link/traversal rejection, source changes, malformed IPC, worker
failure, model checksum/extra-file rejection, and frozen regression boundaries.

The persistent audit backend tests cover HMAC-authenticated events, protected
DPAPI state, recomputed rewrite, rollback, deletion, missing state, and
fail-closed dispatch. The backend deliberately does not claim protection from
arbitrary malicious code already operating as the same interactive Windows
user. `HighAssuranceWindowsServiceAuditBackend` remains an unimplemented future
extension point.

## Model delivery and wake

Model assets are checksum-pinned, staged and verified before promotion. The
manifest records source, revision, license, and release decision. Delivery is
download-on-first-run or user-supplied verified assets; no model binaries are
bundled. Wake is disabled by default and experimental only because measured
near-phrase selectivity was insufficient.

## Hardware acceptance

`DEFERRED_VOICE_HARDWARE_ACCEPTANCE` is retained for Stone 30 final product
acceptance. Real PTT hardware qualification is incomplete: Realtek device 15
produced no recognized text in the authorized one-minute test and TTS was not
reached. No raw audio was retained. This is not represented as a production
voice pass.

## Freeze recommendation

**STONE 26/26.5 SOFTWARE / SECURITY:** PASS  
**REAL HARDWARE VOICE ACCEPTANCE:** DEFERRED / INCOMPLETE  
**WAKE MODE:** EXPERIMENTAL / DISABLED  
**FREEZE:** APPROVED FOR SOFTWARE FREEZE WITH
`DEFERRED_VOICE_HARDWARE_ACCEPTANCE`.
