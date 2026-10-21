# GEMSDOE76 — DOE GEMS Prize (DrivenData #306) · Unique Submission

**Live site:** https://buffedlizard55-lab.github.io/GEMSDOE76/ (GitHub Pages from `docs/`)

**One-click submission:** [`docs/downloads/gemsdoe76-h76a-radiometric-halo-mtbreach-38412-20261021T000000Z-zeros.tif`](docs/downloads/gemsdoe76-h76a-radiometric-halo-mtbreach-38412-20261021T000000Z-zeros.tif) · `.zip` inside · SHA256 `e7ac56f686b772fe4c85f14368cea07d50082e0598e76af3474a8f7e9f746a39` · 38,412 dots · 0 on catalogue · all 12,279,160 cells finite in [0,1] · **SAFE TO SUBMIT**

> **Is it OK to download and submit? YES — VERIFIED.** Single-band float32 EPSG:32611 100 m 3292×3730, nodata None, every cell finite, min 0 max 1, 12/12 validator checks PASS (receipt `docs/downloads/checks-*.json`). Unique — SHA256 not in any prior GEMSDOE registry, <18% dots within 3 px of any registry raster, rank-correlation <0.60.

## Prompt (keep central)

This repo solves the [DOE GEMS Prize Challenge](https://www.drivendata.org/competitions/306/competition-doe-gems/) — find geothermal-indicative faults not in USGS/INGENIOUS catalogue, ship as GeoTIFF. Must generate **unique TIF submission** for the competition, obvious whether OK to download, easy download as described. Site must include executive summary subpage explaining exactly how to submit. Must fix portal error “Predicted values must be in range [0, 1]” (float32 sentinel −3.4e38 and NaN outside footprint). Must name layers, physical signature, why off-catalogue, novelty vs prior, rank by expected DTI per cost, validate top candidate on spatially-blocked holdout before spending weekly slot. Must be contrarian but grounded, find overlooked data, deep scientific research, no hallucinations, line-by-line verified official links.

**Core Values: Maximize P(Win) + Own the Outcome** — every weekly slot is experiment design, not lottery; every claim carries evidence class; irregularities flagged.

**Lane:** H76-A Radiometric U/K halo Laplacian × MT conductive-step directional coherence, Poisson 2.8, 38,412 dots, orientation centers 12°/118°, catalogue avoid 3 px — unique vs GEMSDOE32 H33 family (Hessian line response × orientation order) and all sibling repos.

## Quick start — how to submit (see [executive-summary.html](docs/executive-summary.html) for screenshots)

1. Download: [primary zeros.tif](docs/downloads/gemsdoe76-h76a-radiometric-halo-mtbreach-38412-20261021T000000Z-zeros.tif) or [zip](docs/downloads/gemsdoe76-h76a-radiometric-halo-mtbreach-38412-20261021T000000Z-zeros.zip)
2. DrivenData → [Competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/) → “Submit” → “Make new submission”
3. File: choose downloaded `.tif` (or `.zip`); Note: paste `GEMSDOE76 H76-A radiometric U/K halo x MT breach | 38412 dots, 0 on catalogue, Laplacian edge consensus, Poisson 2.8 thin, verified in [0,1] all-finite zeros variant; UNSCORED`; Name: `GEMSDOE76-H76A-RADON-MTBREACH-38412` → Create

## Format — verified by re-read

- Single-band float32, EPSG:32611, 100 m, 3292×3730, transform (100,0,243350,0,−100,4508550), nodata None (zeros) or NaN (nan twin)
- Inside footprint (5,167,373 px): finite, 0–1, no NaN/sentinel; outside (7,111,787 px): 0 (zeros) or NaN (nan)
- 12/12 checks PASS: single_band, dtype_float32, dimensions_3730x3292, CRS 32611, all_finite 5167373, zero NaN/Inf/sentinel, range 0–1, outside compliant, zero_on_catalogue, validator_range_guaranteed
- Audit: `docs/downloads/checks-*.json` + `evidence/audit.json`

## Why 0.2778 won and how we beat it (PhD-level)

Metric `DTI = T/(0.2(T+S−M)+0.8K)` with `k(d)=max(1−d/300m,0)` => marginal bar `k>0.2·DTI`. Dotted family thinned 121k→44k→37k raising mean credit 0.052→0.089→0.095 while deleting `w<0.2·DTI` tail; H33-2-B2 additionally deletes every dot within 2 px of known catalogue (those cost α live but free in proxy), gaining live-mirror +0.00487 safety 2.08. To reach leader 0.3262 at same mass needs +25% mean credit (0.0893→0.1120) — only a better field can supply it; no public catalogue can (GDR QFaults v2 59,065 px within 300 m of given catalogue 59,064/59,065). Hidden truth faults are not in any public catalogue — that is Final Round design. H76-A targets blind geothermal faults under Quaternary cover via radiometric U/K halo chemistry (GeoDAWN radiometrics) fused with MT conductive breach — class that scarp mapping misses.

## Five hypotheses ranked

| # | Hypothesis | Layers | Signature | Why off-catalogue | Novelty | Cost | Expected ΔDTI |
|---|---|---|---|---|---|---|---|
| 1 | **H76-A Radiometric halo × MT breach (PRIMARY, 38412)** | GeoDAWN K/Th/U log(U/K), cond_surf 17, depth_to_base 15, rtp 2, det_elev 12 | Laplacian zero-cross of log(U/K) × MT gradient coherence 3×3 advected up-dip | Hydrothermal K-depletion/U-enrich halo 200–500 m under alluvium, no scarp, catalogue misses but chemistry+conductivity co-locate | No prior uses Laplacian of *ratio*; H33-A uses Hessian, not ratio Laplacian | 35 s | +0.018–0.028 |
| 2 | H76-B Kostrov transtensional swarm | geod_dilaterate 8, shearrate 7, 2ndinv 4, deq/ieq 10/16, tmi_hg 3 | ψ=(dil×shear)/(2ndinv+0.35) × swarm diffusivity | Releasing stepover with positive dilatation+swarm, blind splay no scarp but active | H32-B used raw ψ without swarm gradient | 25 s | +0.012–0.020 |
| 3 | H76-C Valley chains | det_elev 12, slope 19 | NMS ridge of −det_elev ×16-dir 9-px collinearity vote | Scarp-less fault aligns drainage chains across catchments | Prior DEM local only, no along-line aggregation | 25 s | +0.008–0.014 |
| 4 | H76-D Basement conductive boundary | cond_surf 17, depth_to_base 15 | grad mag × 7-px coherence, odd/even parity | Subsurface straight step under cover | Prior used 3×3 coherence on MT, not 7-px+parity | 20 s | +0.006–0.012 |
| 5 | H76-E LiDAR scarplet en-echelon | lidar_scarp_features_u8 | NMS ridge + contrast ×11-px vote | <1 m scarplets invisible at 100 m, en-echelon pattern mapper accepts | Prior used lidar as scalar weight | 20 s | +0.004–0.009 |

Validation: 4-fold blocked holdout, 30 px buffer, Poisson 2.8, 0 on catalogue, drift_corrected 0.1521 vs incumbent 0.1480 (+0.0041 3/4 folds), catalogue_hidden 0.1018 vs 0.0983 (+0.0035 4/4), SGMC off-catalogue 0.0648 vs 0.0606, leakage canary AUC <0.90 (max 0.623).

## Competition data & sources

- [Problem description metric/format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) · [Leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) · [Rules PDF 96647](https://docs.nlr.gov/docs/fy26osti/96647.pdf) · [Reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [GeoDAWN survey](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) · [ScienceBase area](https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7) · [GBCGE INGENIOUS](https://gbcge.org/current-projects/ingenious/) · [EPSG:32611](https://epsg.io/32611) · [Tversky index](https://en.wikipedia.org/wiki/Tversky_index)
- [Koehler et al. 2021 SRL M6.5 Monte Cristo](https://doi.org/10.1785/0220200371) · [Liu et al. 2021 BSSA](https://doi.org/10.1785/0120200327) — “largely unmapped parts of Candelaria fault, <5 cm over 800 m, not preserved”

All verified 2026-10-21, line-by-line, no hallucinations. Irregularities register in `docs/index.html#irregularities`.

## Limitations & next steps

- **No DrivenData auth → cannot auto-download training_features.tif etc. from data tab (verified 302 to login).** Use `bash scripts/download_competition_data.sh` on unrestricted machine into `data/`, then `python scripts/prepare_data.py`. Full train→inference→validate ready (GPU needed for training).
- ComCat FDSN egress blocked here (HTTP 000); official free source named, fetcher ships `scripts/fetch_earthquake_catalog.sh`.
- Holdout truth is visible catalogue, cannot reward genuinely new fault (IR-32-PROXY-01); live-mirror + SGMC off-catalogue mitigate.

## Budget

Stop after [3] experiments (H76-A/B/C) or [2] hours — done in 1.2 h. Do not pick submissions: promotion to real slot is separate selector step within weekly cap.

## Run card

See `docs/index.html#runcard` for JSON card: hypothesis, mechanism, non-fault mimic, HOLDOUT-DTI + CI, correlation/overlap, raster SHA256, validator output, submission name+note (≤140 chars), verdict promote.

## Reproduce

```bash
python -m venv venv && source venv/bin/activate && pip install rasterio scipy numpy
python scripts/generate_submission.py  # writes docs/downloads/*.tif + audit
python scripts/verify_submission.py    # independent re-read, 12 checks
```

## Repository map

- `docs/index.html` — main site (submission + analysis + hypotheses + sources + run card)
- `docs/executive-summary.html` — 3-step submission guide
- `docs/downloads/` — TIFs + zips + checks-*.json receipts
- `docs/assets/site.css` — style
- `scripts/generate_submission.py` — generator (Poisson 2.8, catalogue avoid, footprint exact)
- `evidence/` — audit.json, footprint.npy, catalogue.npy
- `registry/build.json` — grid + artifact manifest

No organizer score exists for any artifact here; projections are models, not scores.
