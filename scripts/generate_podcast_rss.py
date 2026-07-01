#!/usr/bin/env python3
"""Compatibility shim — use audio/production/generate_rss.py instead."""

from _shim import run

if __name__ == "__main__":
    run("audio/production/generate_rss.py")