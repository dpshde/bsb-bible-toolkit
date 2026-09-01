#!/usr/bin/env python3
"""Compatibility shim for the travel John print sample."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from bsb_pdf_toolkit.generate_travel_pdf import main

if __name__ == "__main__":
    sys.exit(main())
