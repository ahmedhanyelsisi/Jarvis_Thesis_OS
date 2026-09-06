# Stone 26.5 hardening proposal

**Status:** proposal only — no Stone 26.5 implementation has started.  
**Prerequisite:** Stone 26 remains unfrozen. Stone 27 must not start.  
**Baseline:** `phase-2-jarvis-experience`, Stone 25/25.5 commit
`e49777b252652f04791dc17535545de3521ad08b`, plus the present uncommitted
Stone 26 implementation and its validation audit.

## Purpose and acceptance position

Stone 26.5 is a Windows-focused hardening and acceptance increment for the
local voice interface. It must turn the current “installed and smoke-tested”
implementation into a bounded, evidenced local capability before any Stone 27
HUD or experience work consumes it.

Until this increment passes, **push-to-talk is the only supported activation
mode**. Wake mode remains an explicit experimental diagnostic and is never an
authorization boundary. Voice remains limited to the existing read-only thesis
inspection capability. It must not write, compile, export, perform operating
system actions, enable autonomy, or approve a proposal.

Stone 26.5 will pass only when its hardware, security, regression, and
distribution gates below pass and the approved ledger decision is implemented.
Otherwise the correct outcome is a documented follow-on hardening increment,
not Stone 27.

## Evidence from the current implementation

The evidence below comes from the present source, tests, model manifest, and
Stone 26 validation record.

| Gap | Confirmed evidence | Consequence |
|---|---|---|
| Wake selectivity | Synthetic `Hey Jarvis` scored 0.998 but `Hello Jarvis` scored 0.916 against the configured 0.6 threshold. | Hands-free activation is not selective enough to support. |
| Real hardware acceptance | Devices enumerate, but the live wake attempt timed out. There is no observed microphone-to-transcript-to-speaker completion. | Capture, playback, cancellation, and device recovery remain unproven. |
| PTT interaction | `/listen` starts a real capture turn, but it is a console command rather than a hold-to-talk control and has only fixture coverage. | The supported mode needs a guided real-device acceptance test. |
| Speech quality evidence | Four synthesized phrases were a provider smoke test. There is no representative corpus, WER, latency distribution, accent/noise result, or user hardware result. | No accuracy or responsiveness claim is justified. |
| Windows reparse protection | `WorkspaceBackend` rejects `is_symlink()` and, where exposed, `is_junction()`. The symlink test is skipped under this account and junction/reparse behavior is not demonstrated. | Root confinement needs Windows-specific hostile testing. |
| Ledger integrity | The JSONL ledger has an unkeyed SHA-256 chain and takes its trusted head from the same file on restart. A recomputed rewrite, valid-prefix rollback, empty/deleted replacement, or competing process is not stopped by the current design. | Gap 26-E remains open for a malicious same-user process. |
| Distribution terms | Faster-whisper base is recorded as MIT. Piper is GPL-3.0 and its voice card controls voice terms. openWakeWord code is Apache-2.0 while supplied pretrained assets are CC BY-NC-SA 4.0. | The current local install is not a release-ready distributable package. |
| Asset repair | `provision_models.py` can regenerate the manifest during explicit repair. A prior staging copy overwrote the live manifest until it was restored. | Packaging/repair must avoid replacing an installed verified manifest unexpectedly. |

The existing good boundaries are retained: model confidence is a quality signal,
the worker has no generic execution operation, voice cannot activate autonomy,
approvals are one-time and short-lived, and the existing backend is read-only.

## Target architecture

### 1. Activation, capture, and session recovery

The production path will be push-to-talk first. Stone 26.5 will add a small
local acceptance harness and a proper PTT interaction contract: user begins a
turn, capture is bounded, release/stop cancels promptly, transcript quality is
shown, and audio is discarded after processing. No microphone recording is
stored by default.

The harness will enumerate input/output devices, make the selection explicit,
exercise capture, transcription, a safe read-only fixture inspection, speech
output, `/stop`, `/cancel`, mute, device loss/reselection, and a simulated
sleep/resume/restart path where Windows permits it. It writes a structured
result containing device identifiers, timestamps, response classifications,
latencies, and user yes/no playback confirmation; it never writes raw audio.

Wake experimentation remains separate from the PTT path. It will collect
activation scores, test exact and near phrases, and require a post-detection
transcript check for the exact normalized wake phrase before opening the
command window. This is a usability guard only; it does not prove speaker
identity or authorize anything. If the measured gate fails, `/wake` stays
diagnostic-only or is removed from the normal console.

### 2. Benchmark and quality evidence

Add a versioned, text-ground-truth corpus and benchmark runner. The initial
corpus will have at least 30 cases: normal thesis inspections, citations and
chapter terms, names/identifiers, silence and unrelated speech, near wake
phrases, interruption/cancellation, and quiet/noisy variants. Synthetic audio
can exercise deterministic provider integration; it cannot substitute for
human acoustic validation.

The acceptance run will also use a short, consented interactive set on the
actual Realtek input/output path. It processes samples in memory and records
only the expected text, recognized text, aggregate word-error rate, activation
result, timing, and user playback confirmation unless the user explicitly
chooses retained test audio. Metrics are:

- word-error rate (word-level Levenshtein), command success rate, and rejected
  unsafe-command rate;
- p50/p95 capture-to-transcript, transcript-to-result, TTS generation, and
  end-to-end latency;
- wake false accepts and false rejects by corpus category;
- cancellation time and recovery after worker/device failure.

Initial proposed gates are: all unsafe voice requests rejected; no false wake
accept in the required near-phrase/negative corpus; PTT command success at
least 95% in the approved real-device sample; cancellation reaches a controlled
state within two seconds; and no unhandled device failure. The eventual WER and
latency ceilings must be chosen after one measured baseline rather than
invented before the hardware measurement.

### 3. Windows workspace confinement

Harden traversal around a Windows-specific path-policy helper. It will reject
UNC, drive-relative, absolute user-supplied child paths, malformed relative
segments, and every reparse-point component discovered through `lstat` and
Windows file attributes before content is opened. It will compare canonical
paths with a Windows-safe root containment check, then repeat root/fingerprint
checks before and after work. File opening and fingerprinting will be arranged
to minimize check/open replacement windows and to reject any changed
metadata/content during the operation.

Tests will create an actual junction with `mklink /J` when available, exercise
external targets, in-root targets, symlinks, renamed roots, and a simulated
reparse attribute seam when privileges are unavailable. The report will state
which real Windows test ran and which was unavailable; an unavailable privileged
test is not a silent pass.

### 4. Tamper-evident ledger and the same-user boundary

The current hash chain is retained only as legacy local evidence. A
CurrentUser-DPAPI-wrapped HMAC key would improve protection against offline
file copying and another ordinary account, but a malicious process using the
same interactive logon can invoke DPAPI too. It therefore **does not close**
the stated same-Windows-user threat and must not be described as process
isolation.

The recommended implementation is a narrow, local **Windows audit broker**
running under a dedicated, minimally privileged service identity. The broker,
its key, durable ledger head/sequence, configuration, and executable/runtime
must live outside the interactive user’s write/decrypt authority. It exposes no
generic signing operation. Instead it validates bounded event types and writes
its own canonical record containing schema version, ledger epoch,
service-assigned sequence, previous digest, request ID, timestamp, and bounded
payload. Records use domain-separated HMAC-SHA-256. Ledger append and durable
head advancement happen in one transaction; a receipt is returned only after
durable commit.

The interactive authorization manager keeps proposal ownership, expiry,
single-use behavior, and “audit before dispatch.” It receives an audit receipt
from the broker and fails closed if the broker is unavailable, receipt is
invalid, an epoch/key changes unexpectedly, or a recovery condition occurs.
On migration, the old unsigned JSONL ledger is archived and explicitly marked
as legacy evidence; it never restores a scope or approval.

The broker uses a local-only named pipe with a strict DACL, no remote clients,
bounded framing, request IDs, timeouts, rate limits, and a single writer.
Service installation must protect the service definition, code, interpreter,
imports, key/state, and data directory with ACLs that deny modification by the
interactive account. A service loading Python from this writable development
checkout would not satisfy the intended boundary.

This claim remains deliberately limited: it protects committed history from
direct rewrite, deletion, and key extraction by an ordinary process under the
interactive account, assuming Windows service isolation and ACLs hold. It does
not prove that a new client request is human-originated. A compromised client
can submit false claims through an allowed channel; administrator, SYSTEM,
kernel, and physical compromise remain out of scope.

### 5. Assets, licensing, and delivery

Stone 26.5 will keep runtime offline and use a manifest with pinned revisions,
checksums, licenses, provenance, an asset epoch, and explicit install state.
Repair will stage and verify all downloads first, then atomically replace only
the asset directory; it will not overwrite a verified live manifest during a
source copy or failed repair.

The default release policy proposed here is **no bundled model binaries**.
First-run setup will either download the approved assets after presenting their
terms or accept user-supplied verified assets. The final distribution manifest
will include required notices and an allowlist of model/license combinations.
No packaged release may include the current openWakeWord pretrained assets
unless the distribution is compatible with their CC BY-NC-SA 4.0 terms. Piper
engine and selected voice terms require a release-specific review. This is
supported by the upstream Piper GPL-3.0 repository, Piper voice documentation,
openWakeWord’s license statement, and the faster-whisper-base model card
([Piper](https://github.com/OHF-Voice/piper1-gpl),
[Piper voices](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/VOICES.md),
[openWakeWord](https://github.com/dscripka/openWakeWord/blob/main/README.md?plain=1),
[faster-whisper base](https://huggingface.co/Systran/faster-whisper-base)).

## Implementation sequence

1. Create a reproducible Stone 26 baseline inventory and retain the existing
   regression results; do not freeze/tag it yet.
2. Add the PTT acceptance harness, non-audio result schema, fixture corpus, and
   benchmark runner; run it first against the safe fixture, then the chosen
   read-only thesis workspace.
3. Implement path-policy/reparse hardening and its Windows junction, symlink,
   race, and regression tests.
4. Implement the approved ledger option behind an `AuditBackend` interface,
   migration behavior, fail-closed receipts, service packaging/ACL checks, and
   hostile Windows tests.
5. Add wake calibration/second-stage phrase checks only as experimental work;
   decide whether it meets the gate after measured results.
6. Harden manifest repair and document the selected distribution model/notices.
7. Run the entire frozen suite, revised Stone 25/25.5 security suite, Stone 26
   suite, 26.5 hostile tests, offline doctor, real-provider smoke, and the
   guided hardware matrix. Publish a validation audit with raw aggregate
   measurements and any skipped Windows capability explained.

## Required hostile and regression coverage

The new test plan includes cold-start ledger rewrite with recomputed hashes,
valid-prefix rollback, empty/delete/replacement, duplicate request IDs,
concurrent writers, partial commit, broker loss, unauthorized pipe client,
oversized IPC, and legacy migration. It also includes same-user attempts to
read or alter broker state/code, where the service is actually installed.

Voice coverage includes replay/stale results, near wake phrases, unsafe voice
requests, missing diagnostics, stop/cancel/mute, worker crash, device changes,
and return to controlled mode. Workspace coverage includes external junctions,
symlinks, reparse attributes, race/renamed root, oversized files, and unchanged
read-only thesis content. All existing Stones 1–24 hashes and the established
Stone 25/25.5 regressions remain required gates.

## Decisions needed before implementation

1. **Ledger boundary — recommended:** approve the dedicated Windows audit
   broker/service and its administrative installation/ACL requirement. The
   alternative is to use CurrentUser DPAPI HMAC only and explicitly defer the
   malicious same-user requirement; it cannot claim to close Gap 26-E.
2. **Wake policy — recommended:** keep PTT as the supported release mode and
   retain wake only as opt-in experimental diagnostics until it passes the
   measured false-accept/false-reject gate. A custom enrolled wake model would
   be a later privacy and training decision.
3. **Audio privacy — recommended:** retain no test audio; record only aggregate
   results and transcripts. Retained, consented samples would improve
   reproducibility but require a storage/retention policy.
4. **Model delivery — recommended:** user-supplied or first-run verified
   downloads, with no bundled model assets until a distribution legal review
   approves each selected model and notice set.
5. **Hardware target:** approve a safe fixture first and then the external
   thesis workspace for a read-only run, or limit acceptance to the fixture.
6. **Windows test environment:** allow a Developer Mode/privileged CI machine
   if this account cannot create a real symbolic link; junction tests will run
   here where feasible.

## Exit criteria and next step

Stone 26.5 can be recommended for freeze only after the chosen ledger boundary
is demonstrated, the real PTT hardware matrix passes, Windows reparse coverage
is evidenced, distribution status is explicit, and every regression/hostile
gate passes. A wake failure does not block PTT-only release, but it does block
hands-free wake support. Any failed required gate produces a focused 26.5.x
hardening increment; Stone 27 remains blocked.

**No code, configuration, model asset, or external thesis file is changed by
this proposal. Approval of the decisions above is required before Stone 26.5
implementation begins.**
