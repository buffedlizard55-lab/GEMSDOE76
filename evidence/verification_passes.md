# Three-Pass Verification Log — `GEMSDOE76` (Lane H76)

## Pass 1 — Full Implementation, Execution & Pre-Registered Gate Resolution
1. **Data & Channel Forensics (`scripts/download_competition_data.sh`, `scripts/restore_data.py`, `scripts/prepare_data.py`):**
   - Verified SHA-256 checksums across all 3 official competition rasters and 24 external geophysical/geomorphic layers (`evidence/data_manifest.json`).
   - Uncovered and fixed four upstream channel pitfalls before training: float32 sentinel `-3.4028235e+38` on ~0.13% of finite footprint cells, seamless GeoDAWN gamma Total Count identity of `B06 tc` (`r = 0.997140`), `log10(resistivity)` sign on `B17 cond_surf`, and `cov_fp_indices` sparse storage + `Band 9 = relief` layout in `dem1m_high_prior_openness_lrm.npz`.
2. **Leakage Canary Audit (`evidence/leakage_canary_audit.json`):**
   - Tested all 63 features individually on `K = 11,321` withheld Quaternary fault pixels (`gems57-pooled-hide-v2`): **63 / 63 PASS** (`max_symmetric_auc = 0.77222 <= 0.90`).
3. **Three-Experiment Campaign (`E76-1`, `E76-2`, `E76-3`) & Automated Gate Catch (`IR-76-003`):**
   - Ran out-of-fold models within cgroup memory limits (`Peak RSS = 2,227 MB < 3,939 MB`), establishing new `HOLDOUT-DTI` records (`E76-2 = 0.20124`, `E76-3 = 0.15802` vs prior all-time record `GEMSDOE70 P9 = 0.10997`).
   - Initial unconstrained `E76-3` triggered pre-registered Gate 5 (`steep_mountain_fraction = 15.43%` due to double application of `calibrate_terrain_prevalence`) and one-way overlap >0.70 against an 80k-dot candidate. Fixed by single-pass quantile terrain calibration (`27.57%–31.8%` steep parity) + 3-regime submodular allocation (`34%` continuation `2–10 px` / `32%` relay step-over `10–26 px` / `34%` blind multi-physics `>26 px`), achieving **`VERDICT = PROMOTE` (`5 / 5` gates `TRUE`)**.

## Pass 2 — Line-by-Line Audit of Code, Figures, Links & Live Concurrent Sibling Repos
1. **Figure & Evidence Consistency Fixes Caught in Pass 2:**
   - Updated `Figure 1` to include `GEMSDOE70 P9 (0.10997)` alongside `P8 (0.10895)` and exact `44,090` dot count on `GEMSDOE25 D2.8`.
   - Updated `Figure 2` to plot all 6 nested live submissions (`H19.5 -> D1.5 -> D2.8 -> H27-4 -> G36 -> H33`, `r = 0.999063`, `0` XOR pixels).
   - Fixed `E76_3_hero_sensitivity_41800` key in `evidence/run_card.json` to report `0.15871` cleanly rather than duplicating `E76_3_hero_matched_37654` (`0.15802`).
2. **Test Suite Attribute Fix Caught in Pass 2:**
   - Fixed `metric.RADIUS_M` -> `metric.RADIUS_PX == 3.0` (`300 m` at `100 m/px`) in `tests/test_gems76_end_to_end.py`.
3. **Real-Time Concurrent Sibling Repository Scan (`GEMSDOE73`–`GEMSDOE82`):**
   - Polled live GitHub trees across `GEMSDOE73`–`GEMSDOE82` during Pass 2 and detected **12 newly merged concurrent sibling deliverables** (`GEMSDOE73 PR #10`, `GEMSDOE74 PR #13`, `GEMSDOE75 PR #8`, `GEMSDOE77 PR #10`), expanding the uniqueness corpus from **848 to 860 unique SHA-256 GeoTIFFs**.
   - Verified zero collision against every single newly merged sibling raster (`mutual 3-px overlap = 0.247–0.406 <= 0.70`, `|Spearman rho| = 0.031–0.104 <= 0.90`) and regenerated `uniqueness_audit.json`, `run_card.json`, `fig5_uniqueness_audit.png`, `docs/index.html`, and `docs/executive-summary.html`.

## Pass 3 — Final Independent Re-Verification & Release Hygiene Check
1. Re-ran full `pytest -v` suite (`4 / 4 PASSED` in `< 1.2s`).
2. Verified all 35 local asset/download links across `docs/index.html` and `docs/executive-summary.html` resolve cleanly with zero broken paths and zero un-escaped template braces (`0` leaks).
3. Re-verified SHA-256 byte identity across `submissions/`, `docs/downloads/`, `evidence/run_card.json`, `docs/index.html`, `docs/executive-summary.html`, and `README.md`, and verified clean Git tracking size well below snapshot/repo limits prior to PR creation & merge into `main`.
