# GEMSDOE76 Preregistration — Lane G76B "PATCH-CONTEXT CORROBORATION"

**Written 2026-10-21, before any G76B holdout score is computed in this repo.**
Session budget (parallel-run protocol): max 3 experiments, ~2 h experiment wall-clock, 0 weekly
submission slots used by this session (promotion is a separate human selector step).

## 0. Lane assignment note (irregularity, same class as IR-76-01)

The protocol refers to "the single method paragraph below"; the supplied prompt again contains no
unambiguous assigned method paragraph (verified for this session's text). I therefore declare the
lane below myself and stay inside it. Drift rule (protocol rule 1, GEMSDOE70-P8 disclosed
interpretation): **mutual** 3 px dot overlap ≤ 0.70 and surface |Spearman ρ| ≤ 0.90 vs every
registry raster I hold bytes for; one-way forward overlap is also reported (the 206,895-dot
calibration lattice's 3 px halo covers ~99.9 % of the footprint, so forward overlap vs that
witness is ~1.0 for *any* dot raster — disclosed, not hidden).

## 1. The lane (single method paragraph)

**Multi-physics patch-context corroboration surface.** Four catalogue-free lineament response
families are built on the pinned stack: (i) the 1 m-LiDAR scarp dipole response (this repo's own
G76 components: `step_max`, `√(lapneg_max·lappos_max)`, polarity, coherence, strike persistence;
`det_elev` band-pass fallback outside LiDAR coverage), (ii) a magnetic edge response `|∇rtp|`
plus a **cross-scale edge-agreement** term `min(rank|∇rtp|, rank|∇TMI_up150|)` that is high only
where the edge location survives 150 m upward continuation, (iii) a de-regionalized isostatic
gravity edge `|∇(iso_grav − 15 px mean)|`, and (iv) a radiometric alteration edge from
`K/(Th+10)` local anomalies. Each response is then given **2-D patch context** — directional
persistence (max over 8 azimuths of a 5-tap line-kernel mean) and local support density
(5×5 mean of the response rank) — the ingredient the G76 post-mortem identified as missing.
Regional **strain-belt context** (21 px means of `geod_2ndinv`/`geod_shearrate` ranks and
|`geod_dilaterate`| rank) gates the surface toward actively deforming belts. The ~27 features
feed a fold-honest `HistGradientBoostingClassifier` head (positives = fold-visible catalogue,
training pool excludes the tested quadrant entirely and is 12 px-eroded from it, P8-style
isolation), predicted per holdout fold, and per production quadrant (leave-one-quadrant-out).
Emission is the shared template's exact greedy 300 m max-cover allocator
(`vendor/gems57/emit.py`, byte-pinned), catalogue pixels excluded pixel-exactly, live-validated
B = 2 px catalogue-flank exclusion, binary {0,1} dots, zeros outside the footprint
(portal-safe), written only through the shared `submission_writer`.

**Hypothesis.** The hidden expert-mapped faults require *multi-sensor agreement at neighbourhood
scale*: a per-pixel measurement caps at AUC ≈ 0.63 (G76 measured), whereas corroborated
patch-scale lineament organization plus regional active-strain context is the minimum
information an expert uses. Adding patch context to a supervised OOF head should recover
withheld catalogue segments better than any single-measurement lane and better than the
incumbent emission geometry, without new external data.

**Named non-fault mimics:** stratigraphic/lithological contacts (coherent at all scales —
mitigated only by requiring agreement across *unrelated* physics families, not one field's
self-agreement), pluvial shoreline complexes (topographic dipoles, contour-parallel), road and
pipeline corridors (LiDAR steps; road-distance band exists but is NOT used as a feature),
InSAR processing/atmospheric strain artifacts (smooth regional strain), playa evaporite
chemistry (radiometric K/Th), remanence-domain magnetic edges that do not persist upward.

**Difference from prior lanes.** vs G76 (this repo, negative 0.0218): G76 emitted a
single-measurement scarp response alone; G76B uses four physics families, patch context and a
supervised head — the documented missing ingredients. vs GEMSDOE70-P8 (best known Instrument A
0.1113): P8's 41 features are per-pixel localized physical channels + catalogue-geometry
features; G76B adds cross-scale magnetic edge agreement, patch support/directional context, and
strain-belt gating, and uses no catalogue-geometry features at all. vs H19-5/H33 lineage
(user-reported 0.2778): H19-5 is a 4-line gated OOF ensemble (openness/LRM scarps, power-law
tips, thermal/geochemical orphans, worms) with no strain, no cross-scale agreement and no patch
support terms; G76B is a single HGB head over context features. vs 16GEMSDOE (h16-1,
user-reported 0.1855): that lane used `up150` gradient magnitude and raw strain intensities
per-pixel; G76B uses cross-*scale* edge-location agreement and regional strain *context*. The
model class (HGB), holdout evaluator (`gems57-pooled-hide-v2`), allocator and writer are shared
template tools (protocol rule 2), not private forks.

## 2. Candidate hypotheses considered and ranked (required 3–5)

Ranked by expected Instrument-A DTI improvement × implementation cost under the 3 GB / 2 CPU
sandbox constraint. H2–H4 are components of H1; H5 is independent.

| # | Hypothesis (layers → signature) | Why it targets *uncatalogued* faults | Non-fault mimic | Verdict |
|---|---|---|---|---|
| 1 | **Patch-context corroboration** (LiDAR scarp + magnetic edge + gravity edge + radiometric edge, each with directional persistence and 5×5 support density; cross-scale `∇rtp`×`∇TMI_up150` edge agreement; 21 px strain-belt gating; HGB OOF head) — **CHOSEN** | Experts corroborate multiple sensors at neighbourhood scale; per-pixel fields cap at AUC 0.63 (G76 measured); context is the organizer-reference (CNN) ingredient no family lane has run | Stratigraphic contacts, shorelines, roads, InSAR artifacts | Exp 1–3 |
| 2 | Cross-scale magnetic edge persistence (tilt-depth style): edge must survive 150 m upward continuation | Deep blind faults under basin fill have no scarp but persist upward; surficial noise dies with height | Deep lithological contacts, remanence domains | Included as H1 component |
| 3 | Strain-belt gating of geomorphic scarps (regional `geod_2ndinv`/shear/dilatation means) | Catalogue completeness is geomorphic; active strain marks structures mappers missed | Hydrological/processing InSAR artifacts, volcanic uplift | Included as H1 component |
| 4 | Radiometric alteration-oriented edges (`K/(Th+10)` local anomaly gradients) | Fault-controlled hydrothermal alteration traces fluid conduits that can be geomorphically blind | Playa chemistry, soil parent-material changes | Included as H1 component |
| 5 | Vent/wellspring fissure-alignment density (GDR volcanic-vents + wellspring CSVs) | Young volcanic fissure swarms are underrepresented in fault catalogues | Non-tectonic spring clustering, anthropogenic well siting bias | Rejected standalone: GEMSDOE71's hydro-conduit lane (user-reported 0.0558) shows proximity features anti-track; sparse points give a coarse density field; H1 subsumes any value via the strain/topo context |

No hypothesis needs new external downloads: the SHA-pinned mirror stack (13/13 verified this
session, `registry/data_manifest.json`) contains every layer used.

## 3. Frozen evaluation protocol

- **Instrument A (primary):** shared `gems57-pooled-hide-v2` — `holdout.buffered_component_draw(
  grid, seed=20, buffer_px=3, boundary_px=12)`, visible faults masked pixel-exactly, pooled exact
  DTI (α=0.2, β=0.8, R=3 px), 1,000-draw paired 20 km spatial-cluster bootstrap CIs. Fold-honest
  per fold: the HGB head for fold k is trained with positives from the fold-visible catalogue
  restricted to a pool that **excludes the tested quadrant entirely** (12 px-eroded), so no test
  pixel or its neighbours contribute to training.
- **Controls (same folds):** `fair_h33` (D2.8 parent dots re-pruned at `d_vis > 2` vs the
  fold-visible catalogue), `fair_p8` (GEMSDOE70-P8 dots re-pruned identically — the best known
  holdout surface's raster, bytes fetched and hash-verified), `d28_reference` (static D2.8),
  `random_dots` (count-matched uniform). `candidate_surface` (soft, clipped [0,1]) also scored.
- **Instrument B′ (secondary, diagnostic):** SGMC off-catalogue truth `d_cat ≥ 3 px`.
- **Instrument C76-pied (supporting):** B′ truth restricted to piedmont strata
  (`depth_to_base_surf ≥ 250 m`, `det_elev_slope ≤` catalogue p80, LiDAR `relief ≤` catalogue p75
  where LiDAR exists) — the best live-tracking local instrument measured in this repo
  (ρ = 0.52 vs user-reported live, `evidence/instrument_audit.json`).
- **Leakage canaries:** AUC of every feature alone (and the fold-honest fitted probability)
  against pooled withheld-segment positives. Any AUC > 0.90 ⇒ stop and investigate.
- **Promotion gate (all required):** (i) `candidate_dots` beats `fair_h33` on Instrument A
  (seed 20) with paired 95 % CI > 0; (ii) C76-pied point estimate above `h33_ref`; (iii) no
  canary > 0.90; (iv) uniqueness gates pass (mutual ≤ 0.70, |ρ| ≤ 0.90) on the final surface and
  final dots vs every registry raster held locally (count disclosed); (v) shared validator
  passes. `fair_p8` comparison is reported as context (Instrument A is known to weakly track
  live scores, ρ = 0.16; it is not the sole gate). If any gate fails, verdict = **negative**,
  the TIFF is published only as DO-NOT-SUBMIT evidence, and no slot is recommended.
- **Arms inside Exp 1 (one experiment, pre-declared):** soft surface; greedy budget-matched
  37,654 dots. **Exp 2 (only if Exp 1 is not a clear negative):** exactly one change among
  {strain-belt weight ablation, B=3 collar, budget 44,090} chosen by Exp-1 evidence.
  **Exp 3:** untouched confirmation on seed 21 of the frozen final configuration; no tuning
  afterwards.
- **Emission parameters frozen before scoring:** `emit.greedy_allocate(prob, allowed,
  k_truth=1e12, max_dots=37654, candidate_cap=600000)`; `allowed = valid ∧ (d_vis > 2)` per
  fold, `allowed = valid ∧ (d_cat > 2)` for the final (production LOQO) surface;
  `valid = binary_erosion(fp ∧ finite(det_elev) ∧ finite(det_elev_slope), 12)` — identical to
  the G76 session so controls reproduce.

## 4. Score labelling discipline

Every number is labelled `HOLDOUT-DTI (gems57-pooled-hide-v2, n withheld, 95 % CI)`,
`PROXY-DTI (instrument, n, CI)`, or `USER-REPORTED (no organizer receipt in this repo)`.
No projection is ever written as a score. "0.2778" (H33) and "0.4413"/"0.3195" (conflicting
leader values in the request — irregularity IR-76-02 class) are user-supplied numbers; the
live board read on 2026-10-21 by the prior session showed 0.4413 at the top.
