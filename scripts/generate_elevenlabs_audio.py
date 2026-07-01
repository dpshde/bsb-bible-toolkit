#!/usr/bin/env python3
"""Compatibility shim — use audio/production/generate.py instead."""

from _shim import run

if __name__ == "__main__":
    run("audio/production/generate.py")