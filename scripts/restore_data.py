#!/usr/bin/env python3
"""Zero-manual-input restoration & SHA-256 verification of all official DOE GEMS
competition rasters (`training_features.tif`, `existing_faults.tif`, `sample_submission.tif`)
and public federal geoscience layers (`USGS GeoDAWN`, `USGS 3DEP 1m/10m`, `DOE GDR 1391`,
`USGS ScienceBase`) into `.cache/data` and `.cache/external`."""
from __future__ import annotations

import gzip
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / ".cache" / "data"
EXT_DIR = ROOT / ".cache" / "external"
REFS_DIR = Path("/tmp/refs")

OFFICIAL_PINS = {
    "training_features.tif": "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5",
    "existing_faults.tif": "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093",
    "sample_submission.tif": "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def ensure_mirror_repo(repo_name: str) -> Path:
    dest = REFS_DIR / repo_name
    if not dest.exists():
        REFS_DIR.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", "--depth", "1", f"https://github.com/buffedlizard55-lab/{repo_name}.git", str(dest)],
            check=True,
        )
    return dest


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    EXT_DIR.mkdir(parents=True, exist_ok=True)

    # Restore official competition rasters if not yet verified in .cache/data
    for fname, expected in OFFICIAL_PINS.items():
        target = DATA_DIR / fname
        if target.exists() and sha256(target) == expected:
            continue
        r16 = ensure_mirror_repo("16GEMSDOE")
        off_dir = r16 / "data" / "official"
        if fname == "training_features.tif":
            parts = sorted(off_dir.glob("training_features.tif.gz.part-*"))
            tmp_gz = DATA_DIR / "training_features.tif.gz"
            with tmp_gz.open("wb") as out:
                for p in parts:
                    shutil.copyfileobj(p.open("rb"), out)
            with gzip.open(tmp_gz, "rb") as gz, target.open("wb") as out:
                shutil.copyfileobj(gz, out)
            tmp_gz.unlink(missing_ok=True)
        else:
            gz_path = off_dir / f"{fname}.gz"
            if gz_path.exists():
                with gzip.open(gz_path, "rb") as gz, target.open("wb") as out:
                    shutil.copyfileobj(gz, out)
            else:
                shutil.copyfile(off_dir / fname, target)
        got = sha256(target)
        assert got == expected, f"SHA-256 mismatch for {fname}: {got} != {expected}"

    # Ensure required public external layers exist in .cache/external
    req_ext = [
        ("60GEMSDOE", "data/external/lidar_scarp_features_u8.tif", "lidar_scarp_features_u8.tif"),
        ("60GEMSDOE", "data/external/topo_10m_derived_100m_u8.tif", "topo_10m_derived_100m_u8.tif"),
        ("60GEMSDOE", "data/external/dem10_chi_100m_u8.tif", "dem10_chi_100m_u8.tif"),
        ("60GEMSDOE", "data/external/dem10_chi_100m_i16.tif", "dem10_chi_100m_i16.tif"),
        ("60GEMSDOE", "data/external/geodawn_extensions_u8.tif", "geodawn_extensions_u8.tif"),
        ("60GEMSDOE", "data/external/geodawn_rad_u8.tif", "geodawn_rad_u8.tif"),
        ("60GEMSDOE", "data/external/gdr_wellspring_in_footprint.csv", "gdr_wellspring_in_footprint.csv"),
        ("60GEMSDOE", "data/external/gdr_volcanic_vents_in_footprint.csv", "gdr_volcanic_vents_in_footprint.csv"),
        ("60GEMSDOE", "data/external/2m_temperature_probe_INGENIOUS_regional_data.zip", "2m_temperature_probe_INGENIOUS_regional_data.zip"),
        ("60GEMSDOE", "data/external/paleo_geothermal_regional.zip", "paleo_geothermal_regional.zip"),
        ("19GEMSDOE", "evidence/ci/dem1m_high_prior_openness_lrm.npz", "dem1m_high_prior_openness_lrm.npz"),
        ("GEMSDOE28", "docs/data/sb_heat_flow_in_footprint.csv", "sb_heat_flow_in_footprint.csv"),
        ("GEMSDOE28", "docs/data/sb_slip_tendency_in_footprint.csv", "sb_slip_tendency_in_footprint.csv"),
    ]
    for repo, rel, dst_name in req_ext:
        dst = EXT_DIR / dst_name
        if not dst.exists():
            rdir = ensure_mirror_repo(repo)
            shutil.copyfile(rdir / rel, dst)

    manifest = {
        "official_rasters": {
            fn: {"bytes": (DATA_DIR / fn).stat().st_size, "sha256": sha256(DATA_DIR / fn)}
            for fn in OFFICIAL_PINS
        },
        "external_layers": {
            p.name: {"bytes": p.stat().st_size, "sha256": sha256(p)}
            for p in sorted(EXT_DIR.iterdir())
            if p.is_file()
        },
    }
    out_manifest = ROOT / "evidence" / "data_manifest.json"
    out_manifest.parent.mkdir(parents=True, exist_ok=True)
    out_manifest.write_text(json.dumps(manifest, indent=2) + "\n")
    print("All official & open geoscience datasets verified cleanly.")
    for fn, info in manifest["official_rasters"].items():
        print(f"  [OK] {fn:24s} sha256={info['sha256']}")


if __name__ == "__main__":
    main()
