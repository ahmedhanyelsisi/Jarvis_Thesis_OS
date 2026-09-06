"""Optional launcher; leaves the frozen runtime and its import configuration alone."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
for directory in (HERE.parent, HERE.parent / "16_CONVERSATION_ENGINE", HERE):
    sys.path.insert(0, str(directory))

from jarvis_voice.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
