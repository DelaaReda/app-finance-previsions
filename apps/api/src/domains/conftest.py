from __future__ import annotations

import sys
from pathlib import Path


# Keep api/src importable when pytest is launched from the repository root.
SRC_ROOT = Path(__file__).resolve().parents[1]
src_root_str = str(SRC_ROOT)
if src_root_str not in sys.path:
    sys.path.insert(0, src_root_str)
