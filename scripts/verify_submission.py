#!/usr/bin/env python3
"""Compatibility entrypoint; requires a candidate path and never grants slot approval."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('validate_candidate.py')),run_name='__main__')
