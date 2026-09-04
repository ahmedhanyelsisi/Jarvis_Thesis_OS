# Stone 7: Voice Interaction Architecture

## Purpose

Stone 7 adds local voice input and output around Jarvis. It does not replace or
reimplement the kernel, Stone 5 reasoning, Stone 6 memory, or any specialist agent.
Text remains the internal contract, and existing callers can continue using
`Jarvis.process_request()` and `Jarvis.process_workflow()` unchanged.

## Architecture

```text
User voice
   |
   v
+---------------- VoiceManager ----------------+
| SpeechRecognizer -> Transcript                |
| Wake-word gate -> VoiceCommand                |
|                 |                             |
+-----------------|-----------------------------+
                  v
       Jarvis.process_request()  OR
       Jarvis.process_workflow()
                  |
                  v
     Stone 5 reasoning -> Stone 6 memory
                  -> specialist agents
                  |
                  v
             kernel response
                  |
                  v
+---------------- VoiceManager ----------------+
| response-to-text adapter -> SpeechSynthesizer |
+-----------------|-----------------------------+
                  v
              User hears Jarvis
```

## Components

| Component | Responsibility |
| --- | --- |
| `voice_models.py` | Typed `Transcript`, `VoiceCommand`, `VoiceResponse`, and `AudioStatus` transfer models |
| `speech_to_text.py` | Provider-neutral `SpeechRecognizer`, a deterministic mock, and local Windows recognition |
| `text_to_speech.py` | Provider-neutral `SpeechSynthesizer`, a recording mock, and local Windows speech synthesis |
| `voice_manager.py` | Wake-word gating, kernel dispatch, response rendering, synthesis, and listener lifecycle |
| `config.py` | Validated voice runtime options |

The local providers use Windows `System.Speech` through Windows PowerShell. This
keeps the feature local and introduces no Python package or paid API dependency. The
recognizer requires a Windows speech-recognition language matching `voice.language`.

## Data flow

1. `VoiceManager.start()` starts a daemon listener, or
   `process_voice_command()` processes a supplied/captured utterance directly.
2. `SpeechRecognizer.listen()` captures one input payload and `transcribe()` returns
   a typed `Transcript`.
3. The manager performs a case-insensitive, start-of-utterance wake-word check.
   `Jarvis ...` is accepted; speech without that prefix is returned as `ignored` and
   never reaches the kernel.
4. The wake word and punctuation are removed. The remaining text is put in a
   `VoiceCommand` with its timestamp and confidence.
5. Normal commands call the unchanged `process_request()` API. A caller can request
   the existing workflow path with `workflow=True`; no reasoning is implemented in
   the voice package.
6. The kernel's structured result is retained on `VoiceResponse.kernel_result` and
   rendered as speakable text.
7. `SpeechSynthesizer.speak()` plays that text and its result becomes
   `VoiceResponse.audio_status`.

## Integration and configuration

`Jarvis` constructs a `VoiceManager` only when the supplied runtime configuration
contains an enabled voice section. If the section is absent, voice stays disabled so
older programmatic configuration dictionaries retain their prior behavior.

```yaml
voice:
  enabled: true
  wake_word: Jarvis
  language: en
  provider: local
  speech_rate: normal
```

- `enabled` controls manager construction and listener availability.
- `wake_word` controls the local command gate.
- `language` selects an installed local recognition language.
- `provider` is `local` for Windows execution or `mock` for deterministic tests.
- `speech_rate` maps `slow`, `normal`, and `fast` to local synthesis rates.

`Jarvis.start_voice()` and `Jarvis.process_voice_command()` are convenience methods.
`Jarvis.close()` shuts down voice playback/listening before closing existing memory
and knowledge resources.

## Future upgrade path

Future providers should implement the existing `SpeechRecognizer` or
`SpeechSynthesizer` interfaces and be selected in the factories, leaving
`VoiceManager` and Jarvis unchanged. Intended adapters include:

- an on-device Whisper recognizer for higher-quality multilingual STT;
- OpenAI or ElevenLabs synthesis as explicitly configured optional providers; and
- streaming capture, endpointing, and interruption support behind the same methods.

Remote adapters must remain opt-in, keep credentials outside source control, and
report provider failures through the typed response/error boundary. Whisper is an
STT technology; its ecosystem can also contribute voice-activity detection and audio
pre/post-processing while TTS remains behind `SpeechSynthesizer`.

## Operational limits

- Stone 7 wake-word detection is deliberately lexical, not an always-on acoustic
  wake-word model. Recognition occurs first, then the transcript is gated.
- The initial local provider is Windows-specific and depends on installed system
  speech components and microphone permission.
- The listener is a single daemon thread and processes one command at a time.
- Mock providers exercise the full controller and kernel boundary without hardware.
