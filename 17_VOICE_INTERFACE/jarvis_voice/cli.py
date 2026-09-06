"""Text controls remain available when speech dependencies/models are unavailable."""
import argparse
import json
import sys
import threading
from dataclasses import asdict
from pathlib import Path
from conversation_core.chat_manager import ChatManager
from .backend import WorkspaceBackend
from .client import WorkerClient
from .config import VoiceConfig
from .session import VoiceSession


def build_parser():
    parser = argparse.ArgumentParser(description="JARVIS Stone 26 local voice interface")
    parser.add_argument("command", choices=("doctor", "devices", "chat", "listen", "inspect", "speak", "ptt-acceptance"))
    parser.add_argument("--config", type=Path, default=Path(__file__).resolve().parents[1] / "voice_config.example.json")
    parser.add_argument("--worker-python", default=sys.executable)
    parser.add_argument("--thesis-root", type=Path)
    parser.add_argument("--audit-path", type=Path, default=Path(__file__).resolve().parents[1] / ".state" / "audit.jsonl")
    parser.add_argument("--wake", action="store_true", help="Explicitly enable wake mode for this session")
    parser.add_argument("--text", default="Jarvis voice output is ready.")
    parser.add_argument("--ptt-timeout", type=int, default=60, help="PTT acceptance limit in seconds (1-60)")
    parser.add_argument("--acceptance-path", type=Path,
                        default=Path(__file__).resolve().parents[1] / ".state" / "stone_26_5_ptt_acceptance.json")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    worker = session = None
    try:
        config = VoiceConfig.load(args.config)
        if args.command in ("doctor", "devices", "listen", "speak", "chat", "ptt-acceptance"):
            worker = WorkerClient(args.worker_python, args.config)
        if args.command in ("doctor", "devices"):
            result = worker.request("status" if args.command == "doctor" else "devices")
            print(json.dumps(result, indent=2))
            return 0 if args.command == "devices" or result.get("ready") else 2
        if args.command == "ptt-acceptance":
            if args.wake:
                raise ValueError("PTT acceptance does not support wake mode")
            if args.thesis_root is None:
                raise ValueError("PTT acceptance requires --thesis-root")
            from .acceptance import run_ptt_acceptance
            result = run_ptt_acceptance(worker=worker, config=config,
                                        thesis_root=args.thesis_root, result_path=args.acceptance_path,
                                        timeout=args.ptt_timeout,
                                        platform_root=Path(__file__).resolve().parents[2])
            print(json.dumps(result.wire(), indent=2))
            return 0 if result.ok else 2
        backend = WorkspaceBackend(args.thesis_root, platform_root=Path(__file__).resolve().parents[2]) if args.thesis_root else None
        chat = ChatManager(backend=backend, ledger_path=args.audit_path)
        session = VoiceSession(chat, worker, on_event=lambda event: print(json.dumps(event), flush=True))
        if args.command == "inspect":
            reply = session.text("check thesis citations")
            print(json.dumps(asdict(reply), indent=2))
            return 0 if reply.status == "completed" else 2
        if args.command == "speak":
            from conversation_core.service_models import ChatReply
            return 0 if session.speak(ChatReply("completed", args.text)) else 2
        if args.command == "listen":
            if args.wake and not config.wake_experimental:
                raise ValueError("Wake mode is experimental and disabled by this configuration")
            session.enable()
            reply = session.listen("wake" if args.wake else "ptt")
            print(json.dumps(asdict(reply), indent=2))
            if reply.status != "error":
                session.speak(reply)
            return 0 if reply.status == "completed" else 2

        print("JARVIS voice controls: /listen, /wake, /stop, /cancel, /mute, /enable, /quit.")
        print("Microphone starts muted. Type normal requests or an exact displayed approval command.")
        active_thread = None

        def voice_turn(mode):
            reply = session.listen(mode)
            if reply.status not in ("cancelled", "error"):
                session.speak(reply)

        while True:
            try:
                text = input("You: ").strip()
            except EOFError:
                break
            if text == "/quit":
                break
            if text in ("/listen", "/wake"):
                if text == "/wake" and not config.wake_experimental:
                    print("Wake mode is experimental and disabled. Use /listen for push-to-talk.")
                    continue
                if active_thread and active_thread.is_alive():
                    print("Finish or /cancel the active voice turn first.")
                    continue
                session.enable()
                active_thread = threading.Thread(target=voice_turn, args=("wake" if text == "/wake" else "ptt",), daemon=True)
                active_thread.start()
            elif text == "/stop":
                session.interrupt()
            elif text == "/cancel":
                session.cancel()
            elif text == "/mute":
                session.mute()
            elif text == "/enable":
                session.enable()
            elif text:
                reply = session.text(text)
                print(reply.text)
        session.close()
        if active_thread:
            active_thread.join(timeout=2)
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"JARVIS unavailable: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
    finally:
        if session:
            session.close()
        elif worker:
            worker.close()
