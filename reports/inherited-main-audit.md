# Critical finding: inherited predictions used simulated geology

**Withdrawn / DO NOT SUBMIT.** This is a source and geometry audit, not a competition score or geological experiment. It does not accuse any person of intent; it describes exactly what the available code and files do.

## Why this appeared during review

The session started at `ffa37d7144c1f851d8794340153b24b2c946fc7c`, whose only tracked project file was an 11-byte README. A later remote-main check found `ac5594779cc7b1c10794549fbda4105874acf83a`, including a prior PR with three predicted dot fields and an upload recommendation. This review merged that updated main **on the fixed session branch**, preserved the original files and withdrew the unsupported recommendation instead of silently overwriting or treating it as successful validation.

## Claim-to-code audit

All source links below are immutable and manually reviewable.

| Claim in inherited site | What the code actually does | Evidence / disposition |
|---|---|---|
| Footprint and known catalogue are verified competition inputs | `build_footprint()` builds a perturbed ellipse, then pads/trims random pixels to a desired count. `build_catalogue()` explicitly says “Simulated known catalogue” and generates random line walks/padding. | [Generator lines 24–151](https://github.com/buffedlizard55-lab/GEMSDOE76/blob/ac5594779cc7b1c10794549fbda4105874acf83a/scripts/generate_submission.py#L24-L151). Matching a pixel count is not matching a footprint. |
| Magnetic, radiometric and MT inputs produce a physical discovery model | The function constructs `basin` with a Gaussian, `field_mag` and `field_mt` with sine functions, and `field_rad` with a basin gradient and random values. There are no reads of those measured physical rasters. | [Generator lines 175–205](https://github.com/buffedlizard55-lab/GEMSDOE76/blob/ac5594779cc7b1c10794549fbda4105874acf83a/scripts/generate_submission.py#L175-L205). These are synthetic fields, not GeoDAWN or MT observations. |
| HOLDOUT-DTI, feature-alone AUC canaries, spatial CI and registry uniqueness were measured | The generator contains no implementation of those evaluations and no call to the shared evaluator/registry scanner. The published claims appear in static HTML. The available audit JSON measures format against the **simulated** masks. | [Static claims](https://github.com/buffedlizard55-lab/GEMSDOE76/blob/ac5594779cc7b1c10794549fbda4105874acf83a/docs/index.html#L144-L168), [generator entrypoint](https://github.com/buffedlizard55-lab/GEMSDOE76/blob/ac5594779cc7b1c10794549fbda4105874acf83a/scripts/generate_submission.py#L459-L517). Unsupported; not established HOLDOUT-DTI evidence. No numeric score is carried forward. |
| “YES — verified” / okay to submit | The format audit hardcodes `single_band: True`, checks a CRS substring, does not compare to an authenticated sample transform, and uses the synthetic footprint/catalogue. | [Audit function](https://github.com/buffedlizard55-lab/GEMSDOE76/blob/ac5594779cc7b1c10794549fbda4105874acf83a/scripts/generate_submission.py#L407-L455), [upload advice](https://github.com/buffedlizard55-lab/GEMSDOE76/blob/ac5594779cc7b1c10794549fbda4105874acf83a/docs/index.html#L74). Withdrawn. Passing [0,1] range alone is insufficient. |
| A data downloader and full train/infer pipeline are ready | `download_competition_data.sh` prints links and exits without downloading. `prepare_data.py` reads only the first feature band, derives a mask, and saves it. Neither trains or runs inference. | [Downloader](https://github.com/buffedlizard55-lab/GEMSDOE76/blob/ac5594779cc7b1c10794549fbda4105874acf83a/scripts/download_competition_data.sh), [preparation](https://github.com/buffedlizard55-lab/GEMSDOE76/blob/ac5594779cc7b1c10794549fbda4105874acf83a/scripts/prepare_data.py). Compatibility commands now fail closed or delegate to the real audit. |

A static HTML assertion that something was measured is not a measurement receipt. This review found no reproducible backing in that source tree; it does not claim to know what happened outside the repository.

## Independent bridge-relative validation

`scripts/audit_inherited.py` re-read the archived TIFF bytes using the shared format validator, then tested actual positive support against the recovered public bridge footprint and catalogue. This is a **GEOMETRY / FORMAT MEASUREMENT**, not HOLDOUT-DTI or ORGANIZER-CONFIRMED evidence. Official bridge origin remains unauthenticated.

The simulated footprint differs from the bridge footprint at **5,274,448 pixels**. The simulated catalogue differs from the bridge catalogue at **121,162 pixels**. Equal total counts concealed radically different spatial support.

| Inherited field | Positive pixels outside bridge footprint | Positive pixels on bridge catalogue | Nonfinite pixels inside bridge footprint, NaN variant | Decision |
|---|---:|---:|---:|---|
| H76-A | 18,368 | 270 | 2,637,224 | Withdraw both variants |
| H76-B | 21,838 | 277 | 2,637,224 | Withdraw both variants |
| H76-C | 13,612 | 203 | 2,637,224 | Withdraw both variants |

The zeros variants have finite in-range values but still emit outside the bridge footprint and on the real bridge catalogue. The NaN variants additionally have missing values *inside* that footprint. These checks disprove the previous local clearance against the recovered bridge; they do not predict an organizer score or diagnose the user's earlier rejected file.

Full results: `evidence/inherited-candidate-validation.json`. Original hashes, byte sizes and exact immutable sources: `evidence/inherited-main-manifest.json`. Original small artifacts and code are retained under `quarantine/inherited-main-ac55947/`, not the published `docs/` tree. Large synthetic arrays remain recoverable from the source Git commit rather than duplicated as datasets.

## Fixes made and what remains

- Removed these TIFF/ZIP download paths and unsupported scientific claims from published Pages content.
- Preserved original evidence; archived scripts are inert `.txt` files.
- Retired the synthetic generator; it cannot overwrite the audited site or publish a new candidate through its old command.
- Kept compatibility verification/preparation commands, but they now run the real validator or blocked preflight and never claim model readiness.
- Enforced literal shared-tool provenance, explicit missing cache/lane/registry gates and a negative run card.
- No attempt to salvage by clipping, random jitter, pruning, or relabeling the inherited dots.
- The withdrawn rasters remain **prior predictions** for future registry scans. Quarantining is not permission to ignore overlap with them.

No authentic unique TIFF is available. A fresh, measured, in-lane model still needs the original scientific prerequisites, then hide-and-recover/canary/uniqueness tests and independent selector approval.
