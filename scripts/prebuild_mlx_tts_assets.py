#!/usr/bin/env python3
"""Compatibility shim — use audio/local/prebuild_assets.py instead."""

from _shim import run

if __name__ == "__main__":
    run("audio/local/prebuild_assets.py")