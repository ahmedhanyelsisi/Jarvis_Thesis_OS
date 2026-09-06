# Stone 26 voice interface

Stone 26 adds an optional, local Windows voice interface. It does not modify the
frozen Stones 1–24. It offers one verified backend operation: a read-only
workspace-wide LaTeX/citation inspection. Writing, research generation,
compilation, export, and operating-system actions are deliberately unavailable.

## Safety model

- Microphone audio is held in memory only while an utterance is processed; it is
  not saved by the voice runtime.
- “Hey Jarvis” and push-to-talk only activate listening. They never authorize
  an action.
- A transcript's recognition quality is used only to request repetition. It
  never upgrades authority.
- Voice can request a read-only inspection and can cancel. It cannot enable
  autonomous scopes or approve writing/compile/export actions.
- Scope activation requires the exact proposal ID in the local text control.
  Proposals expire after 60 seconds and are consumed once.
- Muting, cancellation, worker failure, restart, and session end return the
  session to controlled mode and revoke pending authorization.

The audit log detects ordinary alteration of its hash chain. It is not a
security boundary against another program running as the same Windows user.

## Setup

The project includes a separate environment at `17_VOICE_INTERFACE/.venv`, a
hash-locked dependency file, an offline wheelhouse, and local model assets.
Model revisions and checksums are in `model_manifest.json`. The assets are
excluded from Git through `.gitignore` because they are large local runtime
dependencies, not project source.

Check that the local setup is ready without opening a microphone:

```powershell
17_VOICE_INTERFACE\.venv\Scripts\python.exe -B 17_VOICE_INTERFACE\launch.py doctor --config 17_VOICE_INTERFACE\voice_config.example.json --worker-python 17_VOICE_INTERFACE\.venv\Scripts\python.exe
```

List devices:

```powershell
17_VOICE_INTERFACE\.venv\Scripts\python.exe -B 17_VOICE_INTERFACE\launch.py devices --config 17_VOICE_INTERFACE\voice_config.example.json --worker-python 17_VOICE_INTERFACE\.venv\Scripts\python.exe
```

Run one bounded push-to-talk acceptance check against an explicit thesis folder.
It enumerates the configured input/output devices, performs one PTT capture,
permits only the read-only inspection route, speaks the result, then stops the
worker. Its JSON result records operational metadata only; it never stores PCM
or transcript/reply text. Wake mode and ledger testing are outside this check.

```powershell
17_VOICE_INTERFACE\.venv\Scripts\python.exe -B 17_VOICE_INTERFACE\launch.py ptt-acceptance --config 17_VOICE_INTERFACE\voice_config.local.json --worker-python 17_VOICE_INTERFACE\.venv\Scripts\python.exe --thesis-root D:\path\to\thesis --ptt-timeout 60
```

Create a local configuration such as `voice_config.local.json` to select a
microphone and output device. The example configuration is safe to copy and is
not changed at runtime. It validates English only in this release.

Start the local control console:

```powershell
17_VOICE_INTERFACE\.venv\Scripts\python.exe -B 17_VOICE_INTERFACE\launch.py chat --config 17_VOICE_INTERFACE\voice_config.local.json --worker-python 17_VOICE_INTERFACE\.venv\Scripts\python.exe --thesis-root D:\path\to\thesis
```

The console begins muted. Type `/enable`, then `/listen` for push-to-talk or
`/wake` for acoustic wake mode. Type `/stop` to stop audio, `/cancel` to revoke
the current request and authorization state, `/mute` to close capture, and
`/quit` to shut down. In the text console, `check thesis citations` is the
available end-to-end operation.

Wake detection is tuned only provisionally. The supplied model recognized both
“Hey Jarvis” and “Hello Jarvis” in synthesized checks, so do not rely on the
wake phrase as a strict phrase boundary or identity check. Use push-to-talk in
quiet/private environments until calibration is completed.

## Stone 26.5 PTT acceptance

The supported activation mode is push-to-talk. After selecting a microphone and
speaker in a local configuration, run one bounded acceptance turn against a
read-only thesis workspace:

```powershell
17_VOICE_INTERFACE\.venv\Scripts\python.exe -B 17_VOICE_INTERFACE\launch.py ptt-acceptance --config 17_VOICE_INTERFACE\voice_config.local.json --worker-python 17_VOICE_INTERFACE\.venv\Scripts\python.exe --thesis-root D:\path\to\thesis
```

The command checks selected devices, captures one PTT request, runs only the
read-only inspection route, plays its response, then stops the worker. Its JSON
record stores device metadata, step outcomes, and timing only; it never stores
microphone PCM or the transcript. A non-zero exit code means that this device
setup is not accepted. `--wake` is rejected for this command.

## Models and licensing

The selected local recognizer is faster-whisper base (MIT). The selected Piper
engine is GPL-3.0, and the selected `en_GB-alan-medium` voice's model card points
to its own dataset terms. The openWakeWord engine code is Apache-2.0; its bundled
pretrained model terms are CC BY-NC-SA 4.0. Inspect `model_manifest.json` and
the bundled Piper `MODEL_CARD` before redistribution. This installation is for
the user's local personal assistant and is not packaged as a redistributable
binary.

The Stone 26.5 delivery rule is first-run verified download or user-supplied
assets, with no bundled model binaries. See
[`MODEL_DISTRIBUTION_POLICY.md`](MODEL_DISTRIBUTION_POLICY.md).

Run `provision_models.py --download` only for explicit setup or repair. Normal
operation is offline and does not download models.

## Validation

Run all suites explicitly, without changing the frozen root pytest configuration:

```powershell
D:\Masters\Jarvis_Thesis_OS\.venv\Scripts\python.exe -B 17_VOICE_INTERFACE\run_tests.py
```

See `STONE_26_IMPLEMENTATION_REPORT.md` and `STONE_26_VALIDATION_AUDIT.md` at
the repository root for current results and known limitations.
