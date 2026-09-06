# Stone 26.5 implementation report

**Status:** implemented; not frozen.  
**Base:** `e49777b252652f04791dc17535545de3521ad08b` plus Stone 26.

## Delivered

- Added the one-turn PTT acceptance harness and `ptt-acceptance` CLI command.
  It performs device checks, one bounded capture, only read-only thesis
  inspection, TTS, and forced cleanup. The persisted record contains only
  device IDs, expected/recognized text, latency, command classification,
  playback-heard status, and pass/fail. Raw audio is never retained.
- Calibrated the local Realtek configuration from non-recorded level probes.
  The selected capture endpoint is device 15 at 48 kHz with a 0.001 PTT VAD
  threshold. This is an unvalidated local setting, not a hardware pass.
- Disabled wake by default through `wake_experimental: false`. It remains
  experimental because the prior synthetic probe accepted both `Hey Jarvis`
  and `Hello Jarvis`.
- Hardened workspace root handling: UNC and drive-relative roots are rejected;
  traversal rejects symlinks, junctions, and Windows reparse attributes before
  reading; canonical containment is checked for each candidate.
- Replaced the persistent unkeyed audit chain with `AuditBackend`.
  `WindowsDPAPIAuditBackend` uses a per-user DPAPI-protected HMAC-SHA-256 key
  and separate DPAPI-protected sequence/head anchor. Altered, replaced,
  deleted, or rolled-back persisted history fails closed at restart.
- Added the reserved `HighAssuranceWindowsServiceAuditBackend` extension point.
  The local backend does not claim protection from arbitrary malicious code
  already running as the same interactive Windows user.
- Hardened provisioning: model files and manifest are staged, checksum-verified,
  then replaced as a pair with rollback on replacement failure.
- Added the no-bundle model delivery policy. Runtime remains offline after
  explicit verified setup; selected model terms prevent a redistributable bundle.

## Validation

| Scope | Result |
|---|---|
| PTT, authorization, and workspace focused tests | 70 passed, 1 expected symlink-permission skip |
| Configuration and PTT tests after wake policy | 22 passed |
| Full frozen suite | 294 passed, 1 third-party deprecation warning |
| Conversation/security suite | 12 passed |
| Voice suite | 101 passed, 1 symlink-permission skip |

## Residual limits

- Real PTT capture did not obtain a usable transcript and was subsequently
  skipped by user instruction. Stone 26.5 therefore cannot freeze yet.
- Wake is disabled/experimental. Its failure does not block a future PTT-only
  freeze once PTT hardware acceptance succeeds.
- Local DPAPI/HMAC protects persisted local state from ordinary file alteration
  under the assumed Windows boundary. It does not protect against malicious
  code already running as the same interactive user.
