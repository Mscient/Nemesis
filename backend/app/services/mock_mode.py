"""
Mock mode helpers — B2.
When MOCK_MODE=true, routers load and return JSON from backend/mocks/*.json.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

_MOCKS_DIR = Path(__file__).resolve().parent.parent.parent / "mocks"


def load_mock(name: str) -> Any:
    """Load a mock JSON file by name (without .json extension)."""
    path = _MOCKS_DIR / f"{name}.json"
    if path.exists():
        return json.loads(path.read_text())
    return {}
