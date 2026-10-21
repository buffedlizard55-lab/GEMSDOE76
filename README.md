# GEMSDOE76 — Lane H76: Multi-Line Geothermal Upflow, Verduzco Potential-Field Tilt & Self-Masked Fracture Continuation for DOE GEMS Fault Detection

> ### STATUS: `GO — VERIFIED OK TO SUBMIT TO DRIVENDATA` (`VERDICT: PROMOTE` • `5 / 5` Pre-Registered Gates Passed)
> - **Primary Competition Upload (`.zip`):** [`docs/downloads/gems76_h76_3_geotherm_tilt_axial_submod_20261021_zeros.zip`](docs/downloads/gems76_h76_3_geotherm_tilt_axial_submod_20261021_zeros.zip) (`102.7 KB`, SHA-256: `76691a8a0dd945f9af82ffb47d4b2083e2448f2247d66e225a03d6abdd0f36d2`)
> - **Primary Competition GeoTIFF (`.tif`):** [`docs/downloads/gems76_h76_3_geotherm_tilt_axial_submod_20261021_zeros.tif`](docs/downloads/gems76_h76_3_geotherm_tilt_axial_submod_20261021_zeros.tif) (`136.9 KB`, SHA-256: `d706807d42d1b21f6417483cd7aeb04a410d62accd5a66c6b2a6ab0dc16662af`)
> - **Unique DrivenData Submission Name:** `gems76-h76-3-geotherm-tilt-axial-submod-zeros`
> - **Submission Note (`134 / 140` chars):** `H76-3: OOF geothermal vent+MT clay-cap+Verduzco grav/mag tilt+deconfounded 1m/10m DEM+12-az axial+self-masked continuation 300m submod`
> - **Portal Range Error Prevention (`"Predicted values must be in range [0, 1]"`):** Single-band `float32`, `EPSG:32611`, `3730 × 3292` (`[100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0]`), `min = 0.000000`, `max = 1.000000`, **`0` NaN cells across all `12,279,160` pixels**, `0` outside-footprint positives, `0` known-catalogue positives, `37,654` binary `1.0` predictions strictly outside the `d_cat <= 2.0 px` zero-credit collar (`16 / 16` preflight validator checks passed).
> - **GitHub Pages Site:** [`docs/index.html`](docs/index.html) (Full PhD Technical Report) & [`docs/executive-summary.html`](docs/executive-summary.html) (Step-by-Step DrivenData Upload Guide).

---

## 1. Key Findings & Experimental Results Summary

### 1.1 Exact Mathematical Forensic Explanation of `GEMSDOE32` `0.2778` (`ORGANIZER-CONFIRMED`) & How to Beat `0.3195` Toward `0.4413`
1. **Zero-Pixel Bitwise Identity (`0` XOR pixels across all `12,279,160` cells):**
   `GEMSDOE32`'s live `0.2778` submission (`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif`, `37,654` dots) is bit-for-bit identical to `(GEMSDOE25_D2.8 > 0) & (EDT(~existing_faults) > 2.0)`. Removing the **6,436** dots lying inside `d_cat <= 2.0 px` (`<= 200 m`) around masked catalogue faults removed `ΔTW = 47,871.7` units of pure zero-credit false-positive kernel mass with `ΔTP = 0`, deterministically raising live DTI from `0.2600` to **`0.2778` (`+0.0178` DTI)**.
2. **Exact Constant-`TP` Reciprocal Collinearity (`r = 0.999063`, `r^2 = 0.998127`):**
   Across five consecutive nested submissions (`D1.5` `60,069` px `0.2477` -> `D2.8` `44,090` px `0.2600` -> `H27-4` `40,199` px `0.2708` -> `G36` `38,854` px `0.2750` -> `H33` `37,654` px `0.2778`), solving the exact Tversky identity (`α = 0.2`, `β = 0.8`, `R = 300 m`) yields public-chunk denominator **`C_G = 48,192.0`** (`K_pub = 60,240.1` off-catalogue fault pixels) and proves every single one of those five submissions recovered the **identical true-positive mass `TP_0 = 38,900 ± 110` (`±0.28%`)**!
3. **Why Scores `> 0.3195` Up to `0.4413` Are Physically Achievable:**
   - Verified directly on the official DrivenData public leaderboard (2026-10-21, `ORGANIZER-CONFIRMED`), five teams already exceed `0.35`: **`#1 xiaofanhu = 0.4413`**, `#2 cfld__ = 0.3904`, `#3 Batik Shirt Brothers = 0.3811`, `#4 BrandenKMurray = 0.3713`, `#5 No Fault of Our Own = 0.3539`.
   - At `TW ≈ 380,000`, required kernel hit precision `h = TP / TW` is `11.68%` to beat `0.2778`, `14.06%` to beat `0.3195`, `17.92%` for Top-3 (`0.3811`), and `22.29%` to match `#1` (`0.4413`).
   - Prior supervised pipelines (`GEMSDOE70 P8`, live `0.2478`) were held back by **mountain-slope confounding** (`69.51%` of dots on steep erosional mountain walls vs `31.75%` true Quaternary faults), **`SGMC` pre-Quaternary bedrock contact targets** (`0.0492` live), **`1/z^2` potential-field burial decay**, and **self-identification collapse (`d_vis == 0`)**. Lane H76 resolves all four simultaneously.

### 1.2 Head-to-Head Spatial Hide-and-Recover Evaluation (`gems57-pooled-hide-v2`, `K = 11,321`)

All scores below are strictly out-of-fold **`HOLDOUT-DTI`** on shared `vendor/gems57/evaluate_holdout.py` (`seed=20`, `buffer_px=3`, `boundary_px=12`, `K = 11,321` withheld Quaternary fault pixels, `1,000` spatial-block bootstrap draws; **zero projections reported as scores**):

| Arm / Experiment | Evidence Class | Pooled `HOLDOUT-DTI` | 95% Bootstrap CI | Notes |
| --- | --- | ---: | :---: | --- |
| **`E76-2` Self-Masked Continuation + Physics HGB** | `HOLDOUT-DTI` | **`0.20124`** | `[0.17910, 0.22226]` | **+83.0%** above prior all-time record (`0.10997`) |
| **`E76-3` Shipped Hero Deliverable (`37,654` dots)** | `HOLDOUT-DTI` | **`0.15802`** | `[0.13856, 0.18024]` | **+43.7%** above `P9`; **34% / 32% / 34%** 3-regime blind-basin allocation; **5/5 gates PASS** |
| **`E76-3` Budget Sensitivity (`41,800` dots)** | `HOLDOUT-DTI` | **`0.15871`** | `[0.13866, 0.18048]` | Confirms robustness across dot-budget perturbation |
| **`E76-1` Pure Zero-Catalogue Multi-Physics (`37,654` dots)** | `HOLDOUT-DTI` | **`0.08666`** | `[0.06358, 0.11432]` | Pure geophysics/geomorphology with zero fault geometry |
| `GEMSDOE70 P9` Piedmont-Submod (Prior Record) | `HOLDOUT-DTI` | `0.10997` | `[0.09196, 0.12817]` | Best prior fold-proper model in `GEMSDOE70` |
| `GEMSDOE70 P8` Dual-Submod (`0.2478` live) | `HOLDOUT-DTI` | `0.10895` | `[0.09292, 0.12491]` | Prior shipped submodular baseline |
| `GEMSDOE32 H33` Fold-Fair (`D2.8 & d_vis > 2.0`) | `HOLDOUT-DTI` | `0.09609` | `[0.08312, 0.10953]` | Paired `Δ = +0.06193`, 95% CI `[+0.04876, +0.07632]` |
| `GEMSDOE25 D2.8` Static (`0.2600` live) | `HOLDOUT-DTI` | `0.09189` | `[0.07947, 0.10462]` | Paired `Δ = +0.06613`, 95% CI `[+0.05305, +0.08060]` |
| Uniform Random Off-Catalogue Control (`37,654` dots) | `HOLDOUT-DTI` | `0.03066` | `[0.02607, 0.03494]` | Exact matched-density null baseline |
| `GEMSDOE32 H33` Static Raster (`0.2778` live) | `HOLDOUT-DTI` | `0.00370` | `[0.00298, 0.00440]` | Masked on full `existing_faults.tif` (collar artifact) |

### 1.3 Complete Verification Gate Summary
- **Gate 1 — Single-Feature Leakage Canary (`<= 0.90`):** **63 / 63 PASS** (`max_symmetric_auc = 0.77222`; `evidence/leakage_canary_audit.json`).
- **Gate 2 — Multi-Repository Uniqueness Across All `860` SHA-256 Unique GeoTIFFs (`GEMSDOE` – `GEMSDOE82`):** **PASS** on both pre-placement surface (`max |Spearman rho| = 0.71366 <= 0.90`) and final binary dots (`mutual 3-px overlap = 0.43597 <= 0.70`; even unidirectional 1-way forward overlap across all sparse candidates `<= 100k` dots = `0.67855 <= 0.70`; includes live Pass-2 delta verification against just-merged PRs `GEMSDOE73 #10`, `GEMSDOE74 #13`, `GEMSDOE75 #8`, and `GEMSDOE77 #10`; `evidence/uniqueness_audit.json`).
- **Gate 3 — GeoTIFF & Single-GeoTIFF ZIP Portal Range Pre-Flight:** **16 / 16 PASS** (`[0.0, 1.0]`, `0` NaN, `EPSG:32611`, `3730 × 3292`; `evidence/validator_report.json`).
- **Gate 4 — Statistically Significant Holdout Gain vs All Benchmarks:** **PASS** (`evidence/holdout_evaluation.json`).
- **Gate 5 — Neotectonic Steep-Terrain Calibration (`[25%, 48%]` vs `31.75%` True Catalogue):** **PASS** (`evidence/spatial_profiles.json`).

---

## 2. End-to-End Autonomous Reproduction

```bash
# 1. Acquire & SHA-256 verify all 27 competition + external geophysical datasets and build 63-feature cache + canary audit
bash scripts/download_competition_data.sh

# 2. Execute the 3 preregistered experiments, 848-raster uniqueness audit, 16-gate GeoTIFF validator, figures & JSON Run Card
.venv/bin/python scripts/run_experiments.py

# 3. Build GitHub Pages site (docs/index.html & docs/executive-summary.html) dynamically from evidence/*.json
.venv/bin/python scripts/build_site.py

# 4. Run full end-to-end automated test suite
.venv/bin/pytest -q
```

---

## 3. Project Baseline Prompt Documentation

Per project instructions, the complete competition research specification and parallel-run protocol governing `GEMSDOE76` are documented below as the baseline contract:

- **Competition Target:** DrivenData / U.S. Department of Energy American-Made GEMS Challenge (`https://www.drivendata.org/competitions/306/competition-doe-gems/`), single-band `float32` `[0, 1]` GeoTIFF on `EPSG:32611` (`3730 × 3292`, 100 m spacing) scored off-catalogue by Dilated Tversky Index (`α = 0.2`, `β = 0.8`, 300 m triangular kernel).
- **Mandatory Deliverables & Rules:**
  1. PhD-level root-cause analysis of why `GEMSDOE32` `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` achieved `0.2778` (`ORGANIZER-CONFIRMED`) and how a submission can surpass `0.2778` and `0.3195` toward top leaderboard performance (`0.4413`).
  2. Pre-registered ranking of 3–5 novel geological/geothermal fault-discovery hypotheses specifying input layers, physical transforms, why they catch faults omitted from the USGS/INGENIOUS catalogue, non-fault mimic suppression, novelty vs prior `GEMSDOE` lanes, expected DTI gain, and free official data sources (`docs/preregistration-h76.md`).
  3. Reuse shared `evaluate_holdout.py` and `submission_writer.py` with spatially-blocked buffered component hide-and-recover evaluation, visible-only feature refitting, pixel-exact catalogue masking, and explicit score labeling (`HOLDOUT-DTI` vs `ORGANIZER-CONFIRMED`; zero projections written as scores).
  4. Single-feature leakage canaries (`AUC <= 0.90`), pre-placement surface & post-placement dot uniqueness checks (`|Spearman rho| <= 0.90` and `3-px dot overlap <= 0.70`), strict `[0, 1]` zero-NaN GeoTIFF validation, prominent top-of-page GO / DO-NOT-SUBMIT download UX, three complete verification passes, canonical JSON Run Card, and GitHub PR created and merged into `main`.
