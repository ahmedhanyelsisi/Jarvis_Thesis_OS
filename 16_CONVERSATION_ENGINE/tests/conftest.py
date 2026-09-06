import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for folder in (ROOT, ROOT / "16_CONVERSATION_ENGINE", ROOT / "17_VOICE_INTERFACE"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))
