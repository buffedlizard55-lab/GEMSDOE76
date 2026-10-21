#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' 'BLOCKED: this environment cannot download authenticated competition data or private template caches.' >&2
printf '%s\n' 'Public pinned bridge inputs can be recovered with: .venv/bin/python scripts/recover_inputs.py' >&2
printf '%s\n' 'These bridge files are reference inputs, NOT competition predictions or a complete training dataset.' >&2
exit 2
