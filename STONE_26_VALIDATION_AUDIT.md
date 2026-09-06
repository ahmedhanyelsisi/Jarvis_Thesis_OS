# Stone 26 validation audit

Validated 6 September 2026. Base branch: `phase-2-jarvis-experience`.

## Results

| Check | Result |
|---|---|
| Frozen Stones 1–24 source hashes | 317 checked, 0 changed |
| Frozen regression suite | 294 passed; 1 third-party deprecation warning |
| Conversation/security suite | 12 passed |
| Stone 26 suite | 93 passed, 1 skipped |
| Worker lifecycle suite | 6 passed; included in Stone 26 total |
| Offline voice `doctor` | Passed: six packages and five checksum-verified local models ready |
| Real provider smoke test | Passed with synthesized local audio: transcription, read-only inspection, and voice-scope rejection |
| Real microphone/wake test | Inconclusive: no activation before timeout; no audio persisted |
| Real speaker playback | Not human-confirmed |
| External thesis changes | None |

The skipped test requires Windows symlink creation permission. It checks refusal
of a linked file. The implementation contains this check; validation remains
incomplete for Windows junctions and privileged symlink creation.

## Security validation

The automated checks cover malformed/oversized IPC, unknown worker operations,
stale/replayed turns, missing/non-finite recognition diagnostics, unactivated
voice, voice attempts to enable autonomy, exact local approval text, proposal
replay, changed payload/target/source, permission denial at dispatch, corrupted
preferences/audit records, worker crash, cooperative cancellation, forced worker
termination, and cancellation while inspection is running.

The implementation correctly treats model confidence as a quality signal rather
than proof of user approval. Audio worker messages cannot carry an authorization
origin or a generic execution request.

## Findings that block a Stone 26 freeze

1. **Wake phrase calibration is not safe to freeze.** In the local synthetic
probe, “Hey Jarvis” scored 0.998, but “Hello Jarvis” also scored 0.916 above the
configured 0.6 threshold. The model is useful as an activation hint, but this
false activation makes hands-free wake mode insufficiently selective.
2. **Live microphone and speaker behaviour is unproven.** The local devices
enumerate and packages/models load, but the first live wake run timed out with
no captured activation. This needs an observed push-to-talk test, an acoustic
wake test, output confirmation, and tests after sleep/resume or device removal.
3. **The provider test set is too small for a quality claim.** Four synthesized
phrases are a smoke test, not an accuracy study. It lacks the planned 100-command
set, ambient-noise sample, accents, chapter identifiers, and technical vocabulary.
4. **Model-distribution policy needs an explicit decision.** Piper's engine and
voice data have different licensing considerations; openWakeWord's pretrained
model has CC BY-NC-SA 4.0 terms. This is suitable for the user's local setup,
but must be resolved before a distributable desktop application.
5. **The audit ledger is local integrity evidence, not tamper-proof storage.**
Another program running as the same Windows user may remove or replace it. The
runtime fails closed for the active ledger path, but a protected key store or
external append-only service would be needed for stronger claims.

## Recommendation

Do **not** move directly to Stone 27 or freeze Stone 26. Run a short
**Stone 26.5 Voice Hardening** increment first. It should calibrate or replace
the wake detector, complete the real hardware acceptance matrix, add a recorded
test corpus and metrics, test Windows device lifecycle behaviour, and decide the
distribution/licensing model. Keep push-to-talk as the supported activation mode
until those conditions pass.

Stone 27 can consume the already-defined event and transcript contracts after
that hardening gate. It should not turn unvalidated wake mode into a default HUD
feature.
