# GEMSDOE76 — Lane G76 "Piedmont Scarp-Dipole" · verdict: **negative (DO NOT SUBMIT)**

DOE GEMS Prize Challenge (DrivenData #306) — one pre-registered parallel-run lane, executed
line-by-line against official sources. **Read [`PROMPT.md`](PROMPT.md) first every session.**

## ⛔ Submission status — read this first

**There is NO approved submission file in this repository.** The only TIFF produced,
`docs/downloads/gems76-piedmont-dipole-exp2-27569dots-DO-NOT-SUBMIT.tif`
(SHA-256 `322ca8753a56e71796db6ceb9c7a03f76f890aff1d09f9180304d84e64152178`), is format-valid
(shared fail-closed writer: single-band float32, EPSG:32611, 3730×3292, all cells finite in
[0,1], 0 dots on the catalogue) and provably unique (worst mutual 3 px overlap **0.106** vs
122 registry rasters) — but it **failed its promotion gate** and must not be submitted:

| Evidence (all local; no organizer-confirmed score exists here) | Value |
|---|---|
| HOLDOUT-DTI (gems57-pooled-hide-v2, seed 20, n=11,321 withheld px) — Exp2 candidate | **0.0218** [0.0145, 0.0303] |
| HOLDOUT-DTI — fair-H33 control (same evaluator) | 0.0927 [0.0802, 0.1058] |
| HOLDOUT-DTI — count-matched random dots | 0.0458 |
| PROXY-DTI B′ (SGMC off-catalogue, n=63,121) / C76-piedmont (n=10,792) | 0.0172 / 0.0208 |
| Leakage canaries (max feature-alone AUC, alarm >0.90) | 0.60 — clean |
| Weekly competition slots used by this session | **0** |

Site (GitHub Pages, `/docs`): https://buffedlizard55-lab.github.io/GEMSDOE76/ — verdict banner
first, executive summary at `docs/executive-summary.html`, run card at `docs/run-card.json`.

## What was tested and why it failed

**Hypothesis:** youthful Quaternary scarps missing from the USGS/INGENIOUS catalogue carry a
paired crest-toe Laplacian dipole + slope-facing polarity in 1 m LiDAR derivatives, mostly in
low-relief piedmont. **Exp 1** (hand-set dipole product) and **Exp 2** (pre-registered logistic
combiner over the same 10 components; `docs/preregistration-g76.md`, `…-amendment-exp2.md`) both
scored ≈0.022 HOLDOUT-DTI — below random. Measured cause: the LiDAR bands are max-pooled from
2 m to 100 m, so every fan channel saturates them (best single-field AUC 0.631; fitted holdout
AUC 0.620; ranking top hits truth at 3.0% vs 1.7% random). Under the 300 m max-cover metric,
concentrated-but-imprecise dots lose to a uniform spread. DEM10 one-sided fields are no better
(AUC 0.496). **Per-pixel 100 m fields cap at AUC ≈0.63 regardless of sensor** — the winning
family's advantage is learned multi-physics corroboration + spatial context, not a transform.

## Why the incumbent (0.2778, USER-REPORTED) leads the family

Forensically (all measured from local bytes; full write-up `docs/research/why-02778.md`):
`h33-h33-2-b2…-zeros` is a **strict subset** of the 44,090-dot D2.8 raster — the supervised,
4-quadrant-OOF, catalogue-distance-free H19-5 surface thinned to isolated dots, then pruned of
every dot within 2 px of the catalogue (37,654 dots; median 2.0 km from known faults). The
`-zeros` encoding adds no score (twins are bit-identical in-footprint) but cannot fail the
portal's "[0, 1]" whole-raster check. Beating it needs roughly **2× the truth coverage**
(leader 0.4413, verified on the official leaderboard 2026-10-21, implies c≈0.5 vs incumbent
c≈0.3) — a surface problem, not an emission problem. This session also re-scored **77
hash-verified registry rasters** on three instruments vs their USER-REPORTED live scores:
Spearman ρ = 0.16 (Instrument-A-as-is, construction-biased), 0.33 (SGMC B′), **0.52**
(piedmont-conditioned C76). No local instrument reliably ranks the top; B′ is trivially
gameable by SGMC-derived files. See `evidence/instrument_audit.json`, `docs/score-ledger.csv`.

## Repository map

- `PROMPT.md` — operative prompt + parallel-run protocol + core values (read first).
- `docs/` — GitHub Pages site (verdict-first), executive summary, preregistrations,
  `irregularities.md` (9 flagged items, incl. the incumbent site's **empty download ZIP**),
  downloads (DO-NOT-SUBMIT artifact + writer receipt), `score-ledger.csv`, figures.
- `evidence/` — `run_card.json`, per-experiment manifests/canaries/holdout/proxy JSONs,
  instrument audit, uniqueness audit, data receipt.
- `src/gems76/` — lane code only (`features.py` dipole surface, `model.py` Exp-2 combiner).
- `vendor/gems57/` — shared template, byte-pinned copy of `60GEMSDOE/src/gems57`
  (`registry/template_pin.json`); **never edited** (protocol rule 2). One defect found in its
  greedy allocator is reported in `docs/irregularities.md` (IR-76-06) for upstream fixing.
- `scripts/` — `restore_data.py` (SHA-pinned mirror restore — the "data placement blocker"
  does not exist where GitHub is reachable), `run_experiment{1,2}.py`, `fetch_registry.py`,
  `audit_instruments.py`, `build_artifact.py`, `audit_uniqueness.py`, `build_site.py`.
- `registry/data_manifest.json` — every input byte pinned by SHA-256 (mirror integrity ≠
  organizer authentication). `data/bridge/` — the two small grid-defining rasters.
- `tests/` — shared-metric verification vs the official formula (brute force + hand examples).

## Reproduce

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/restore_data.py        # needs authenticated `gh`
.venv/bin/python -m pytest -q
.venv/bin/python scripts/run_experiment1.py     # refuses to re-run if evidence exists
.venv/bin/python scripts/run_experiment2.py
.venv/bin/python scripts/build_artifact.py && .venv/bin/python scripts/audit_uniqueness.py
.venv/bin/python scripts/build_site.py
```

## Limitations & next steps (for the next session / selector)

- **Limitations of this environment:** no DrivenData auth (cannot submit, read slot balance,
  or organizer-authenticate mirrored data); no GPU (2 CPU / 3 GB) — the identified highest-
  upside route (2-D patch-context U-Net-class model, whole-component OOF, no catalogue-distance
  inputs) needs real compute. Non-GitHub/PyPI hosts unreachable from the sandbox.
- **For the human selector:** no file here is slot-worthy. Among existing unscored files
  measured this session, GEMSDOE70's P9 hero leads the least-bad instrument (C76-pied 0.1079);
  that is a measurement, not a pick — and its own site asks for selector sign-off on literal
  forward-overlap vs the calibration lattice.
- **Next scientific step (new lane required):** GPU-backed patch-context supervised model in
  the H19-5/P9 recipe family; or a genuinely new data type. Do not re-run scarp-transform
  variants at 100 m — falsified here and in ~10 sibling lanes.
- **Housekeeping owed upstream:** fix `gems57.emit.greedy_allocate` early-stop on diffuse
  surfaces (IR-76-06) in 60GEMSDOE; replace GEMSDOE32's empty `…-zeros.zip` (IR-76-02).
