# GEMSDOE76 Preregistration — Lane G76 "PIEDMONT DIPOLE"

**Written 2026-10-21, before any Exp-1 holdout score was computed in this repo.**
Session budget (parallel-run protocol): max 3 experiments, ~2 h of experiment wall-clock, 0 weekly
submission slots used by this session (promotion is a separate human selector step).

## 0. Lane assignment note (irregularity IR-76-01)

The protocol says "your lane is the single method paragraph below", but the supplied prompt
contains no single assigned method paragraph (same defect recorded by GEMSDOE70 session 2/3).
I therefore declare the lane myself, below, and stay inside it. Drift rule (protocol rule 1),
using the GEMSDOE70-P8 disclosed interpretation: **mutual** 3 px dot overlap ≤ 0.70 and surface
|Spearman ρ| ≤ 0.90 vs every registry raster I can obtain bytes for; literal one-way forward
overlap is also reported (the 206,895-dot calibration lattice's 3 px halo covers 99.87 % of the
footprint, so one-way forward overlap vs that synthetic witness is ~1.0 for *any* dot raster and
cannot be the operative test — disclosed, not hidden).

## 1. The lane (single method paragraph)

**Polarity-consistent piedmont scarp-dipole detector on the 1 m-LiDAR-derived 100 m stack.**
Decode the pinned 12-band uint8 LiDAR scarp stack (`lidar_scarp_features_u8.tif`, USGS 3DEP 1 m
source). A cell is fault-like only if it shows a *paired crest-toe dipole* — geometric mean of
crest convexity (`lapneg_max`) and base concavity (`lappos_max`) — together with a slope-facing
step (`step_max` high and polarity ratio `max(upface,downface)/(max(upface,downface)+cross_max)`
high, which rejects channel banks), *axial persistence* (the dipole-step response is smoothed
along the decoded local `strike` azimuth over ±2 px and weighted by `coh100`), and a *piedmont
domain gate* (decoded `relief` at or below the 75th percentile of relief sampled on the visible
catalogue — alluvial/piedmont scarps, not bedrock range fronts). Outside LiDAR coverage, a
label-free quantile-matched fallback from `det_elev` band-pass dipole × structure-tensor
coherence (training band 12) fills the domain so no footprint stratum is abandoned. Emission is
the shared template's exact greedy 300 m max-cover allocator (`vendor/gems57/emit.py`,
byte-pinned) on the rank-belief surface, catalogue pixels excluded pixel-exactly and the
live-validated B=2 px catalogue-flank exclusion applied (`d_cat > 2 px`); binary {0,1} dots,
zeros outside the footprint (portal-safe encoding; NaN twin only if explicitly labelled).

**Hypothesis.** The hidden expert-labelled faults are predominantly youthful Quaternary normal-
fault scarps in alluvium/piedmont that a human mapper finds in LiDAR topography; they carry the
crest-toe Laplacian dipole + slope-facing polarity signature at 1 m scale even when the 100 m
geophysics is unremarkable, which is exactly why geophysics-supervised lanes keep failing live
while the topography-led H19-5 lineage leads.

**Named non-fault mimics:** Pleistocene pluvial shoreline scarps (Lahontan/Bonneville — linear
dipoles, but contour-parallel; mitigated only by the polarity/piedmont terms, NOT by an elevation
filter — that is GEMSDOE70-P9's mechanism, deliberately not reused), terrace risers, channel
banks (rejected by polarity ratio), road grades/quarry benches (short, low coherence), dune slip
faces (high relief gate + low dipole pairing).

**Difference from prior lanes.** vs H19-5/H33 (0.2778 lineage): no supervised OOF model, no
thermal/geochemical lines, no worm/tip population terms; H19-5's openness covered only 8 tiles
(71,974 cells) whereas this uses the full-domain 3.89 M-cell LiDAR stack with explicit
dipole×polarity physics. vs GEMSDOE70-P9 H-P5-1: no DEM10, no χ/ksn drainage terms, no
shoreline-elevation penalty, no supervised heads. vs GEMSDOE70-E2 alluvial-step: 1 m-derived
dipole bands and LiDAR strike, not 100 m `det_elev` mean-shift across an RTP normal. vs
GEMSDOE30 H-31-02b (failed): adds the lapneg×lappos dipole product, the polarity-vs-channel
ratio, strike-guided anisotropic persistence, and the piedmont relief gate; H-31-02b had none of
these and emitted 93,390 top-mass dots. vs GEMSDOE66 lidar03 (0.1152 live): that lane trained on
SGMC bedrock faults and emitted 0 dots outside LiDAR; this lane is catalogue-free in its features
and explicitly fills the non-LiDAR stratum.

## 2. Candidate hypotheses considered and ranked (required 3–5)

| # | Hypothesis (layers → signature) | Why it targets *uncatalogued* faults | Non-fault mimic | Verdict |
|---|---|---|---|---|
| 1 | **Piedmont scarp dipole** (LiDAR lapneg×lappos, step, up/downface vs cross, strike persistence, relief gate) — **CHOSEN** | Experts map youthful alluvial scarps; sub-1.5 m throws invisible at 100 m but present in 1 m dipole bands | Pluvial shorelines, terrace risers | Exp 1–3 |
| 2 | Fan-chronosequence radiometric offset (GeoDAWN K/Th/U oriented step inside single fans) | Same-age fan surfaces offset by unmapped fault; airborne radiometrics sees surface age, not bedrock | Inset-fan boundaries, provenance change | Deferred: 100 m radiometric footprint likely too blurry; no budget left after lane 1 |
| 3 | Mapping-effort inversion (road distance × LiDAR coverage × visibility reweighting) | Catalogue completeness, not faulting, varies with access; hidden faults concentrate where effort was low | Genuinely fault-free remote basins | Deferred: second-order reweighting, needs a base detector (=lane 1) first |
| 4 | Seismicity lineation from bands 10/16 (`deq/ieq_n100a15`) | Blind active faults under basin fill align microseismicity | Geothermal-field induced seismicity, mine blasts | Rejected: band semantics unverifiable from official text; raw catalogue host (USGS) unreachable from this sandbox |
| 5 | Depth-to-basement hinge straightness (band 15) | Basin-margin hinges localize concealed faults | Depositional basin axes | Rejected: h61 basement-step lane scored 0.0009 live (owner ledger) |

No hypothesis above needs new external downloads beyond the SHA-pinned mirror stack already
restored and hash-verified in this session (see `registry/data_manifest.json`).

## 3. Frozen evaluation protocol

- **Instrument A (primary):** shared `gems57-pooled-hide-v2` hide-and-recover — whole catalogue
  segments withheld per quadrant fold (`vendor/gems57/holdout.py`, seeds 20 = decision,
  21 = confirmation only), visible faults masked pixel-exactly, pooled exact DTI
  (α=0.2, β=0.8, R=3 px), 1,000-draw paired 20 km spatial-cluster bootstrap CIs.
  All catalogue-derived quantities in my lane (relief gate quantile, B=2 distance) are recomputed
  from the **visible** catalogue inside each fold.
- **Instrument B′ (secondary):** SGMC off-catalogue faults with `d_cat ≥ 3 px` as truth
  (diagnostic proxy only; known to anti-track live scores — reported, never used as sole gate).
- **Instrument C76-pied (supporting):** B′ truth restricted to piedmont strata
  (`depth_to_base_surf ≥ 250 m`, `det_elev_slope ≤ p80` of catalogue values, LiDAR `relief ≤ p75`
  of catalogue values; quantiles from catalogue only, zero live-score fitting). My own
  recomputation in the spirit of GEMSDOE70's C_pied; their ρ=+0.87 live-correlation claim is
  treated as a *claim to verify* on rasters available here, not as established.
- **Leakage canaries:** AUC of every surface component alone vs withheld-segment pixels
  (Instrument A folds). Any AUC > 0.90 ⇒ leakage investigation before any result is trusted.
- **Controls:** fair-H33 (d2.8 parent dots re-pruned at B=2 vs *visible* catalogue per fold),
  count-matched uniform-random dots in the allowed domain, and (on B′/C76) the incumbent H33 dots
  as-is. H33-as-is on Instrument A is reported only as "not fold-honest" context.
- **Promotion gate (all required):** (i) candidate beats fair-H33 on Instrument A (seed 20,
  mode=all) with paired 95 % CI > 0; (ii) direction confirmed on seed 21 and on C76-pied
  (point estimate above H33); (iii) no canary > 0.90; (iv) uniqueness gates pass
  (mutual ≤ 0.70, |ρ| ≤ 0.90) on surface and final dots; (v) shared validator passes.
  If any gate fails, verdict = **negative**, the TIFF is published only as DO-NOT-SUBMIT
  evidence, and no slot is recommended. Negative results are deliverables.
- **Emission arms inside Exp 1 (one experiment, pre-declared arms):**
  (a) soft surface; (b) greedy cover, budget-matched 37,654 dots;
  (c) greedy cover stopped by the exact marginal bar with declared prior |G| = 12,500
  (lattice-inverted hidden-truth size, order-of-magnitude prior — recomputed and disclosed in
  Exp 1, sensitivity is Exp 2's only allowed change together with B ∈ {2,3}).
- **Exp 2 (only if Exp 1 is not a clear negative):** exactly one change among
  {prior |G| ∈ {8,000, 20,000}, flank prune B=3, budget 54,000} chosen by Exp-1 Instrument-A
  evidence. **Exp 3:** untouched confirmation (seed 21 + detached mode) of the frozen final
  configuration; no further tuning afterwards.

## 4. Score labelling discipline

Every number is labelled `HOLDOUT-DTI (gems57-pooled-hide-v2, n withheld, 95 % CI)`,
`PROXY-DTI (instrument, n, CI)`, or `ORGANIZER-REPORTED (user-supplied, no receipt in repo)`.
No projection is ever written as a score. The user's "0.2778" for the H33 zeros file and
"0.4413" public-leader value: the latter was verified on the live leaderboard page this session
(xiaofanhu, 2026-10-21); the former has **no organizer receipt in any cloned repo** and is
labelled user-supplied throughout.
