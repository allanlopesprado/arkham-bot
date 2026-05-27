"""Compatibility wrapper for legacy handler-local local_storage imports."""

import json
from pathlib import Path
from typing import Any


def load_json_file(path: str | Path, default: Any = None) -> Any:
    """Load JSON from disk, returning default when the file is absent or invalid."""
    try:
        target = Path(path)
        if not target.exists():
            return default
        with target.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return default
