# Stone 26.5 hardware acceptance report

**Status:** incomplete — do not use as a release acceptance pass.

## Authorized test record

The test retained no raw microphone audio. The final stored result contains
only the fields authorized for this run.

| Field | Result |
|---|---|
| Selected input device | Realtek device 15 |
| Selected output device | Realtek speakers device 4 |
| Expected text | `check thesis citations` |
| Recognized text | none |
| Capture latency | 60,008 ms |
| Command/result classification | error before read-only inspection |
| TTS playback heard | not reached |
| Pass | no |

## Investigation

The first endpoint (device 1) delivered a low but non-zero level, with maximum
RMS 0.001609. Device 15 delivered maximum RMS 0.002014. The original VAD
threshold (0.012) was above those measurements; the local PTT configuration
was recalibrated to device 15, 48 kHz, and VAD 0.001. A subsequent one-minute
run still produced no recognized text.

No authorization, write operation, compilation, export, or external thesis
change occurred. The selected thesis workspace was opened only through the
existing read-only inspection adapter.

## Decision

At the user's request, further live PTT attempts are skipped for this increment.
The hardware acceptance gate remains open. A future PTT-only freeze requires a
successful observed microphone-to-transcript-to-read-only-result-to-heard-TTS
turn and a non-audio record of that result.
