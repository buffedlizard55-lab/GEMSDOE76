# GEMSDOE76 review — 2026-10-21

## Executive decision

**NEGATIVE / BLOCKED. No unique prediction TIFF was generated. There is no file approved to download and submit. No weekly submission slot was used.** This is an incomplete scientific deliverable, not a successful submission build. Producing random dots, changing an old TIFF's name, or quietly dropping uniqueness checks would violate the request.

**Integration update:** remote main subsequently contained synthetic prediction candidates and static scientific claims. These have been audited and withdrawn, with originals preserved outside Pages. See the [critical inherited-main audit](inherited-main-audit.md) on the website (source: `reports/inherited-main-audit.md`). No inherited candidate is a new deliverable from this run.

The starting checkout contained only `README.md` (`# GEMSDOE76`). There was no previous-session code, handoff, training pipeline, cached stack, registry, or data downloader in this checkout. The assertion in the supplied brief that data placement was the single remaining blocker does not describe this repository.

## Evidence and access

The audit recovered the public template modules from [60GEMSDOE at b99591ee](https://github.com/buffedlizard55-lab/60GEMSDOE/tree/b99591eede63c6d45c8a896255b8cd34824fa00b/src/gems57), unmodified. `evidence/upstream/recovery.json` records source commit, exact path, size and SHA256 for each recovered file. We reuse `evaluate_holdout.py`, `holdout.py`, `metric.py`, `submission_writer.py`, and the literal `uniqueness.py`; there is no private evaluator fork. The current template's literal forward-overlap rule, rather than GEMSDOE70's older modified copy, is authoritative for this project.

The public bridge sample/catalogue were recovered from [GEMSDOE70 at 158aec19](https://github.com/buffedlizard55-lab/GEMSDOE70/tree/158aec19800d4c7b8ca9fb94b06567e2b7d61e8d/data/bridge). They are reference inputs, **not submission predictions**. Their origin has not been authenticated against an organizer download. Preflight independently checks their hashes, CRS, dimensions and affine transform. The template's cache receipts describe arrays in `.cache/features60/`, but those arrays are not in this checkout or the public template Git tree. No release assets were returned by the template or GEMSDOE70 release endpoints during this review. Receipts are not data. We did not rebuild substitutes.

`evidence/source_inventory.json` checks the corresponding public GitHub metadata for all named project numbers, using the actual prefix-style names for projects 55–62. This is **not** verification of the deployed Pages sites, all scientific code, or a complete raster comparison. A repository being reachable does not validate its claims. The fresh inventory records timestamps; it is a snapshot, not a continuously running feed.

The environment permits outbound GitHub and package-registry access only. The DrivenData leaderboard, submission page, rules, data tab, USGS/GDR/NLR sites, and Dropbox files could not be directly inspected here. No authenticated organizer receipt or weekly-cap information was available. We did not ask for or store credentials, attempt a competition submission, or claim a live leader.

## H33: what is known and what is not

The prompt reports a leaderboard result for H33, but no authenticated submission-page receipt supports it. All quoted leaderboard values in the original brief remain **USER-REPORTED / UNVERIFIED**, not ORGANIZER-CONFIRMED and not HOLDOUT-DTI. The brief also supplies inconsistent current-leader values; none can establish today's leaderboard.

[The pinned H33 validation source](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/98901f3130e8704f4254f173784589e63f000673/evidence/h33_validation.json), [candidate implementation](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/98901f3130e8704f4254f173784589e63f000673/src/gems32/h33.py), and [later forensic analysis](https://github.com/buffedlizard55-lab/GEMSDOE70/blob/158aec19800d4c7b8ca9fb94b06567e2b7d61e8d/evidence/p8_dual_submod300/h33_forensic_reanalysis.json) support this interpretation: H33 B2 is a sparse subset of the H19-5 → D28 → H27 lineage, with additional near-catalogue dots removed. The later analysis reports that all H33 dots lie on the H19-5 support. These are **inherited analyses**, not a new byte-level reproduction in GEMSDOE76; no archived prediction TIFF was downloaded as a candidate.

The local shared metric uses a triangular kernel with 300 m radius, alpha=0.2 and beta=0.8. Let T be truth coverage, S emitted mass, M nearest-truth kernel credit at emitted cells, and N truth count. Then

`DTI = T / [T + 0.2(S − M) + 0.8(N − T)]`.

Removing a dot can help if the false-positive reduction outweighs lost marginal coverage. Sparse placement can reduce redundant emission; pixel-exact known-fault masking can make near-catalogue placements unhelpful when they do not cover a hidden fault. Neither fact proves that removing any particular band caused an organizer improvement. The physical signal inherited from H19-5 must not be erased from the explanation. H33 is neither evidence of a wholly new learned detector nor proof that geology is irrelevant.

The [official reference notebook](https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/unet-mc-cv-reference-solution.ipynb) confirms fault detection, multi-channel geospatial inputs, U-Net, and Tversky *training loss* with alpha=0.2 and beta=0.8. It does **not** independently verify the full distance-weighted organizer evaluation formula; that must be checked against page 967 when access is available. Do not equate training loss with organizer DTI or geothermal-vent discovery.

Can we beat the user-reported H33 result? It is possible, but this review provides no evidence that a new candidate does so. There is no scientifically defensible projected leaderboard score. Known-catalogue recovery differs from discovering newly mapped faults, and both differ from identifying productive geothermal vents.

## Conditional geological hypotheses — generated before method implementation

These are research proposals, not assigned lanes, not proven globally new, and not viable experiments until input arrays and a lane are supplied. This repository had no prior method. Differences below are relative to the inspected template modules and GEMSDOE70 summaries, **not** an exhaustive claim about every sibling repository. Ordering is a qualitative judgment of potential incremental information, not a projected DTI improvement. No hypothesis was trained, tuned, or evaluated.

| Priority | Hypothesis, specific layers and transform | Missing-fault mechanism | Non-fault mimic and falsifier | Difference / cost / availability |
|---|---|---|---|---|
| A | **Displaced geophysical contacts:** GeoDAWN magnetic anomaly and K, eU, eTh grids. Trace coherent contacts with gradient tensors, then estimate along-contact lateral translation by local cross-correlation on opposing windows; require concordant translation across magnetic and radiometric contacts. | A buried cross-cutting fault could offset an older lithologic contact without a mapped surface scarp. No proximity-to-catalogue prior is needed. | Channel alluvium and survey line-leveling seams can shift apparent contacts. Test channel/flight-line controls, translation sign consistency and source-resolution sensitivity. | Contact *displacement* rather than mere edge strength or coincident gradients in the inspected HGB feature summary. Medium/high implementation cost; expected incremental potential highest but uncertain. Feature rasters/cache absent: **blocked**, no new data acquisition claimed. |
| B | **Paired radiometric depletion with magnetic continuity:** K/eTh and eU/eTh, magnetic anomaly, DEM slope/curvature. Use denominator floors fitted only on training blocks, paired cross-normal profiles and a continuity residual along the magnetic contact. | Fluid alteration along a previously unmapped fracture may deplete mobile K while leaving comparatively immobile Th and an independently constrained contact geometry. | Weathering, transported soils, low-count radiometry and lithology; reject anomalies explained by slope/soil transport or unstable Th denominators. | Paired signed profile residuals rather than generic alteration magnitude; older alteration methods exist, so global novelty is unproven. Medium cost, lower expected specificity than A. Required cached band bytes unavailable: **blocked**. |
| C | **Across-divide drainage disequilibrium:** hydrologically sound USGS 3DEP DEM, template chi, ksn, terminal/drainage identity and channel masks. Contrast signed chi and ksn residuals of paired opposing basins at common outlet/base-level strata, then seek contiguous divide-normal anomalies. | Differential uplift may tilt adjoining small basins before a trace is mapped. | Drainage capture, lithologic contrasts, unequal outlets and climate. Match base levels, exclude closed playas, test lithologic boundaries, use withheld basins as controls. | Divide-pair contrasts, not the template's mainstem knickpoint magnitude or H74 signed channel steps. High cost, substantial confounding. The recovered geomorph receipt routes on **detrended** elevation; do not trust that for hydrologic inference without validation. Official seamless DEM or an authenticated true-DEM cache is necessary: **not presently viable**. |
| D | **Cross-scale contact termination asymmetry:** gravity horizontal gradient plus magnetic analytic-signal/gradient grids and radiometric contacts. Measure whether an edge terminates abruptly at a transverse, cross-sensor-supported discontinuity, controlling local edge strength and background spectral slope. | Fault truncation of a buried lithologic boundary could be visible where the shallow DEM has no scarp. | Intrusive tips, volcanic flow ends and inversion/continuation artifacts; compare polarity, depth sensitivity and synthetic truncation controls. | Contact termination already occurs in GEMSDOE70's earlier lane; only the conditional, cross-scale termination asymmetry is proposed as distinct. Medium/high cost, expected information lowest of these proposals due duplication risk. Required cache missing: **blocked**. |

Official source leads for manual verification: [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [USGS 3DEP](https://www.usgs.gov/3d-elevation-program), [DOE GDR 1391](https://gdr.openei.org/submissions/1391). These are named source leads from the brief/review, not newly verified download availability. No external-data-dependent candidate is represented as viable: this environment cannot check those hosts, and no public official raster was obtained. Free/public hosting alone would not establish competition-rule eligibility.

## Required validation and selection sequence

1. Resolve the **single method lane** in `project.json` through the parallel-run coordinator. Do not select one of the proposals implicitly.
2. Place the template's hash-pinned cache arrays, recover the complete accessible raster registry with hashes and coverage scope, and authenticate reference inputs and external-data eligibility. Respect the existing data ignore rules.
3. Before placement, use template uniqueness checks on the proposed surface. Stop and log duplicate if Spearman exceeds 0.90 or forward positive-support overlap within 3 px exceeds 70% against any registry raster. Continuous positive registry surfaces may make the literal overlap rule impossible to pass; do not invent density exemptions, reverse-overlap clearance, or jitter.
4. Build the shared whole-segment buffered spatial holdout. Derive every catalogue feature from **visible faults only** inside each fold. Do not precompute full-catalogue distances and reuse them after hiding positives. Do not relabel an external proxy as holdout truth.
5. Compute feature-alone AUC canaries on withheld positives with prespecified negative sampling and blocked uncertainty. AUC above 0.90 is a leakage stop pending a documented causal audit. No canary has run in this session.
6. Evaluate a frozen candidate and the reproduced current holdout best on exactly matched folds and budgets with `gems57.evaluate_holdout.evaluate` and `pooled_summary`. Pool additive components, not fold scores; report evaluator version, withheld-positive count and spatial-bootstrap 95% CI. Historical upstream results are not the reproduced local current best.
7. Check uniqueness again on final dots. Compare all registry rasters, record unavailable priors, and stop on duplicate or incomplete access. Do not use byte uniqueness alone.
8. Only after these gates, use the **unmodified shared writer**. Do not clip or silently repair raw scores. Probabilities must already be normalized and finite; explicitly zero the exterior before serialization. Validate the on-disk TIFF/ZIP against the authenticated reference, visible catalogue and footprint, record SHA256, exact name and a comment of at most 140 characters.
9. Promotion to a real submission is a **separate selector step**, requiring a current submission-page cap check and a holdout improvement against the current best. Never automate a slot from a format-only success. Stop after the request's experiment or wall-time budget.

## Irregularities and limitations

- **No method paragraph / lane assignment.** The prompt refers to one but does not identify it.
- **Conflicting leaderboard claims and no receipt.** No ORGANIZER-CONFIRMED score is available; imported JSON retains original unverified claims for audit only.
- **Inherited report inconsistency.** The forensic analysis key-findings prose gives a hidden-truth estimate of approximately 7,500–8,000 with cover about 0.5835, whereas its `uniform_lattice_prevalence_check` fields give cover about 0.3748 and inferred count about 12,649. These are model-dependent inferences, not observed truth counts, and must not calibrate this project without resolving the mismatch.
- **Proxy contamination risk.** SGMC/Quaternary traces can redigitize existing faults. A narrow exclusion band does not establish independent hidden truth.
- **Cache not portable.** Recorded local array paths/hashes do not make the cache downloadable. `recover_inputs.py` recovers only published byte-pinned inputs; it does not fix data placement.
- **Hydrology warning.** Detrended elevation is not interchangeable with true elevation for drainage routing or base-level comparisons.
- **Range error cause unknown.** The portal error can arise from negative/unscaled values, over-one values or nodata handling; no offending file was supplied. Our stricter all-finite [0,1] policy prevents those local data-value failures but is not proof of portal acceptance.
- **No slot cap, eligibility, license or rules authentication.** These require official access. No password/token should be posted in chat.
- **No exhaustive line-by-line scientific validation of all 78 projects.** We verified repository metadata and a pinned subset of code/evidence; reporting more would be misleading.
- **No successful unique TIFF.** This central user goal remains blocked; the site does not disguise the failure with a sample or copied TIFF.

## Three-pass review

Pass 1: repository inspection, source snapshots, pinned shared-tool recovery, reference-grid audit, preflight, research/requirements documentation and Pages implementation.

Pass 2: software regression checks for range rejection, NaN/Inf, grid mismatch, catalogue overlap, literal forward-overlap gates, pooled evaluator consistency, modified pins and missing data. These are synthetic **software tests**, not geological experiments or HOLDOUT-DTI evidence.

Pass 3: rerun the complete suite and reproducibility checks; verify no predictive artifact, stale claim of approval, external credentials, private evaluator fork or submission action was introduced. Exact command outcomes belong in `evidence/verification.json` and the handoff.

## Next session, in order

Resolve the lane; make the shared cache portable at a pinned immutable location without rebuilding; authenticate competition inputs/rules; refresh the full scoped raster registry; preregister one eligible hypothesis; reproduce current best and canaries; run at most three experiments within two hours; generate only if gates pass. If any shared tool is wrong, fix it in the template via an upstream issue/PR, not here. No shared-tool bug requiring a patch was established in this review.
