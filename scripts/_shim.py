"""Run a relocated script for backwards-compatible `scripts/` entry points."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


def run(relative_target: str) -> None:
    target = Path(__file__).resolve().parent.parent / relative_target
    if not target.is_file():
        raise SystemExit(f"Missing shim target: {target}")
    sys.argv[0] = str(target)
    runpy.run_path(str(target), run_name="__main__")