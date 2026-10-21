# GEMSDOE76 Preregistration Amendment — Experiment 2

**Written 2026-10-21 after Experiment 1 completed, before any Exp-2 score was computed.**
This amendment is part of the frozen record; Exp 1's negative result stands unmodified
(`evidence/exp1/`).

## What Exp 1 falsified (measured, HOLDOUT-DTI gems57-pooled-hide-v2, n=11,321)

- Candidate dots 0.02171 [0.01370, 0.03026] vs fair-H33 0.09269 [0.08018, 0.10585] vs
  count-matched random 0.04577 [0.04014, 0.05120]. Paired Δ vs fair-H33 = −0.07097
  [−0.08601, −0.05641]. Proxies B′/C76-pied agree (candidate below random).
- Diagnostics (training catalogue only): every component's catalogue-vs-far-field contrast is
  ≤1.42× in means and ≤0.631 in AUC; `coh100` alone is 0.488; `face−cross` is negative almost
  everywhere (channel-bank energy dominates the polarity contrast I hypothesised);
  max-pooled 2 m→100 m bands are saturated by ubiquitous micro-topography.
- Secondary defect: the shared greedy allocator's candidate cap (250k) saturated at 26,414 of
  37,654 requested dots on the diffuse rank surface — an emission-pool artifact, not the cause
  of the negative (per-dot efficiency was ~3× worse than random).

**Conclusion:** the frozen *hand-set multiplicative combiner* is falsified. The lane's physical
question — whether the LiDAR scarp-dipole feature family carries expert-fault information — is
not yet answered, because a rank-product is the weakest possible combiner for correlated weak
fields. Exp 2 therefore changes **only the combiner** (plus the emission-pool cap), keeping the
lane's exact feature family, gates, instruments and budget. It is counted as Experiment 2 of 3.
If Exp 2 also fails the promotion gate, the lane is closed as a negative result; no Exp-3
transform search will be run (Exp 3 is reserved as untouched confirmation of a passing Exp 2).

## Exp 2 frozen configuration

- **Features (lane family only, no geophysics, no catalogue-derived inputs):**
  `step_max`, `dipole=sqrt(lapneg·lappos)`, `dipole/(ex_mean+0.01)`, `polarity`, `coh100`,
  `ex_mean`, `persisted` (strike-smoothed step·dipole), `fallback` response, `has_lidar`
  indicator. Relief enters as a *feature* (`relief`, NaN→domain median) instead of Exp 1's hard
  piedmont gate, so the combiner — not a hand threshold — decides how relief modulates the
  dipole evidence. Non-LiDAR cells get LiDAR-feature values of 0 with `has_lidar=0` (declared
  missingness encoding).
- **Combiner:** L2 logistic regression (`sklearn`, C=1.0, lbfgs, class_weight=None) on
  features standardized by visible-domain median/IQR. Training positives: visible-catalogue
  pixels; negatives: fixed-seed sample (10× positives, cap 600k) from valid domain excluding
  the full catalogue and excluding withheld components (both withheld pixels themselves are
  already catalogue pixels, hence excluded by the catalogue exclusion). One model per holdout
  draw (the draw's hidden set is global across its 4 folds), trained only on that draw's
  `visible` mask; final model trained on the full catalogue.
- **Emission:** shared greedy 300 m allocator on predicted probability, `candidate_cap=600,000`,
  budget-matched 37,654 dots; holdout arms exclude `masked_known` pixels; final dots apply the
  B=2 px full-catalogue flank exclusion. No other change.
- **Gates:** identical to the original preregistration §3 (Instrument A seed-20 paired CI > 0
  vs fair-H33; canaries ≤0.90 — now also computed for the fitted probability; B′/C76 reported;
  uniqueness and validator gates before any promotion language).
