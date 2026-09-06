"""Make the standalone HUD module importable from the repository test runner."""
from __future__ import annotations

import sys
from pathlib import Path


HUD_ROOT = Path(__file__).resolve().parents[1]
if str(HUD_ROOT) not in sys.path:
    sys.path.insert(0, str(HUD_ROOT))
