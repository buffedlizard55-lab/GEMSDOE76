"""The shipped (negative) artifact must stay format-valid and hash-stable."""
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
ART = ROOT / "evidence/lane-g76/gems76-piedmont-dipole-exp2-27569dots-DO-NOT-SUBMIT.tif"


@pytest.mark.skipif(not ART.exists(), reason="artifact not built")
def test_artifact_valid_and_pinned():
    from gems57 import validate
    from gems57.grid import load_grid
    grid = load_grid(ROOT / "data/bridge")
    v = validate.validate(ART, footprint=grid.footprint, catalogue=grid.catalogue)
    assert v["all_checks_passed"], v["checks"]
    card = json.loads((ROOT / "evidence/run_card.json").read_text())
    assert hashlib.sha256(ART.read_bytes()).hexdigest() == card["raster_sha256"]
    assert card["verdict"] == "negative"
    assert "DO-NOT-SUBMIT" in ART.name
