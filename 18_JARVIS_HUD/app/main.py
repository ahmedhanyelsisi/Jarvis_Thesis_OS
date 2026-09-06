"""Launch the Stone 27 functional HUD and optional frozen runtime composition."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QUrl, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from bridge import RuntimeBridge

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None):
    parser = argparse.ArgumentParser(description="JARVIS Stone 27 functional HUD")
    parser.add_argument("--screenshot", type=Path, help="Render one local PNG preview and exit")
    parser.add_argument("--prototype", action="store_true",
                        help="Expose the isolated Gate 3 development controls.")
    parser.add_argument("--no-runtime", action="store_true",
                        help="Launch without booting the frozen runtime composition.")
    args = parser.parse_args(argv)
    application = QGuiApplication(sys.argv[:1])
    application.setApplicationName("JARVIS — Functional HUD")
    engine = QQmlApplicationEngine()
    bridge = RuntimeBridge(
        prototype_mode=args.prototype,
        live_runtime=not args.prototype and not args.no_runtime,
    )
    engine.rootContext().setContextProperty("runtimeBridge", bridge)
    engine.warnings.connect(lambda warnings: [print(warning.toString(), file=sys.stderr) for warning in warnings])
    engine.load(QUrl.fromLocalFile(str(ROOT / "qml" / "Main.qml")))
    if not engine.rootObjects():
        return 2
    window = engine.rootObjects()[0]
    if args.screenshot:
        destination = args.screenshot.resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)

        def capture():
            image = application.primaryScreen().grabWindow(window.winId())
            if image.isNull() or not image.save(str(destination)):
                application.exit(3)
            else:
                application.quit()

        QTimer.singleShot(8000 if not args.no_runtime and not args.prototype else 400, capture)
    result = application.exec()
    bridge.close()
    return result


if __name__ == "__main__":
    raise SystemExit(main())
