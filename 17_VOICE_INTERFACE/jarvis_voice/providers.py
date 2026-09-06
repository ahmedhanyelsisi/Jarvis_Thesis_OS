"""Lazy local speech providers. Missing assets never trigger network downloads."""
import importlib.util
import math
import re
import time
from dataclasses import asdict
from .assets import ModelAssets
from .audio import EnergySegmenter, SoundDeviceAudio
from .models import Recognition


class FasterWhisperRecognizer:
    def __init__(self, config, assets):
        from faster_whisper import WhisperModel
        path = assets.resolve(config.whisper_model)
        if not path.is_dir():
            raise ValueError("Whisper requires a verified local model directory")
        self.language = config.language
        self.model = WhisperModel(str(path), device="cpu", compute_type="int8",
                                  cpu_threads=config.cpu_threads, local_files_only=True)

    def transcribe(self, pcm, cancel):
        segments, info = self.model.transcribe(pcm, language=self.language, beam_size=3,
                            condition_on_previous_text=False, vad_filter=True, temperature=0)
        text, logs, silence, ratios = [], [], [], []
        for index, segment in enumerate(segments):
            if cancel.is_set():
                raise InterruptedError("Transcription cancelled")
            if index >= 256:
                raise ValueError("Transcription segment limit exceeded")
            text.append(segment.text)
            if sum(map(len, text)) > 4096:
                raise ValueError("Transcript exceeds limit")
            logs.append(segment.avg_logprob)
            silence.append(segment.no_speech_prob)
            ratios.append(segment.compression_ratio)
        if cancel.is_set():
            raise InterruptedError("Transcription cancelled")
        return Recognition(" ".join(text).strip(), info.language,
                           min(logs) if logs else None, max(silence) if silence else None,
                           max(ratios) if ratios else None)


class OpenWakeWordDetector:
    def __init__(self, config, assets):
        from openwakeword.model import Model
        self.threshold = config.wake_threshold
        self.model = Model(wakeword_models=[str(assets.resolve(config.wake_model))],
                           inference_framework="onnx", vad_threshold=0,
                           melspec_model_path=str(assets.resolve(config.melspectrogram_model)),
                           embedding_model_path=str(assets.resolve(config.embedding_model)))

    def detected(self, frame):
        import numpy as np
        predictions = self.model.predict(np.clip(frame * 32768, -32768, 32767).astype(np.int16))
        return any(math.isfinite(float(score)) and self.threshold <= float(score) <= 1 for score in predictions.values())

    def reset(self):
        self.model.reset()


class PiperSynthesizer:
    def __init__(self, config, assets):
        from piper import PiperVoice, SynthesisConfig
        path = assets.resolve(config.piper_model)
        files = assets.document["models"][config.piper_model]["files"]
        if path.name + ".json" not in files:
            raise ValueError("Piper voice configuration must also be checksum-verified")
        self.voice = PiperVoice.load(str(path), use_cuda=False)
        self.settings = SynthesisConfig(length_scale=1 / config.speech_rate)

    def chunks(self, text, cancel):
        for chunk in self.voice.synthesize(text, syn_config=self.settings):
            if cancel.is_set():
                raise InterruptedError("Synthesis cancelled")
            yield chunk.sample_rate, chunk.sample_channels, chunk.sample_width, chunk.audio_int16_bytes


class LocalVoiceRuntime:
    def __init__(self, config):
        self.config = config
        self.audio = SoundDeviceAudio(config)
        self.recognizer = self.detector = self.synthesizer = None

    def status(self):
        installed = {name: importlib.util.find_spec(name) is not None
                     for name in ("faster_whisper", "piper", "openwakeword", "sounddevice", "numpy", "scipy")}
        verified, failures = [], {}
        try:
            assets = ModelAssets(self.config.model_manifest)
            for name in (self.config.whisper_model, self.config.piper_model, self.config.wake_model,
                         self.config.melspectrogram_model, self.config.embedding_model):
                try:
                    assets.resolve(name)
                    verified.append(name)
                except (OSError, ValueError, KeyError, TypeError) as exc:
                    failures[name] = str(exc)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            failures["manifest"] = str(exc)
        return {"installed": installed, "verified_models": verified, "errors": failures,
                "hardware_validated": False, "ready": all(installed.values()) and not failures,
                "microphone_open": False}

    def devices(self):
        return self.audio.devices()

    @staticmethod
    def cue():
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_OK)
        except (ImportError, RuntimeError):
            pass

    def listen(self, mode, cancel, event):
        assets = ModelAssets(self.config.model_manifest)
        if self.recognizer is None:
            self.recognizer = FasterWhisperRecognizer(self.config, assets)
        if mode == "wake":
            if self.detector is None:
                self.detector = OpenWakeWordDetector(self.config, assets)
            self.detector.reset()
        segmenter = EnergySegmenter(self.config)
        activated = mode == "ptt"
        started = time.monotonic()
        event("listening" if activated else "ready")
        if activated:
            self.cue()
        # The generator's context manager closes capture before inference/playback.
        capture = self.audio.frames(cancel)
        pcm = None
        try:
            for frame in capture:
                if cancel.is_set():
                    raise InterruptedError("Capture cancelled")
                if not activated:
                    if time.monotonic() - started >= self.config.wake_timeout:
                        raise TimeoutError("No wake phrase detected")
                    if self.detector.detected(frame):
                        activated = True
                        segmenter.reset()
                        event("listening")
                        self.cue()
                    continue
                pcm = segmenter.feed(frame)
                if pcm is not None:
                    break
        finally:
            capture.close()
        if pcm is None or cancel.is_set():
            raise InterruptedError("Capture cancelled")
        event("transcribing")
        try:
            result = self.recognizer.transcribe(pcm, cancel)
            text = re.sub(r"^\s*hey\s+jarvis\b[\s,.!?]*", "", result.text, flags=re.I)
            return dict(asdict(result), text=text)
        finally:
            pcm.fill(0)

    def speak(self, text, cancel, event):
        event("speaking")
        if self.config.tts_provider == "windows":
            from voice.text_to_speech import LocalSpeechSynthesizer
            if self.synthesizer is None:
                self.synthesizer = LocalSpeechSynthesizer()
            self.synthesizer.speak(text)
            if cancel.is_set():
                raise InterruptedError("Playback stopped")
            return {"playback": "spoken", "provider": "windows", "degraded": True}
        if self.synthesizer is None:
            self.synthesizer = PiperSynthesizer(self.config, ModelAssets(self.config.model_manifest))
        self.audio.play(self.synthesizer.chunks(text, cancel), cancel)
        return {"playback": "spoken", "provider": "piper"}

    def stop(self):
        self.audio.stop()
        if self.config.tts_provider == "windows" and self.synthesizer:
            self.synthesizer.stop()
