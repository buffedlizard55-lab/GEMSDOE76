#!/usr/bin/env python3
"""Fetch registry rasters that carry a user-reported live score.

Sources: GEMSDOE70's inherited registry index (repo:path + sha256 per raster).
Every fetched file is hash-verified against that index.  Files land in
``.cache/registry/`` (git-ignored).  The score table below is transcribed from
the project prompt's per-site list and is labelled USER-REPORTED everywhere it
is used — no organizer receipt exists in any cloned repo for these numbers.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / ".cache" / "registry"
INDEX = Path("/home/user/siblings/GEMSDOE70/registry/inherited_registry.json")

# (distinctive substring of the file name, user-reported live DTI)
SCORED = [
    ("h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros", 0.2778),
    ("anderson-geothermal-pinn-38854", 0.2750),
    ("h27-4-solo-d28-20261004-8acb75e1", 0.2708),
    ("h36-1-rung30-blind-r1-20261003-b531dae0a36f", 0.2710),
    ("h38-1-hf-euler-r30-r1-20261003-56a9f473edc7", 0.2707),
    ("h32-1-prethin-tip-euler-d2-8-20261003-31e35eee884e", 0.2649),
    ("h33d-analog-tip-stepover-r30-20261004-cb490425926e", 0.2632),
    ("dotted-h19-5-d2-8-20261002-e56ea318af89", 0.2600),
    ("d28-poisson300m-offcat-44090", 0.2600),
    ("efd28-repro-20261003-1cc7dc534d51", 0.2600),
    ("wormrank-d28-20261003-59dcaf6dd11d", 0.2560),
    ("gems70-p5-dual-submod300-oof38k-20261020", 0.2478),
    ("h25-1-dotted-h19-5-d1-5-20261002-989f59505db1", 0.2477),
    ("topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1", 0.2449),
    ("gate_ortho_w0.25-40k-20261006T213721Z", 0.2376),
    ("cvarlw-thin-s3p17-54864-20261011T220606Z-c58f60c4", 0.2303),
    ("h59-cover-ds-belief-b2xh33d-20261008T184547Z-b79c4c61d8d8", 0.2296),
    ("h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf", 0.1922),
    ("h19-4-multiline-corroborated-openness-thermal-pop-20260930-691e4dfa", 0.1894),
    ("h20-1-sarnnpu-powerlaw-pi0363-tilt-wingcrack-20260930-be0e8f6b", 0.1890),
    ("h20-5-continuous-pu-proxy-unverified-20260930-824ce73a", 0.1859),
    ("h16-1-topo-geophys-baseline-ridges-20260930-df20f65e", 0.1855),
    ("h28-dotted-ridge-20260928T020256236880Z-6452ae1d00", 0.1839),
    ("r11f-scarp-radiometric-fusion-00e049b51218", 0.1589),
    ("gems-submission-20260925T001403Z-7f00890a", 0.1563),
    ("gemsdoe2-dual-family-union-20260925T160406Z-f68e590f", 0.1560),
    ("lidarscarp-ridge-top2pct-36c3a3f341c8", 0.1461),
    ("ovtr-ml-cover-tau3p0-20261012", 0.1426),
    ("h30-arrangement-matched-habitat-20261002-0d4e02e8", 0.1352),
    ("r7-nms3-dem10-scarp_0c9199f14e62", 0.1294),
    ("H25-ctx-ridge-20260927T232947704150Z-6452ae1d00", 0.1280),
    ("dilcond-oof-v1-20261003-47629f496133", 0.1223),
    ("pindrop-v4-nodes-20260925T152420Z-f347b70daa", 0.1193),
    ("pindrop-v4-ridge-20260925T152422Z-4e03fc9705", 0.1152),
    ("gems66-lidar03-cvretrain-reliefdecile-37654dots", 0.1152),
    ("h53-twostage-20261008T040951Z-9a0b32c871", 0.1047),
    ("h23-a-dti-optimal-emission-6pct-20261002-e2ec4b49", 0.1002),
    ("h45-eulerdepthreadcluster-20261006-f28e5cff6826", 0.0984),
    ("h18-3a-topo-geophys-x-complexity-prior-20260930-c502dfab", 0.0976),
    ("h20-dem10-scarp-thin-20260927T155223039488Z-ffc91a1686", 0.0921),
    ("r13-lattice-s5_v2", 0.0904),
    ("h97b-candidate", 0.0856),
    ("r12-scarp-rad-concordance-23e807e2de9f", 0.0843),
    ("pindrop-v4-discovery-20260925T152423Z-37f9d5b855", 0.0830),
    ("gems-tso1-20260929T005627Z-conj_alteration_mag", 0.0782),
    ("h34-scatter-q50-arr-matched-20261004T223317Z", 0.0778),
    ("h59-sharpened-scarp-scatter-90k-20261007T171954Z", 0.0764),
    ("D-step-3p0-07pct-tipProt-20261005-ecfbf59e2b48", 0.0763),
    ("h61o-vardepth-none-40000dots-20261011T160711Z-28d4fac611ea", 0.0751),
    ("h23-b-dti-optimal-emission-10pct-20261002-86176698", 0.0748),
    ("h46-twostageAB_20261006T160000Z_b0cfe956", 0.0715),
    ("h56-final-dotted-ridge-d2p8-20261009T190421Z", 0.0658),
    ("xscale-worm-persistence-20261006T000541Z", 0.0581),
    ("gems71-hydro-conduit-38800-20261020T120000Z", 0.0558),
    ("wormsurv-filter-20261003-921f10960d6e", 0.0532),
    ("sgmc-off-catalogue-44k-20261003-c8dcd780e3fd", 0.0512),
    ("h59j-coherence-consensus-dotted-20261011T043000Z", 0.0499),
    ("h16-continuation-20260927T065521077735Z-3431b83c7c", 0.0461),
    ("h35-06-aaa86efb25-20261004T225420098147Z", 0.0418),
    ("sup01-hgb21-sep40-n40000-20261006-bc2e4e9a8d6f", 0.0424),
    ("h60-lidarscarp-s2p0-20261007", 0.0430),
    ("sar-em-propensity-half-20261011T223500Z-5e4660cd", 0.0431),
    ("gems68-autoctx-s3-strands-35000dots-20261020T210000Z-849a0f04", 0.0437),
    ("xfit-c0-habitat-20261003-ca879db0089a", 0.0439),
    ("h64-lidar-scarp-cv-20261011T220000Z", 0.0383),
    ("h18-4-usgs-geologic-map-faults-gap-20260930-aef8f42c", 0.0360),
    ("h8-euler-lineament-depthcluster-20261006-785c4f5d5ce1-hard", 0.0397),
    ("xfit-h41-union-qfaults-20261003-9edb34b99e3a", 0.0356),
    ("h67a-orientip-lane-29447dots-20261012T021226Z", 0.0356),
    ("h73-chi-coherent-corridor-12000-20261011T195818Z", 0.0351),
    ("gems-submission-20260926T163915Z-237f0063", 0.0343),
    ("h40-e-disc-h40e-30k", 0.0339),
    ("H19-C_20260930T212401Z_c11e495e", 0.0297),
    ("tensor_full-n16000-sep3-20261009T211747Z", 0.0290),
    ("gems6_hgb88-topk03_33cec71ff0", 0.0286),
    ("h57r-joint-strata-38000-20261010T214547Z-00cf5b2066f1", 0.0254),
    ("h42-submission-primary", 0.0245),
    ("gems-structural-area06-v1", 0.0202),
    ("17GEMSDOE_F-ensemble-2pct_20260930T050626Z", 0.0187),
    ("ml-binary-ridge-20261012T000000Z", 0.0180),
    ("h8-tiprelay-ridgeconcord-pr2-n80000-20261009-49bec522", 0.0159),
    ("2314b599", 0.0107),
    ("h51-km-faultzone-20261006", 0.0106),
    ("h69-joint-relayramp-pullapart-38669-20261020T201504Z-f29b6df5", 0.0053),
    ("repo-c0-habitat-emission-20261003-a4d439b07426", 0.0041),
    ("GEMS_r5-geom-horse-ensemble_20260929T154852Z_ccbe1de0", 0.0020),
    ("h61a-basement-step-20000dots-20261011T012029Z-eb2ae4bb024b", 0.0009),
]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    index = json.loads(INDEX.read_text())
    rasters = index["rasters"] if "rasters" in index else index.get("entries", [])
    if not rasters:  # fall back: any list-like member
        for v in index.values():
            if isinstance(v, list) and v and isinstance(v[0], dict) and "sources" in v[0]:
                rasters = v
                break
    by_source = {}
    for r in rasters:
        for s in r.get("sources", []):
            by_source[s] = r
    DEST.mkdir(parents=True, exist_ok=True)
    ledger = []
    for needle, score in SCORED:
        hits = [(s, r) for s, r in by_source.items() if needle in s]
        if not hits:
            ledger.append({"needle": needle, "live_user_reported": score, "status": "NOT_IN_REGISTRY_INDEX"})
            print("MISS", needle)
            continue
        # prefer the first source (index order); fetch & verify
        src, rec = hits[0]
        repo, path = src.split(":", 1)
        dest = DEST / Path(path).name
        status = "cached"
        if not (dest.exists() and sha256(dest) == rec["sha256"]):
            tmp = dest.with_suffix(".tif.partial")
            with tmp.open("wb") as out:
                subprocess.run(["gh", "api",
                                f"repos/buffedlizard55-lab/{repo}/contents/{path}",
                                "-H", "Accept: application/vnd.github.raw"],
                               stdout=out, check=True)
            tmp.replace(dest)
            status = "fetched"
        got = sha256(dest)
        ok = got == rec["sha256"]
        ledger.append({"needle": needle, "live_user_reported": score, "source": src,
                       "file": dest.name, "sha256": got, "sha_match": ok, "status": status})
        print(("OK  " if ok else "FAIL"), dest.name, score)
    (DEST / "ledger.json").write_text(json.dumps(ledger, indent=1))
    n_ok = sum(1 for r in ledger if r.get("sha_match"))
    print(f"fetched+verified {n_ok}/{len(SCORED)} scored rasters")
    return 0


if __name__ == "__main__":
    sys.exit(main())
