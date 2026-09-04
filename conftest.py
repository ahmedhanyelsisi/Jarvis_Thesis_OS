"""Repository-wide pytest path setup for the numeric architecture folders."""

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent

for folder in ("01_CORE_KERNEL", "02_AI_AGENTS"):
    path = str(PROJECT_ROOT / folder)
    if path not in sys.path:
        sys.path.insert(0, path)
