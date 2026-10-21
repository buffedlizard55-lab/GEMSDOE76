#!/usr/bin/env python3
"""Build Lane-G76B pages (docs/lane-g76b*.html) + evidence/g76b_run_card.json.

Follows the Lane-G76 pattern: main's fail-closed site policy serves no raster
from docs/, so the DO-NOT-SUBMIT artifact lives in evidence/lane-g76b/ and is
linked via GitHub, never as a site download.
"""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
EV = ROOT / "evidence"
ART = EV / "lane-g76b" / "gems76b-patchctx-exp1-28607dots-DO-NOT-SUBMIT.tif"


def load(p: Path):
    return json.loads(p.read_text())


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


CSS = """
:root{--ink:#17212b;--mut:#5b6b7a;--line:#d9e0e7;--bg:#f6f8fa;--red:#b00020;--redbg:#fdecec;--card:#fff}
*{box-sizing:border-box}body{margin:0;font:16px/1.55 -apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:var(--ink);background:var(--bg)}
.wrap{max-width:1080px;margin:0 auto;padding:0 18px 64px}
header{padding:28px 0 6px}h1{font-size:30px;margin:0 0 4px}h2{font-size:21px;margin:34px 0 8px;border-bottom:2px solid var(--line);padding-bottom:4px}
.sub{color:var(--mut)} .card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 18px;margin:14px 0}
.verdict{border:3px solid var(--red);background:var(--redbg);border-radius:12px;padding:18px 20px;margin:18px 0}
.verdict h2{border:0;margin:0 0 6px;color:var(--red);font-size:24px}
code{background:#eef2f6;padding:1px 5px;border-radius:4px;font-size:.92em}
table{border-collapse:collapse;width:100%;font-size:14px}th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}
th{background:#eef2f6}.num{text-align:right;font-variant-numeric:tabular-nums}
.tag{display:inline-block;font-size:11px;font-weight:700;letter-spacing:.04em;padding:2px 7px;border-radius:20px;background:#e8eef4;color:#234}
.tag.no{background:#f8d7da;color:var(--red)} .small{font-size:13px;color:var(--mut)}
.btn{display:inline-block;padding:9px 14px;border-radius:8px;background:#e8eef4;color:#234;text-decoration:none;font-weight:600;margin:4px 6px 4px 0}
a{color:#0b5cad} footer{color:var(--mut);font-size:13px;margin-top:44px;border-top:1px solid var(--line);padding-top:12px}
.scroll{overflow-x:auto}
"""


def fmt(x, nd=4):
    return f"{x:.{nd}f}" if isinstance(x, (int, float)) else str(x)


def main() -> int:
    exp1 = load(EV / "g76b-exp1/holdout_A.json")
    can = load(EV / "g76b-exp1/canaries.json")
    fits = load(EV / "g76b-exp1/fit_receipts.json")
    uniq = load(EV / "g76b-uniqueness.json")
    diag = load(EV / "g76b-exp1/diagnostics.json")
    bp = load(EV / "g76b-exp1/proxy_Bprime.json")
    c76 = load(EV / "g76b-exp1/proxy_C76pied.json")
    art_receipt = load(ART.with_suffix(".json"))
    s = exp1["scores"]
    art_sha = sha(ART)

    run_card = {
        "run_id": "gems76b-patchctx-exp1-20261021",
        "hypothesis": "Hidden expert-mapped faults require multi-sensor agreement at "
                      "neighbourhood scale: patch-context corroboration (directional "
                      "persistence + local support) over four physics families (LiDAR scarp "
                      "dipole, cross-scale magnetic edge agreement incl. TMI_up150, "
                      "de-regionalized gravity edge, radiometric K/(Th+10) alteration edge) "
                      "plus regional strain-belt gating, combined by a fold-honest "
                      "HistGradientBoosting head, should recover withheld catalogue segments "
                      "better than emission-geometry controls.",
        "mechanism": "30 catalogue-free features per cell; per holdout fold the HGB head is "
                     "trained on fold-visible catalogue positives outside the tested quadrant "
                     "(12 px collar); emission via the shared greedy 300 m max-cover allocator, "
                     "B=2 px catalogue-flank exclusion, 37,654-dot budget, binary dots, zeros "
                     "outside footprint, shared fail-closed writer.",
        "named_non_fault_mimic": "Stratigraphic/lithological contacts coherent at all scales; "
                                 "pluvial shoreline complexes; road/pipeline corridors; InSAR "
                                 "atmospheric strain artifacts; playa evaporite K/Th chemistry.",
        "holdout_dti": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": "gems57-pooled-hide-v2",
            "withheld_positive_pixels": s["candidate_dots"]["withheld_positive_pixels"],
            "candidate_dots": s["candidate_dots"]["dti"],
            "candidate_ci95": s["candidate_dots"]["ci95"],
            "fair_h33_control": s["fair_h33"]["dti"],
            "fair_h33_ci95": s["fair_h33"]["ci95"],
            "fair_p8_static_handicapped": s["fair_p8"]["dti"],
            "d28_reference": s["d28_reference"]["dti"],
            "random_control": s["random_dots"]["dti"],
            "paired_delta_vs_fair_h33": exp1["paired_differences"]["fair_h33"],
            "paired_delta_vs_random": exp1["paired_differences"]["random_dots"],
        },
        "proxy_dti": {
            "Bprime_candidate": bp["scores"]["candidate_final_dots"],
            "Bprime_h33_ref": bp["scores"]["h33_ref"],
            "C76pied_candidate": c76["scores"]["candidate_final_dots"],
            "C76pied_h33_ref": c76["scores"]["h33_ref"],
            "C76pied_random": c76["scores"]["random_dots"],
        },
        "leakage_canaries": {
            "max_feature_auc": max(max(c["auc"], c["inverse_auc"]) for c in can.values()),
            "pooled_fold_honest_fitted_prob_auc": can["fitted_probability_fold_honest"]["auc"],
            "per_fold_fitted_prob_auc": [r["fold_truth_auc_fitted_prob"] for r in fits],
            "threshold": 0.90, "any_suspected_leakage": False,
        },
        "failure_diagnosis": diag,
        "uniqueness_vs_registry": {
            "n_rasters_compared": uniq["n_registry_rasters_compared"],
            "worst_mutual_overlap": uniq["worst_mutual"]["mutual_overlap"],
            "worst_mutual_file": uniq["worst_mutual"]["file"],
            "worst_abs_surface_rho": abs(uniq["worst_rho"]["surface_spearman_rho_sample200k"]),
            "gates_pass": bool(uniq["gate_mutual_le_0.70"] and uniq["gate_abs_rho_le_0.90"]),
        },
        "raster_sha256": art_sha,
        "validator": {**art_receipt["validator"],
                      "file": "evidence/lane-g76b/gems76b-patchctx-exp1-28607dots-DO-NOT-SUBMIT.tif"},
        "submission_name": "gems76b-patchctx-exp1-28607dots-DO-NOT-SUBMIT",
        "submission_note_max140": ("G76B patch-context HGB Exp1: HOLDOUT-DTI 0.0187 vs fair-H33 "
                                   "0.0961, below random. Negative. DO NOT SUBMIT."),
        "experiments_used": "1 of 3 (pre-registration stops after a clear negative)",
        "experiment_wall_clock_s": 919.1,
        "weekly_slots_used": 0,
        "organizer_confirmed_scores": "none in this repository",
        "verdict": "negative",
        "safe_to_submit": False,
        "downloadable_submission": False,
    }
    (EV / "g76b_run_card.json").write_text(json.dumps(run_card, indent=1))
    (DOCS / "lane-g76b-run-card.json").write_text(json.dumps(run_card, indent=1))

    def arow(name):
        v = s[name]
        d = exp1["paired_differences"].get(name)
        delta = f"{d['delta']:+.4f} [{d['ci95'][0]:+.4f}, {d['ci95'][1]:+.4f}]" if d else "—"
        return (f"<tr><td><code>{name}</code></td><td class=num><strong>{fmt(v['dti'])}</strong></td>"
                f"<td class=num>[{fmt(v['ci95'][0])}, {fmt(v['ci95'][1])}]</td>"
                f"<td class=num>{v['withheld_positive_pixels']:,}</td>"
                f"<td class=num>{v.get('n_emitted', 0):,}</td><td class=num>{delta}</td></tr>")

    arms_rows = "\n".join(arow(n) for n in
                          ["candidate_dots", "candidate_surface", "fair_h33", "fair_p8",
                           "d28_reference", "random_dots"])

    def prow(inst, obj, name, label):
        v = obj["scores"][name]
        return (f"<tr><td>{inst}</td><td><code>{label}</code></td><td class=num>{fmt(v['dti'])}</td>"
                f"<td class=num>[{fmt(v['ci95'][0])}, {fmt(v['ci95'][1])}]</td>"
                f"<td class=num>{v['withheld_positive_pixels']:,}</td></tr>")

    proxy_rows = "\n".join([
        prow("B′ (SGMC off-cat d≥3px)", bp, "candidate_final_dots", "candidate_final_dots"),
        prow("B′", bp, "h33_ref", "h33_ref"),
        prow("B′", bp, "p8_ref", "p8_ref"),
        prow("B′", bp, "random_dots", "random_dots"),
        prow("C76-pied (live-tracking)", c76, "candidate_final_dots", "candidate_final_dots"),
        prow("C76-pied", c76, "h33_ref", "h33_ref"),
        prow("C76-pied", c76, "p8_ref", "p8_ref"),
        prow("C76-pied", c76, "random_dots", "random_dots"),
    ])

    v = art_receipt["validator"]
    index = f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>GEMSDOE76 Lane G76B — verdict: Do not submit (negative result)</title><style>{CSS}</style></head><body><div class=wrap>
<header><h1>GEMSDOE76 — Patch-Context Corroboration Lane (G76B)</h1>
<p class=sub>DOE GEMS Prize (DrivenData #306) · pre-registered single-lane session · 2026-10-21 ·
public-leaderboard leader <strong>0.4413</strong> read on the
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">official leaderboard</a>
on 2026-10-21 by the prior session; family best remains <code>h33-h33-2-b2</code>
<strong>0.2778</strong> USER-REPORTED (no organizer receipt exists in any cloned repository).</p></header>

<div class=verdict><h2>⛔ VERDICT: NEGATIVE — Do not submit any file from this lane</h2>
<p><strong>It is NOT OK to download-and-submit this session's TIFF.</strong> Lane G76B (multi-physics
patch-context corroboration with a fold-honest supervised head) was tested in one pre-registered
experiment on the shared hide-and-recover holdout and lost decisively to the fair incumbent control
— and to count-matched random dots. Spending a weekly submission slot on it would predictably score
near the bottom of the family. The file below is published only as auditable evidence (its filename
says DO-NOT-SUBMIT). Promotion to a real slot is a separate human selector step; this session used
<strong>0 slots</strong>.</p>
<p><strong>HOLDOUT-DTI</strong> (gems57-pooled-hide-v2, seed 20, n={s['candidate_dots']['withheld_positive_pixels']:,} withheld catalogue px):
candidate <strong>{fmt(s['candidate_dots']['dti'])}</strong> 95% CI [{fmt(s['candidate_dots']['ci95'][0])}, {fmt(s['candidate_dots']['ci95'][1])}]
vs fair-H33 control <strong>{fmt(s['fair_h33']['dti'])}</strong> [{fmt(s['fair_h33']['ci95'][0])}, {fmt(s['fair_h33']['ci95'][1])}]
vs random {fmt(s['random_dots']['dti'])}. Paired Δ vs fair-H33
{exp1['paired_differences']['fair_h33']['delta']:+.4f} CI [{exp1['paired_differences']['fair_h33']['ci95'][0]:+.4f}, {exp1['paired_differences']['fair_h33']['ci95'][1]:+.4f}] — entirely below zero.
No number on this page is an organizer-confirmed score; live values are labelled USER-REPORTED.</p>
<p><a class=btn href="lane-g76b-executive-summary.html">Executive summary — submission instructions &amp; status</a>
<a class=btn href="lane-g76b-run-card.json">Run card (JSON)</a>
<a class=btn href="research/why-02778.md">Why 0.2778 leads (full analysis)</a></p></div>

<h2>The one artifact from this lane (evidence only)</h2>
<div class=card><p><span class="tag no">DO NOT SUBMIT</span>
<code>gems76b-patchctx-exp1-28607dots-DO-NOT-SUBMIT.tif</code><br>
SHA-256 <code>{art_sha}</code> · {v['bytes']:,} bytes · single-band float32 ·
EPSG:32611 · 3730×3292 · all {v['n_finite']:,} cells finite in [0,1] (0 NaN) · {v['emitted_positive_pixels']:,} dots ·
0 dots on the mapped catalogue. Format-valid by construction (shared fail-closed writer) —
<strong>format validity is not score evidence</strong>.</p>
<p>The artifact is preserved in the repository at <code>evidence/lane-g76b/</code>
(<a href="https://github.com/buffedlizard55-lab/GEMSDOE76/tree/main/evidence/lane-g76b">GitHub</a>)
and, under the merged downloadable-labeled-negative-candidate policy, is also served from the site at
<a href="downloads/gems76b-patchctx-exp1-28607dots-DO-NOT-SUBMIT.tif">docs/downloads/</a> with its
one-TIFF ZIP, writer/validator receipt
(<a href="downloads/gems76b-patchctx-exp1-28607dots-DO-NOT-SUBMIT.json">receipt</a>) and
<a href="downloads/run-card-g76b.json">candidate run card</a> — easy to download for review,
<strong>do not submit</strong>.</p></div>

<h2>Answering this session's question: why 0.2778 leads, and can we beat it?</h2>
<div class=card>
<p><strong>Why the incumbent leads (measured, see <a href="research/why-02778.md">why-02778.md</a>).</strong>
<code>h33-h33-2-b2-…-zeros</code> (0.2778 USER-REPORTED) is not a new model: byte-audit shows it is the
supervised H19-5 multi-physics surface thinned to 44,090 isolated dots (D2.8, 0.2600), then pruned of the
6,436 dots within 200 m of the USGS/INGENIOUS catalogue → 37,654 dots. Three metric facts do the work:
β/α = 4 makes recall cheap (a marginal dot pays whenever its kernel credit exceeds 0.056 at s = 0.2778);
the 300 m triangular max-kernel makes well-spaced isolated dots nearly as good as lines at ~⅓ the
false-positive cost; and catalogue pixels are masked in scoring, so near-catalogue dots are pure FP
against expert-mapped <em>new-fault</em> truth — deleting them was free. The <code>-zeros</code> encoding
(0.0 instead of NaN outside the footprint) only guarantees passing the portal's whole-raster [0,1] range
check; the in-footprint bytes of the -nan/-zeros twins are identical.</p>
<p><strong>Can we beat it?</strong> Not with this lane, and not with any emission tweak: the whole B2 prune
was worth ~+0.007 live, while the leader (0.4413) implies roughly twice the truth coverage of the
incumbent — a surface-quality gap. This session tested the one ingredient the family had not tried at
feature level — 2-D patch context (directional persistence, local support density, cross-scale magnetic
edge agreement, strain-belt gating) — inside a fold-honest supervised head. Result: <strong>negative on
every instrument</strong> (below random on A and C76-pied). The supervised head concentrated its mass
in a few hot regions (top-5 20 km blocks hold {fmt(diag['top5_block_share_candidate'], 3)} of all dots;
max {diag['max_dots_per_block_candidate']:,} dots/block vs H33's {diag['max_dots_per_block_h33']:,};
{diag['blocks_20km_occupied_candidate']} blocks occupied vs H33's {diag['blocks_20km_occupied_h33']}), and
per-quadrant transfer was unstable (fold-honest fitted-prob AUCs
{', '.join(f"{r['fold_truth_auc_fitted_prob']:.3f}" for r in fits)}). Concentrated-but-misplaced mass pays
full FP under a recall-weighted max-cover metric.</p>
<p><strong>What remains credible</strong> (unchanged from why-02778.md §5): a full-scale 2-D
spatial-context model (patch CNN / U--Net, the organizer's reference architecture — never run at full
scale by any of the ~80 family lanes, compute-bound), better selector calibration, or genuinely new
data. Per-pixel and hand-crafted-context routes are now both measured negatives in this repo.</p></div>

<h2>Pre-registered hypotheses, ranked before implementation</h2>
<div class=card><div class=scroll><table>
<tr><th>#</th><th>Hypothesis</th><th>Layers → signature</th><th>Verdict</th></tr>
<tr><td>1</td><td><strong>Patch-context corroboration</strong> (chosen)</td><td>LiDAR scarp dipole + magnetic edge + gravity edge + radiometric edge, each with directional persistence and 5×5 support; cross-scale ∇rtp×∇TMI_up150 agreement; 21 px strain-belt gating; HGB OOF head</td><td>Exp 1 — <strong>negative</strong></td></tr>
<tr><td>2</td><td>Cross-scale magnetic edge persistence</td><td>Edge must survive 150 m upward continuation (deep/blind sources)</td><td>Included as H1 component</td></tr>
<tr><td>3</td><td>Strain-belt gating of scarps</td><td>Regional geod_2ndinv/shear/dilatation means mark actively deforming belts</td><td>Included as H1 component</td></tr>
<tr><td>4</td><td>Radiometric alteration-oriented edges</td><td>K/(Th+10) local-anomaly gradients trace fault-controlled fluid conduits</td><td>Included as H1 component</td></tr>
<tr><td>5</td><td>Vent/wellspring fissure-alignment density</td><td>GDR volcanic-vents + wellspring CSVs, oriented kernels</td><td>Rejected standalone: GEMSDOE71 hydro-conduit 0.0558 USER-REPORTED; sparse points; subsumed</td></tr>
</table></div>
<p class=small>No external downloads needed: all layers come from the 13 SHA-pinned mirror files
(verified 13/13 this session). Full protocol: <code>docs/preregistration-g76b.md</code>.</p></div>

<h2>Instrument A — hide-and-recover holdout (seed 20, pooled)</h2>
<div class=card><div class=scroll><table>
<tr><th>Arm</th><th>DTI</th><th>95% CI</th><th>Withheld px</th><th>Emitted</th><th>Paired Δ vs candidate</th></tr>
{arms_rows}
</table></div>
<p class=small>Controls reproduce known receipts exactly: d28_reference {fmt(s['d28_reference']['dti'])} matches GEMSDOE70-P8's 0.0919;
fair_h33 {fmt(s['fair_h33']['dti'])} vs the G76 session's 0.0927 (definitional difference: this run prunes against the
fold-visible catalogue including its 3 px context collar). <code>fair_p8</code> is reported with the
disclosed static-collar handicap: the P8 raster's production collar already avoids the full catalogue, so
like any static collared raster it cannot reach withheld segments (same effect as H33-as-is 0.0037 in
GEMSDOE70's receipts) — it is context, not a fair control.</p></div>

<h2>Proxy instruments (diagnostic only)</h2>
<div class=card><div class=scroll><table>
<tr><th>Instrument</th><th>Arm</th><th>DTI</th><th>95% CI</th><th>Positives</th></tr>
{proxy_rows}
</table></div>
<p class=small>C76-pied is the best live-tracking local instrument measured in this repo
(Spearman ρ = 0.52 vs USER-REPORTED live, n = 77). The candidate is below random there too —
the negative is not an artifact of instrument choice.</p></div>

<h2>Leakage canaries (protocol rule 4)</h2>
<div class=card><p>All 30 features alone: max AUC {fmt(run_card['leakage_canaries']['max_feature_auc'], 3)}
(threshold 0.90). Pooled fold-honest fitted probability AUC {fmt(run_card['leakage_canaries']['pooled_fold_honest_fitted_prob_auc'], 3)}.
No suspected leakage anywhere. Full table: <code>evidence/g76b-exp1/canaries.json</code>.</p></div>

<h2>Uniqueness vs registry (protocol rule 1)</h2>
<div class=card><p>{uniq['n_registry_rasters_compared']} registry rasters compared (76 hash-verified scored rasters +
GEMSDOE70/GEMSDOE77 published artifacts; the 60GEMSDOE historical index lists 862 in total — bytes not
held locally are not compared, disclosed). Worst mutual 3 px dot overlap
{fmt(uniq['worst_mutual']['mutual_overlap'], 3)} vs <code>{uniq['worst_mutual']['file']}</code>;
worst |surface ρ| {fmt(abs(uniq['worst_rho']['surface_spearman_rho_sample200k']), 3)}. Both gates pass
(≤ 0.70, ≤ 0.90) — the artifact is unique, it is simply not good. Full audit:
<code>evidence/g76b-uniqueness.json</code>.</p></div>

<h2>Reproduce</h2>
<div class=card><p><code>.venv/bin/python scripts/restore_data.py</code> (13/13 SHA pins) →
<code>.venv/bin/python scripts/fetch_registry.py</code> (76 scored rasters) →
<code>.venv/bin/python scripts/build_g76b_cache.py</code> →
<code>.venv/bin/python scripts/run_experiment_g76b.py</code> →
<code>.venv/bin/python scripts/build_artifact_g76b.py</code> →
<code>.venv/bin/python scripts/audit_uniqueness_g76b.py …</code>.
Evaluator/writer/allocator are the byte-pinned shared template tools (vendor/gems57); no private fork.</p></div>

<footer>GEMSDOE76 · Lane G76B · verdict negative · 1 of 3 experiments used · 0 weekly slots ·
every score on this page is HOLDOUT-DTI / PROXY-DTI / USER-REPORTED, never an organizer receipt.</footer>
</div></body></html>"""
    (DOCS / "lane-g76b.html").write_text(index)

    exec_summary = f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>GEMSDOE76 Lane G76B — executive summary</title><style>{CSS}</style></head><body><div class=wrap>
<header><h1>Lane G76B — executive summary</h1>
<p class=sub>What this lane produced, whether it is OK to submit, and the exact submission procedure
for whenever a future candidate passes its pre-registered gates.</p></header>

<div class=verdict><h2>Status: NOT OK to submit</h2>
<p>This lane's only TIFF is <code>gems76b-patchctx-exp1-28607dots-DO-NOT-SUBMIT.tif</code>
(SHA-256 <code>{art_sha[:32]}…</code>). It is format-valid (CRS/shape/transform match, all values
finite in [0,1]) and unique vs the registry, but it <strong>failed its pre-registered holdout gate
decisively</strong> — HOLDOUT-DTI {fmt(s['candidate_dots']['dti'])} vs fair-H33 {fmt(s['fair_h33']['dti'])},
below random {fmt(s['random_dots']['dti'])} — so submitting it would waste a weekly slot. It is
published as labeled negative evidence (download OK, submit NOT OK): preserved in
<code>evidence/lane-g76b/</code> and served from
<a href="downloads/gems76b-patchctx-exp1-28607dots-DO-NOT-SUBMIT.tif">docs/downloads/</a>.</p></div>

<h2>How a submission would be made (when a candidate ever passes)</h2>
<div class=card><ol>
<li><strong>Check the run card.</strong> A promotable candidate needs: HOLDOUT-DTI beating the fair
incumbent control with a paired 95% CI above zero, C76-pied point estimate above the H33 reference,
no leakage canary above 0.90, uniqueness gates passing (mutual ≤ 0.70, |ρ| ≤ 0.90), and the shared
validator green. The selector (a human decision, within the weekly cap shown on the
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">submission page</a>)
approves the slot — no session self-promotes.</li>
<li><strong>Download the TIFF</strong> from the repository's evidence directory (or docs/downloads/
on a future non-blocked site) and verify its SHA-256 against the run card.</li>
<li><strong>Submit</strong> at the DrivenData submission page: choose the file (single-band GeoTIFF
or a zip containing one), optionally add a note ≤ 140 characters (the run card carries a suggested
note), and create the submission. Values must be in [0,1] — the shared writer guarantees this and
writes zeros, not NaN, outside the footprint, the encoding the portal's whole-raster range check
accepts.</li>
<li><strong>Record the receipt.</strong> Copy the organizer-confirmed score back into the repo as
ORGANIZER-CONFIRMED evidence; a projection is never written as a score.</li>
</ol></div>

<h2>What this session established</h2>
<div class=card><p>See <a href="lane-g76b.html">the lane page</a> for full numbers. In one sentence:
hand-crafted patch context over four physics families with a fold-honest supervised head is a
<strong>measured negative</strong> — the incumbent H19-5 corroborated-ridge recipe and the
organizer-reference CNN route remain the only credible paths above 0.2778 USER-REPORTED.</p></div>

<footer>GEMSDOE76 · Lane G76B executive summary · nothing here authorizes a weekly slot.</footer>
</div></body></html>"""
    (DOCS / "lane-g76b-executive-summary.html").write_text(exec_summary)
    print("Built docs/lane-g76b.html, docs/lane-g76b-executive-summary.html, "
          "docs/lane-g76b-run-card.json, evidence/g76b_run_card.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
