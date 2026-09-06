"""Bounded audio capture, simple energy segmentation, and cancellable playback."""
import math
import queue
import threading
import time
from collections import deque


class EnergySegmenter:
    """Engineering VAD gate, not a speaker identity or authorization signal."""
    def __init__(self, config):
        self.config = config
        self.reset()

    def reset(self):
        self.frames = []
        self.elapsed = 0.0
        self.silence = 0.0
        self.started = False
        self.preroll = deque(maxlen=5)

    def feed(self, frame):
        import numpy as np
        if len(frame) != 1280 or not np.isfinite(frame).all():
            raise ValueError("Invalid 80 ms audio frame")
        self.elapsed += .08
        energy = float(np.sqrt(np.mean(frame * frame)))
        voiced = energy >= self.config.vad_rms
        if not self.started:
            self.preroll.append(frame.copy())
            if voiced:
                self.started = True
                self.frames.extend(self.preroll)
                self.preroll.clear()
            elif self.elapsed >= self.config.activation_timeout:
                raise TimeoutError("No speech after activation")
        else:
            self.frames.append(frame.copy())
        self.silence = 0 if voiced else self.silence + .08
        if self.elapsed >= self.config.max_utterance_seconds:
            raise ValueError("Utterance exceeded limit; incomplete speech discarded")
        if self.started and self.silence >= self.config.silence_seconds:
            return np.concatenate(self.frames)
        return None


class SoundDeviceAudio:
    def __init__(self, config):
        self.config = config
        self.__output = None
        self.__lock = threading.Lock()

    @staticmethod
    def devices():
        import sounddevice as sd
        return [{"id": i, "name": item["name"], "inputs": item["max_input_channels"],
                 "outputs": item["max_output_channels"], "sample_rate": item["default_samplerate"]}
                for i, item in enumerate(sd.query_devices())]

    def frames(self, cancel):
        import numpy as np
        import sounddevice as sd
        rate = self.config.device_sample_rate
        blocksize = rate * 80 // 1000
        blocks = queue.Queue(maxsize=25)
        broken = threading.Event()

        def callback(data, frames, timestamp, status):
            if status or frames != blocksize:
                broken.set()
                return
            try:
                blocks.put_nowait((time.monotonic(), bytes(data)))
            except queue.Full:
                broken.set()

        sd.check_input_settings(device=self.config.input_device, channels=1, dtype="int16", samplerate=rate)
        with sd.RawInputStream(device=self.config.input_device, channels=1, dtype="int16",
                               samplerate=rate, blocksize=blocksize, callback=callback) as stream:
            while not cancel.is_set():
                if broken.is_set() or not stream.active:
                    raise RuntimeError("Audio overflow or device lost; utterance discarded")
                try:
                    captured, raw = blocks.get(timeout=.1)
                except queue.Empty:
                    continue
                if time.monotonic() - captured > .5:
                    raise RuntimeError("Stale audio buffer; utterance discarded")
                frame = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768
                if rate != 16000:
                    from scipy.signal import resample_poly
                    divisor = math.gcd(rate, 16000)
                    frame = resample_poly(frame, 16000 // divisor, rate // divisor).astype(np.float32)
                yield frame
        if cancel.is_set():
            raise InterruptedError("Capture cancelled")

    def play(self, chunks, cancel):
        import sounddevice as sd
        stream = None
        audio_format = None
        try:
            for rate, channels, width, data in chunks:
                if cancel.is_set():
                    raise InterruptedError("Playback stopped")
                if width != 2 or channels != 1 or not 8000 <= rate <= 96000 or len(data) % 2:
                    raise ValueError("Unsupported synthesized audio format")
                if stream is None:
                    audio_format = (rate, channels, width)
                    stream = sd.RawOutputStream(samplerate=rate, channels=channels, dtype="int16",
                                                device=self.config.output_device, latency="low")
                    with self.__lock:
                        self.__output = stream
                    stream.start()
                if audio_format != (rate, channels, width):
                    raise ValueError("Synthesis changed audio format")
                # 40 ms writes keep cooperative interruption responsive.
                size = int(rate * .04) * 2
                for offset in range(0, len(data), size):
                    if cancel.is_set():
                        raise InterruptedError("Playback stopped")
                    stream.write(data[offset:offset + size])
            if cancel.is_set():
                raise InterruptedError("Playback stopped")
        finally:
            with self.__lock:
                self.__output = None
            if stream is not None:
                if cancel.is_set():
                    stream.abort()
                else:
                    stream.stop()
                stream.close()

    def stop(self):
        with self.__lock:
            stream = self.__output
        if stream:
            try:
                stream.abort()
            except Exception:
                pass  # worker termination remains the bounded fallback
