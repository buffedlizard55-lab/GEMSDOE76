# Operative prompt for GEMSDOE76 (read at the start of every session)

> Stored per the project owner's instruction: "Put this prompt into the repo readme and read it
> everytime we work on the project." This file preserves the operative requirements verbatim in
> substance; the long per-site score list from the original message is distilled, with hashes,
> into `docs/score-ledger.csv` and `evidence/instrument_audit.json`.

## Highest urgency

MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A PREVIOUS SUBMISSION
UNLESS IT'S FOR LEARNING AND EDUCATION. IT MUST BE OBVIOUS WHETHER IT IS OK TO DOWNLOAD AND
SUBMIT THE GENERATED TIF SUBMISSION. There should be an easy-to-download submission TIF file
as described by the prompt. Read the entire prompt.

## PARALLEL-RUN PROTOCOL

1. **LANE.** Your lane is the single method paragraph below. Stay inside it. If your raster's
   rank-correlation with any registry raster exceeds 0.90, or more than 70% of your dots fall
   within 3 px of one registry raster's dots, you have drifted into another lane: log it as a
   duplicate and stop. Check this on the surface before placement AND on the final dots.
   *(GEMSDOE76 note IR-76-01: no lane paragraph was present in the supplied prompt; the lane
   was self-declared in `docs/preregistration-g76.md`. Overlap is reported forward/reverse/
   mutual; mutual ≤0.70 is the operative gate because the dense calibration lattice's 3 px halo
   covers ~99.9% of the footprint — disclosed, following GEMSDOE70-P8.)*
2. **REUSE, DON'T REBUILD.** Use the template's cached feature stack, `evaluate_holdout.py` and
   `submission_writer.py`. Holdout = hide-and-recover: withhold whole fault segments with a
   buffer, derive every catalogue-based feature only from the visible faults, mask visible
   faults pixel-exactly, score pooled DTI (alpha 0.2, beta 0.8, 300 m triangular kernel). If a
   shared tool is wrong, fix it once in the template and report it; never keep a private fork.
3. **LABEL EVERY NUMBER** as HOLDOUT-DTI (evaluator version, number of withheld positives,
   95% CI) or ORGANIZER-CONFIRMED (copied from a submission-page receipt). A projection is
   never written as a score.
4. **LEAKAGE CANARY.** Test each feature alone on the holdout before trusting any result.
   AUC above 0.90 means leakage until proven otherwise.
5. **RUN CARD.** End with one JSON card: hypothesis; mechanism; the named non-fault process
   that could mimic it; holdout DTI + CI; correlation/overlap vs registry; raster sha256;
   validator output (no NaN inside the footprint, values in [0,1], CRS/shape/transform match);
   submission name + note of at most 140 characters; verdict promote / negative. Negative
   results are deliverables.
6. **BUDGET.** Stop after 3 experiments or 2 hours. Do not pick submissions: promotion to a
   real slot is a separate selector step, within the weekly cap shown on the submission page.

## Standing research requirements

- Before implementing, generate 3–5 candidate geological hypotheses not yet tried, each naming
  the layer(s), the physical signature/transform, why it catches faults missing from the
  USGS/INGENIOUS catalogue, and how it differs from anything already implemented. Rank by
  expected DTI improvement and cost. Validate the top candidate on the spatially-blocked
  holdout before touching a weekly slot. If a candidate needs new external data, name the
  specific free official source and check it is obtainable first.
- Study why the family's best file (`h33-h33-2-b2-…-zeros`, USER-REPORTED 0.2778, GEMSDOE32)
  scored highest, with PhD-level judgement, then use the answer. Current public-leaderboard
  high: 0.4413 (verified 2026-10-21).
- Work line by line verifying from official verified trusted sources; provide links for manual
  review; no manual input; flag irregularities; no hallucinations.
- The site must make the submission file and its submit/do-not-submit status obvious at the
  very beginning (executive summary). The historical portal error "Predicted values must be in
  range [0, 1]" must be engineered out. Every submission gets a unique name and a short
  distinguishing note. Create an executive-summary subpage explaining exactly how to submit.
- Competition: https://www.drivendata.org/competitions/306/competition-doe-gems/ (problem
  p.967, about p.968, data tab requires login). Reference solution:
  https://github.com/drivendataorg/gems-prize-reference-solution. Rules PDF:
  https://docs.nlr.gov/docs/fy26osti/96647.pdf. USGS GeoDAWN:
  https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and
  INGENIOUS: https://gbcge.org/current-projects/ingenious/ · EPSG:32611 https://epsg.io/32611
  · Tversky index https://en.wikipedia.org/wiki/Tversky_index · GDR #1391
  https://gdr.openei.org/submissions/1391
- Multi-pass discipline: Pass 1 implement+verify; Pass 2 review for bugs/missing requirements/
  edge cases and fix; Pass 3 re-check against the original request and fix what remains. Then
  create a pull request and merge it into main; list remaining work and limitations.

## Core values (Arena AI team, adopted by the owner)

**Maximize P(Win)** — in every decision, weigh tradeoffs, assess risk, and choose the path
that maximizes the probability of success; set aside emotions and make tough decisions to
maximize P(Win). **Own the Outcome** — own results end to end; when problems arise and we have
the means to act, do so without waiting for permission; treat failure and success as signals
and use them to improve; stay accountable to the final outcome.
