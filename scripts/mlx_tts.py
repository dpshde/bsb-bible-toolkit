#!/usr/bin/env python3
"""Compatibility shim — use audio/local/mlx_tts.py instead."""

from _shim import run

if __name__ == "__main__":
    run("audio/local/mlx_tts.py")