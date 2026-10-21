#!/usr/bin/env python3
"""Compatibility entrypoint: no invented training-ready state or rebuilt cache."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('preflight.py')),run_name='__main__')
