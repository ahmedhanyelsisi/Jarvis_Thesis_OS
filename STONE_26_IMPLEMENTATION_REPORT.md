# Stone 26 implementation report

Implemented 6 September 2026 on `phase-2-jarvis-experience` from base commit
`e49777b252652f04791dc17535545de3521ad08b`.

## Delivered

Stone 26 is an optional local voice interface in `17_VOICE_INTERFACE`. It runs
speech packages in a separate Python environment and uses a bounded JSON-lines
pipe to an audio worker. The worker accepts only status, device listing,
listen, speak, cancel, and shutdown operations; it has no generic backend or
shell execution operation.

The interface includes:

- Local faster-whisper recognition using a verified local base model.
- Local Piper synthesis, with an interruptible audio output path.
- Acoustic wake mode and push-to-talk capture, bounded speech segmentation,
  device enumeration, stop/cancel, mute, and worker-loss handling.
- Transcript provenance and recognition-quality checks. Missing or poor model
  diagnostics cause clarification, not execution.
- A local-only, read-only thesis-inspection adapter around the existing
  `ThesisWorkspaceManager`. It verifies a configured root, rejects links,
  bounds input size, checks the source fingerprint before and after work, and
  reports citation/structure results.
- Versioned session and UI event records for Stone 27 to consume later.
- A separate hash-locked package resolution, offline wheelhouse, model manifest,
  checksums, and an offline `doctor` command.

## Approved Stone 25/25.5 corrections

The required boundary corrections are limited to
`16_CONVERSATION_ENGINE`. They do not touch Stones 1–24.

- Voice confidence no longer changes the source into a confirmed authority.
- Text, agent, and memory have explicit input provenance. Agent/memory input
  cannot submit commands.
- Pending proposals bind session, target, payload, source fingerprint, scope,
  agent, expiry, and a one-time digest. A bare “yes” cannot approve anything.
- Voice cannot enable autonomous scopes. Enabling scopes requires a displayed
  proposal ID entered through the local text control.
- The authorization ledger uses an owner capability rather than a caller-name
  string and blocks dispatch if its required audit record cannot be written.
- Recovery persists allowlisted preferences only and always restores controlled
  mode.
- Agent permissions are checked at actual read-only dispatch, not only while
  forming a mock workflow.

The previous conversation tests were corrected because they asserted mock
execution strings and called a removed `is_autonomous()` method. They now assert
the actual authorization boundary.

## Observed capability

Using local Piper-generated fixtures, faster-whisper transcribed three thesis
inspection requests and each reached the real read-only citation checker. The
fourth fixture, “Enable autonomous mode,” was recognized but rejected because
voice cannot activate scopes. The inspection fixture detected one intentionally
missing bibliography entry and did not change any input file.

The local microphone/speaker devices are visible to the audio library. A live
wake attempt received no detected phrase before timeout. No audio was retained.
Therefore microphone capture and live playback are installed and ready for a
guided check, but are not validated as working on this room/device setup.

## Files and local state

Models, environment, wheelhouse, diagnostics, and local configuration are
excluded under `17_VOICE_INTERFACE/.gitignore`. Model assets use approximately
426 MB. The source implementation, tests, setup instructions, proposal, and
validation report are intended for review. No external thesis repository was
edited.

Stone 26 is implemented but should not be frozen until the hardening items in
the validation audit are resolved and a live hardware test passes.
