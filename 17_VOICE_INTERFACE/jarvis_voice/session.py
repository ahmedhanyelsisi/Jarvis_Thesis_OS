"""Session and playback state with explicit activation and cancellation epochs."""
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass
from conversation_core.service_models import ChatReply
from .models import Recognition, Quality, SessionState, assess_quality


@dataclass(frozen=True)
class TurnTicket:
    turn_id: str
    auth_session: str
    expires_at: float
    mode: str


class VoiceSession:
    def __init__(self, chat, worker=None, *, language="en", clock=time.monotonic, on_event=None):
        self.chat = chat
        self.worker = worker
        self.language = language
        self.clock = clock
        self.on_event = on_event or (lambda event: None)
        self.state = SessionState.MUTED
        self.playback = "stopped"
        self.enabled = False
        self.__ticket = None
        self.__worker_id = None
        self.__lock = threading.RLock()
        self.__sequence = 0
        self.events = deque(maxlen=200)
        if worker:
            worker.event_callback = self.worker_event

    def emit(self, kind, **data):
        with self.__lock:
            self.__sequence += 1
            event = {"version": 1, "sequence": self.__sequence, "kind": kind, **data}
            self.events.append(event)
        self.on_event(dict(event))

    def _state(self, state):
        self.state = state
        self.emit("state", state=state.value, playback=self.playback)

    def enable(self):
        with self.__lock:
            if self.state == SessionState.STOPPED:
                raise RuntimeError("Closed session; start a new session")
            self.enabled = True
            self._state(SessionState.READY)

    def begin_turn(self, mode="ptt"):
        with self.__lock:
            if not self.enabled or self.state == SessionState.STOPPED:
                raise PermissionError("Enable listening before opening the microphone")
            if mode not in ("ptt", "wake") or self.__ticket is not None or self.playback == "playing":
                raise RuntimeError("Capture unavailable while busy or speaking")
            self.__ticket = TurnTicket(uuid.uuid4().hex, self.chat.auth_manager.session_id,
                                       self.clock() + 180, mode)
            self._state(SessionState.LISTENING if mode == "ptt" else SessionState.READY)
            return self.__ticket

    def worker_event(self, identifier, data):
        with self.__lock:
            if identifier != self.__worker_id:
                return
            state = data["state"]
            if state == "speaking":
                self.playback = "playing"
                self.emit("playback", state="playing")
            elif self.enabled and self.__ticket is not None:
                self._state(SessionState(state))

    def _started(self, identifier):
        with self.__lock:
            self.__worker_id = identifier

    def listen(self, mode="ptt", *, timeout=180):
        if self.worker is None:
            raise RuntimeError("No audio worker configured")
        ticket = self.begin_turn(mode)
        try:
            wire = self.worker.request("listen", {"mode": mode}, timeout=timeout, on_started=self._started)
            return self.accept(Recognition.from_wire(wire), ticket)
        except InterruptedError:
            return ChatReply("cancelled", "Listening cancelled.")
        except Exception as exc:
            self.fail(str(exc))
            return ChatReply("error", f"Voice unavailable: {exc}")
        finally:
            with self.__lock:
                if self.__ticket is ticket:
                    self.__ticket = None
                self.__worker_id = None

    def accept(self, recognition, ticket):
        with self.__lock:
            if (ticket is not self.__ticket or not self.enabled or self.clock() >= ticket.expires_at
                    or ticket.auth_session != self.chat.auth_manager.session_id):
                return ChatReply("rejected", "Stale or replayed transcript discarded.")
            self.__ticket = None  # a turn is consumable exactly once
            quality = assess_quality(recognition, self.language)
            if quality != Quality.HIGH:
                self._state(SessionState.CLARIFYING)
                self.emit("recognition", quality=quality.value, text=recognition.text)
                return ChatReply("clarification", "I could not reliably understand that. Repeat it or use text.")
            self.emit("transcript", text=recognition.text, final=True, turn_id=ticket.turn_id)
            self._state(SessionState.EXECUTING)
        reply = self.chat.handle_voice(recognition.text, expected_session=ticket.auth_session)
        with self.__lock:
            if ticket.auth_session != self.chat.auth_manager.session_id:
                return ChatReply("cancelled", "Request cancelled; late result discarded.")
            self._show_reply(reply)
        return reply

    def _show_reply(self, reply):
        state = {"waiting_for_approval": SessionState.WAITING_FOR_APPROVAL,
                 "clarification": SessionState.CLARIFYING, "error": SessionState.ERROR}.get(reply.status, SessionState.READY)
        self._state(state if self.enabled else SessionState.MUTED)
        self.emit("response", status=reply.status, text=reply.text, proposal_id=reply.proposal_id)

    def text(self, text):
        # Local typing interrupts capture/playback to keep requests unambiguous.
        if self.state == SessionState.EXECUTING:
            self.chat.cancel(reset_session=True)
        self.interrupt()
        reply = self.chat.handle_text(text)
        self._show_reply(reply)
        return reply

    def speak(self, reply, *, timeout=60):
        if self.worker is None:
            return False
        with self.__lock:
            if self.__ticket is not None or self.state == SessionState.STOPPED:
                return False
            session_id = self.chat.auth_manager.session_id
            self.playback = "playing"
        try:
            self.worker.request("speak", {"text": reply.text[:1000]}, timeout=timeout, on_started=self._started)
            with self.__lock:
                self.playback = "spoken" if session_id == self.chat.auth_manager.session_id else "stopped"
            return self.playback == "spoken"
        except InterruptedError:
            self.playback = "stopped"
            return False
        except Exception as exc:
            self.playback = "error"
            self.emit("error", text=f"Speech output unavailable: {exc}")
            if not self.worker.alive:
                self.fail("Audio worker lost")
            return False
        finally:
            with self.__lock:
                self.__worker_id = None
            self.emit("playback", state=self.playback)

    def interrupt(self):
        """Stop audio only; retain a local pending approval for a subsequent answer."""
        with self.__lock:
            self.__ticket = None
            self.__worker_id = None
            self.playback = "stopped"
        if self.worker and not self.worker.stop():
            self.fail("Audio worker did not stop; terminated")

    def mute(self):
        self.chat.cancel(reset_session=True)
        with self.__lock:
            self.enabled = False
            self.__ticket = None
        self.interrupt()
        self._state(SessionState.MUTED)

    def cancel(self):
        self.chat.cancel(reset_session=True)
        self.interrupt()
        self._state(SessionState.READY if self.enabled else SessionState.MUTED)

    def fail(self, message):
        self.chat.cancel(reset_session=True)
        with self.__lock:
            self.enabled = False
            self.__ticket = None
            self.__worker_id = None
            self.playback = "stopped"
        self._state(SessionState.ERROR)
        self.emit("error", text=message)

    def close(self):
        self.mute()
        if self.worker:
            self.worker.close()
        self.events.clear()
        self._state(SessionState.STOPPED)
