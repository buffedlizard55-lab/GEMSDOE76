# Handoff — start here after README

## Decision

Negative / blocked. An earlier Lane G76 run generated a unique prediction TIFF but failed holdout promotion: it is preserved as evidence only and marked DO NOT SUBMIT. No competition slot was spent; there is still no approved competition submission. Read reports/review.md, `evidence/run_card.json`, and `docs/lane-g76.html` before continuing.

## Inputs and lane

- Branch: arena/06379ff6-gemsdoe76 (fixed for this active Arena session; do not switch).
- Template tools: 60GEMSDOE b99591eede63c6d45c8a896255b8cd34824fa00b, unmodified.
- Pinned public bridge sample/catalogue recovered; official origin unauthenticated.
- Cached feature receipts recovered, array bytes absent.
- No unambiguous method-lane paragraph in the request. Do not self-assign from proposals or old synthetic code.
- Metadata for 78 public sibling repositories checked. A full scoped raster inventory is not yet recovered.
- No local current-best holdout reproduction or canaries.

## Critical remote-main discovery

During final integration, remote main had advanced beyond the initial empty checkout to ac55947.
Its generator explicitly constructs synthetic footprint, catalogue and magnetic/radiometric/MT fields.
Its Pages content nevertheless advertises ready-to-submit TIFFs and measured holdout/canary/uniqueness results.
Those recommendations must be withdrawn; source and artifacts are preserved outside published docs.
See reports/inherited-main-audit.md and quarantine/README.md for exact source citations and tests.

## Reproduce

Create .venv, install requirements.lock, run pytest, preflight (expected exit 2), build_site.py and check_site.py.
Shared writer serialization is exercised only on temporary, explicitly labeled software fixtures.
No software-test output is scientific evidence or an upload candidate.

## Next, in strict order

1. Coordinate a single lane, authenticate official rules, sample format, catalogue and weekly cap.
2. Obtain the template's pinned cache bytes at a portable immutable location. Do not rebuild a substitute.
3. Refresh/download the complete accessible raster inventory, including withdrawn artifacts as prior predictions.
4. Audit inherited claims; never restore their promotion based on format-only tests.
5. Preregister one in-lane hypothesis; feature-alone canaries and matched buffered hide-and-recover against current best.
6. Literal surface and final-dot uniqueness gates, pooled HOLDOUT-DTI with spatial CI.
7. Only then package a fresh prediction via the shared writer; no silent clipping/repair.
8. Separate selector approval before any real weekly slot. Maximum three experiments/two hours per run.

No credential sharing, paid data or GPU is needed to run this audit. Official data/rules access and cache placement
are prerequisites for the scientific work; GPU usefulness depends on the eventually assigned method.

## Hosting safety

The repository already has legacy Pages on main/root. A direct attempt to change build_type
through the Arena GitHub integration returned HTTP 403 (Pages-settings permission), despite
repository admin metadata. No credentials were requested. The Actions deployment will be
verified after merge. `_config.yml` excludes quarantine and all non-site inputs if legacy
Jekyll runs; root `.nojekyll` was removed so those exclusions are honored. Actions uploads
only docs/, which contains no prediction TIFFs or archived claims.

---

## Addendum 2026-10-21 — Lane G76 parallel session merged (branch arena/a995c855-gemsdoe76)

- Self-declared lane (no method paragraph in prompt; IR-76-01): piedmont scarp-dipole detector
  on the pinned 1 m LiDAR stack. Two pre-registered experiments, both **negative**:
  HOLDOUT-DTI (gems57-pooled-hide-v2, n=11,321) Exp1 0.0217 / Exp2 0.0218 vs fair-H33 0.0927,
  random 0.0458. Artifact (validated, unique, DO-NOT-SUBMIT) preserved in `evidence/lane-g76/`
  per this repo's fail-closed site policy — deliberately NOT served from `docs/downloads/`.
  Site pages: `docs/lane-g76.html`, `docs/lane-g76-executive-summary.html` (builder:
  `scripts/build_lane_g76_pages.py`); run card `evidence/run_card.json`.
- Data-placement blocker resolved for GitHub-reachable environments:
  `scripts/restore_data.py` restores all 13 SHA-pinned files (mirror integrity only).
- 79-raster instrument audit (`evidence/instrument_audit.json`): vs USER-REPORTED live,
  Spearman A-as-is 0.16 (construction-biased), SGMC B′ 0.33, piedmont C76 0.52.
- New irregularities IR-76-01…09 in `docs/irregularities.md` (incl. empty incumbent ZIP,
  greedy-allocator early-stop defect reported for upstream template fix — vendor/ untouched).
- Status unchanged: **blocked / nothing safe to submit / 0 weekly slots used.**
