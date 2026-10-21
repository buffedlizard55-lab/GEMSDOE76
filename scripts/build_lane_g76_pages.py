#!/usr/bin/env python3
"""Build Lane-G76 pages (docs/lane-g76*.html) + evidence/run_card.json + docs/score-ledger.csv.

Renamed from build_site.py at integration with main (PR #2 owns scripts/build_site.py
and the canonical blocked-status site).  Main's fail-closed policy serves no raster
from docs/, so the DO-NOT-SUBMIT artifact lives in evidence/lane-g76/ and is linked
via GitHub, never as a site download.
"""
from __future__ import annotations

import csv
import hashlib
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
EV = ROOT / "evidence"


def load(p: Path):
    return json.loads(p.read_text())


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


CSS = """
:root{--ink:#17212b;--mut:#5b6b7a;--line:#d9e0e7;--bg:#f6f8fa;--red:#b00020;--redbg:#fdecec;--ok:#0b6e2f;--card:#fff}
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
img{max-width:100%;border:1px solid var(--line);border-radius:8px}
.btn{display:inline-block;padding:9px 14px;border-radius:8px;background:#e8eef4;color:#234;text-decoration:none;font-weight:600;margin:4px 6px 4px 0}
.btn.disabled{background:#eee;color:#999;pointer-events:none}
a{color:#0b5cad} footer{color:var(--mut);font-size:13px;margin-top:44px;border-top:1px solid var(--line);padding-top:12px}
.scroll{overflow-x:auto}
"""


def fmt(x, nd=4):
    return f"{x:.{nd}f}" if isinstance(x, (int, float)) else str(x)


def main() -> int:
    exp1 = load(EV / "exp1/holdout_A.json")
    exp2 = load(EV / "exp2/holdout_A.json")
    can1 = load(EV / "exp1/canaries.json")
    can2 = load(EV / "exp2/canaries.json")
    audit = load(EV / "instrument_audit.json")
    uniq = load(EV / "uniqueness_audit.json")
    lat = load(EV / "exp1/lattice_inversion.json")
    data_receipt = load(EV / "data_receipt.json")
    art = ROOT / "evidence/lane-g76/gems76-piedmont-dipole-exp2-27569dots-DO-NOT-SUBMIT.tif"
    art_receipt = load(art.with_suffix(".json"))
    e2s = exp2["scores"]

    run_card = {
        "hypothesis": "Youthful Quaternary normal-fault scarps missing from the USGS/INGENIOUS "
                      "catalogue carry a paired crest-toe Laplacian dipole with slope-facing "
                      "polarity in 1 m LiDAR derivatives aggregated to 100 m, concentrated in "
                      "low-relief piedmont; a detector built only on that signature family "
                      "should recover expert-labelled new faults.",
        "mechanism": "Exp1: hand-set product of dipole x polarity x coherence with strike-guided "
                     "persistence and a piedmont relief gate. Exp2 (pre-registered amendment): "
                     "L2 logistic combiner over the same 10 components, visible-catalogue "
                     "training only, greedy 300 m max-cover emission, B=2px catalogue-flank "
                     "exclusion, binary dots, zeros outside footprint.",
        "named_non_fault_mimic": "Pleistocene pluvial shoreline scarps (Lahontan/Bonneville), "
                                 "terrace risers, fan distributary channel banks, road grades.",
        "holdout_dti": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": "gems57-pooled-hide-v2",
            "withheld_positive_pixels": e2s["candidate_dots"]["withheld_positive_pixels"],
            "exp2_candidate_dots": e2s["candidate_dots"]["dti"],
            "exp2_candidate_ci95": e2s["candidate_dots"]["ci95"],
            "exp1_candidate_dots": exp1["scores"]["candidate_dots"]["dti"],
            "fair_h33_control": e2s["fair_h33"]["dti"],
            "random_control": e2s["random_dots"]["dti"],
            "paired_delta_vs_fair_h33": exp2["paired_differences"]["fair_h33"],
        },
        "proxy_dti": {
            "Bprime_candidate": load(EV / "exp2/proxy_Bprime.json")["scores"]["candidate_final_dots"],
            "C76pied_candidate": load(EV / "exp2/proxy_C76pied.json")["scores"]["candidate_final_dots"],
        },
        "leakage_canaries_max_auc": {
            "exp1": max(max(c["auc"], c["inverse_auc"]) for c in can1.values()),
            "exp2": max(max(c["auc"], c["inverse_auc"]) for c in can2.values()),
            "threshold": 0.90, "any_suspected_leakage": False,
        },
        "uniqueness_vs_registry": {
            "n_rasters_compared": uniq["n_registry_rasters_compared"],
            "worst_mutual_overlap": uniq["worst_mutual"]["mutual_overlap"],
            "worst_mutual_file": uniq["worst_mutual"]["file"],
            "worst_abs_surface_rho": abs(uniq["worst_rho"]["surface_spearman_rho_sample200k"]),
            "gates_pass": bool(uniq["gate_mutual_le_0.70"] and uniq["gate_abs_rho_le_0.90"]),
        },
        "raster_sha256": sha(art),
        "validator": {**art_receipt["validator"], "file": "evidence/lane-g76/gems76-piedmont-dipole-exp2-27569dots-DO-NOT-SUBMIT.tif", "note_on_path": "artifact relocated from docs/downloads/ at integration with main PR #2 (fail-closed site policy); bytes unchanged, sha256 identical"},
        "submission_name": "gems76-piedmont-dipole-exp2-27569dots-DO-NOT-SUBMIT",
        "submission_note_max140": ("G76 piedmont-dipole logistic Exp2: HOLDOUT-DTI 0.0218 vs "
                                   "fair-H33 0.0927 (negative, below random). DO NOT SUBMIT."),
        "experiments_used": "2 of 3 (Exp3 reserved for confirmation of a passing Exp2; not run)",
        "weekly_slots_used": 0,
        "organizer_confirmed_scores": "none in this repository",
        "verdict": "negative",
    }
    (EV / "run_card.json").write_text(json.dumps(run_card, indent=1))
    (DOCS / "lane-g76-run-card.json").write_text(json.dumps(run_card, indent=1))

    rows = audit["rows"]
    with open(DOCS / "score-ledger.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "live_dti_USER_REPORTED_no_organizer_receipt", "n_dots",
                    "A20_holdout_as_is_not_fold_honest", "Bprime_sgmc_proxy", "C76_piedmont_proxy"])
        for r in sorted(rows, key=lambda r: -(r["live_user_reported"] or -1)):
            w.writerow([r["file"], r["live_user_reported"], r["n_dots"],
                        f"{r['A20']:.4f}", f"{r['Bprime']:.4f}", f"{r['C76pied']:.4f}"])

    corr = audit["correlations_vs_live_user_reported"]
    scored = sorted([r for r in rows if r["live_user_reported"] is not None],
                    key=lambda r: -r["live_user_reported"])
    unscored = [r for r in rows if r["live_user_reported"] is None]

    def trow(r):
        live = "—" if r["live_user_reported"] is None else f"{r['live_user_reported']:.4f}"
        return (f"<tr><td><code>{html.escape(r['file'][:72])}</code></td>"
                f"<td class=num>{live}</td><td class=num>{r['n_dots']:,}</td>"
                f"<td class=num>{r['A20']:.4f}</td><td class=num>{r['Bprime']:.4f}</td>"
                f"<td class=num>{r['C76pied']:.4f}</td></tr>")

    top_rows = "\n".join(trow(r) for r in scored[:15])
    unscored_rows = "\n".join(trow(r) for r in unscored)
    v = art_receipt["validator"]

    index = f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>GEMSDOE76 Lane G76 — verdict: Do not submit (negative result)</title><style>{CSS}</style></head><body><div class=wrap>
<header><h1>GEMSDOE76 — Piedmont Scarp-Dipole Lane</h1>
<p class=sub>DOE GEMS Prize (DrivenData #306) · pre-registered Lane G76 session · 2026-10-21 ·
archived official leaderboard observation <strong>0.4413</strong> (read 2026-10-21; not verified as current).
The project brief later reports a current high of <strong>0.3195</strong> (USER-REPORTED; not independently verified here).
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Review the official leaderboard</a>.</p></header>

<div class=verdict><h2>⛔ VERDICT: NEGATIVE — Do not submit any file from this lane</h2>
<p><strong>It is NOT OK to download-and-submit this session's TIFF.</strong> Lane G76 was tested in two
pre-registered experiments on the shared hide-and-recover holdout and lost decisively — below even
count-matched random dots. The holdout result does not support promotion or justify a weekly slot.
The file below is retained only as auditable evidence (its filename says DO-NOT-SUBMIT). A real slot
requires a separate selector step; this session used
<strong>0 slots</strong>.</p>
<p><strong>HOLDOUT-DTI</strong> (gems57-pooled-hide-v2, seed 20, n=11,321 withheld catalogue px):
candidate <strong>{fmt(e2s['candidate_dots']['dti'],4)}</strong> 95% CI [{fmt(e2s['candidate_dots']['ci95'][0],4)}, {fmt(e2s['candidate_dots']['ci95'][1],4)}]
vs fair-H33 control <strong>{fmt(e2s['fair_h33']['dti'],4)}</strong> vs random {fmt(e2s['random_dots']['dti'],4)}.
No number on this page is an organizer-confirmed score; live values are labelled USER-REPORTED.</p>
<p><a class=btn href="lane-g76-executive-summary.html">Executive summary — how submission works &amp; what to do instead</a>
<a class=btn href="lane-g76-run-card.json">Run card (JSON)</a></p></div>

<h2>The one download on this page (evidence only)</h2>
<div class=card><p><span class="tag no">DO NOT SUBMIT</span>
<code>gems76-piedmont-dipole-exp2-27569dots-DO-NOT-SUBMIT.tif</code><br>
SHA-256 <code>{run_card['raster_sha256']}</code> · {v['bytes']:,} bytes · single-band float32 ·
EPSG:32611 · 3730×3292 · all 12,279,160 cells finite in [0,1] (0 NaN) · 27,569 dots ·
0 dots on the mapped catalogue. Format-valid by construction (shared fail-closed writer) —
<strong>format validity is not score evidence</strong>.</p>
<p>Per this repository's fail-closed site policy (main PR #2), no raster is served from the
website. The artifact is preserved in the repository at
<code>evidence/lane-g76/gems76-piedmont-dipole-exp2-27569dots-DO-NOT-SUBMIT.tif</code>
(<a href="https://github.com/buffedlizard55-lab/GEMSDOE76/blob/main/evidence/lane-g76/gems76-piedmont-dipole-exp2-27569dots-DO-NOT-SUBMIT.tif">GitHub</a>)
with its one-TIFF ZIP and writer receipt beside it — review only, <strong>do not submit</strong>.</p>
<p class=small>Suggested portal note if a future file from this lane were ever promoted (it is not):
<code>{html.escape(run_card['submission_note_max140'])}</code></p></div>

<h2>Why the incumbent scored 0.2778 — and why this lane could not beat it</h2>
<div class=card>
<p><strong>Measured:</strong> the incumbent <code>h33-h33-2-b2…-zeros</code> is a strict subset of the earlier
44,090-dot "D2.8" raster — the supervised H19-5 surface thinned to isolated dots, with the 6,436 dots
within 200&nbsp;m of the catalogue deleted (37,654 dots left). The <code>-zeros</code> vs <code>-nan</code>
twins are bit-identical inside the footprint (verified); "zeros" (0.0 outside instead of NaN) only
guarantees passing the portal's whole-raster [0,1] check — it adds no score. Three metric facts do the
work: β/α&nbsp;=&nbsp;4 makes recall cheap (marginal bar k&nbsp;&gt;&nbsp;0.056 at s=0.2778); the
300&nbsp;m max-kernel makes isolated dots nearly as good as lines at ~⅓ the FP cost; and catalogue pixels
are masked in scoring, so near-catalogue dots are pure FP against expert "new fault" truth — deleting
them was free.</p>
<p><strong>Why G76 failed:</strong> the 1&nbsp;m-LiDAR dipole bands, max-pooled to 100&nbsp;m, are saturated by
every fan channel and gully (best single-field AUC 0.631; fitted holdout AUC 0.620). Concentrated but
imprecise dots lose to a uniform spread under this max-cover metric. Per-pixel 100&nbsp;m fields cap at
AUC&nbsp;≈&nbsp;0.63 across every stack we measured (LiDAR, DEM10, GeoDAWN) — the winning ingredient is
learned multi-physics + spatial context, which is the incumbent family's recipe, not a new transform.
Full analysis: <a href="research/why-02778.md">docs/research/why-02778.md</a>.</p>
<img src="assets/fig_dot_maps.png" alt="Dot maps: G76 Exp2 vs incumbent vs catalogue"></div>

<h2>Experiments (pre-registered; 2 of 3 used)</h2>
<div class=card><div class=scroll><table>
<tr><th>Arm</th><th class=num>HOLDOUT-DTI (A, seed20, n=11,321)</th><th class=num>95% CI</th><th class=num>PROXY-DTI B′</th><th class=num>PROXY-DTI C76-pied</th></tr>
<tr><td>Exp1 dipole-product dots (26,414)</td><td class=num>{fmt(exp1['scores']['candidate_dots']['dti'])}</td><td class=num>[{fmt(exp1['scores']['candidate_dots']['ci95'][0])}, {fmt(exp1['scores']['candidate_dots']['ci95'][1])}]</td><td class=num>0.0106</td><td class=num>0.0140</td></tr>
<tr><td><strong>Exp2 logistic-combiner dots (27,799 holdout / 27,569 final)</strong></td><td class=num><strong>{fmt(e2s['candidate_dots']['dti'])}</strong></td><td class=num>[{fmt(e2s['candidate_dots']['ci95'][0])}, {fmt(e2s['candidate_dots']['ci95'][1])}]</td><td class=num>0.0172</td><td class=num>0.0208</td></tr>
<tr><td>fair-H33 control (fold-honest B=2)</td><td class=num>{fmt(e2s['fair_h33']['dti'])}</td><td class=num>[{fmt(e2s['fair_h33']['ci95'][0])}, {fmt(e2s['fair_h33']['ci95'][1])}]</td><td class=num>0.0961*</td><td class=num>0.0945*</td></tr>
<tr><td>random dots (37,654)</td><td class=num>{fmt(e2s['random_dots']['dti'])}</td><td class=num>[{fmt(e2s['random_dots']['ci95'][0])}, {fmt(e2s['random_dots']['ci95'][1])}]</td><td class=num>0.0708</td><td class=num>0.0426</td></tr>
</table></div>
<p class=small>*H33-as-is on proxies. Leakage canaries: max feature-alone AUC Exp1 {max(max(c['auc'],c['inverse_auc']) for c in can1.values()):.3f},
Exp2 {max(max(c['auc'],c['inverse_auc']) for c in can2.values()):.3f} (alarm &gt;0.90 — none fired).
Lattice inversion prior: implied hidden-truth size ≈ {lat['implied_hidden_truth_pixels']:,.0f} px
(mean kernel cover {lat['mean_kernel_cover_uniform_truth']:.4f}, bijection approximation — prior only, not a score).
Preregistration: <a href="preregistration-g76.md">lane</a> + <a href="preregistration-g76-amendment-exp2.md">Exp-2 amendment</a> (both written before their scores).</p></div>

<h2>Instrument audit — do local scores predict the live board?</h2>
<div class=card><p>77 registry rasters with USER-REPORTED live scores were fetched, hash-verified against the
GEMSDOE70 registry index, and re-scored identically. Correlations with live: Instrument-A-as-is
Spearman ρ={corr['A20']['spearman_rho']:.3f} (p={corr['A20']['spearman_p']:.1e}) — construction-biased, see IR-76-08;
SGMC B′ ρ={corr['Bprime']['spearman_rho']:.3f}; piedmont-conditioned C76 ρ={corr['C76pied']['spearman_rho']:.3f}
(p={corr['C76pied']['spearman_p']:.1e}; LOO range [{corr['C76pied']['loo_spearman_min']:.3f}, {corr['C76pied']['loo_spearman_max']:.3f}]).
C76 is the least-bad selector instrument but still leaves the whole top family statistically
undifferentiated, and B′/C76 are gameable by SGMC-derived files (IR-76-09).
Full table: <a href="score-ledger.csv">score-ledger.csv</a>.</p>
<img src="assets/fig_instrument_correlation.png" alt="Instrument vs live correlation">
<div class=scroll><table><tr><th>Top-15 by USER-REPORTED live</th><th class=num>live*</th><th class=num>dots</th><th class=num>A20</th><th class=num>B′</th><th class=num>C76</th></tr>
{top_rows}</table></div>
<h3>Unscored headline files (selector reference — measurements, not picks)</h3>
<div class=scroll><table><tr><th>File</th><th class=num>live*</th><th class=num>dots</th><th class=num>A20</th><th class=num>B′</th><th class=num>C76</th></tr>
{unscored_rows}</table></div>
<p class=small>*USER-REPORTED from the project prompt's per-site list; no organizer receipt exists in any
cloned repository (IR-76-03). A20 for registry files is not fold-honest.</p></div>

<h2>Uniqueness (protocol rule 1)</h2>
<div class=card><p>Compared against <strong>{uniq['n_registry_rasters_compared']} registry rasters</strong> (surface + final dots):
worst mutual 3&nbsp;px dot overlap <strong>{uniq['worst_mutual']['mutual_overlap']:.3f}</strong>
(vs <code>{html.escape(uniq['worst_mutual']['file'][:60])}</code>; gate ≤0.70) and worst |Spearman ρ|
<strong>{abs(uniq['worst_rho']['surface_spearman_rho_sample200k']):.3f}</strong> (gate ≤0.90) — uniquely in its lane,
which is necessary but (here) not sufficient. One-way forward overlap vs the dense 206,895-dot calibration
lattice is ~1.0 for any dot raster; disclosed in <code>evidence/uniqueness_audit.json</code>.</p></div>

<h2>Data &amp; provenance</h2>
<div class=card><p>Competition rasters were restored from the owner's public GitHub mirrors and verified
byte-for-byte against SHA-256 pins ({'all ' + str(len(data_receipt['files'])) + ' files match' if data_receipt['all_match'] else 'MISMATCH — see receipt'}):
<code>training_features.tif</code> 4371c82e…, <code>labels/existing_faults</code> 7ba308cc…,
<code>sample_submission</code> 2176d08e…. Mirror integrity is <em>not</em> organizer authentication; the
authoritative source is the DrivenData data page (login required). The prompt's "single remaining blocker"
(data placement) does not exist from an environment with GitHub access: <code>scripts/restore_data.py</code>
reproduces the full stack. External layers: USGS 3DEP-derived LiDAR scarp stack &amp; GeoDAWN products via
the same pins (<code>registry/data_manifest.json</code>).</p></div>

<h2>Irregularities flagged (9)</h2>
<div class=card><p>Includes: the incumbent site's <strong>empty download ZIP</strong> (216 bytes, no TIFF inside);
no organizer receipt for "0.2778"; internally inconsistent holdout fields in the incumbent's audit JSON;
the non-independent "Anderson" 0.2750 dot set; a shared-allocator early-stop defect (reported for upstream
fix, vendor code untouched here). Full list: <a href="irregularities.md">docs/irregularities.md</a>.</p></div>

<h2>Official sources (manual review)</h2>
<div class=card><ul>
<li>Problem description &amp; metric &amp; submission format — <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">DrivenData p.967</a></li>
<li>About / additional resources — <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/">DrivenData p.968</a></li>
<li>Leaderboard — <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">official board</a>; this page's archived 2026-10-21 snapshot was 0.4413, while the prompt later reports 0.3195 as current. Current value is not verified in this environment.</li>
<li>Rules PDF (NLR FY26OSTI 96647) — <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">docs.nlr.gov</a></li>
<li>Masking of known faults (staff clarification) — <a href="https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516">forum thread 11516</a></li>
<li>Reference solution — <a href="https://github.com/drivendataorg/gems-prize-reference-solution">github.com/drivendataorg/gems-prize-reference-solution</a></li>
<li>USGS GeoDAWN surveys — <a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">usgs.gov</a> · DOI 10.5066/P93LGLVQ</li>
<li>GBCGE INGENIOUS — <a href="https://gbcge.org/current-projects/ingenious/">gbcge.org</a> · DOE GDR #1391 — <a href="https://gdr.openei.org/submissions/1391">gdr.openei.org</a> (CC BY 4.0)</li>
<li>EPSG:32611 — <a href="https://epsg.io/32611">epsg.io/32611</a> · Tversky index — <a href="https://en.wikipedia.org/wiki/Tversky_index">Wikipedia</a></li>
</ul></div>

<h2>Limitations</h2>
<div class=card><ul>
<li>No DrivenData authentication in this environment: cannot submit, cannot read the private board or weekly slot balance, cannot authenticate mirror data with the organizer.</li>
<li>No GPU; 2 CPU / 3 GB RAM sandbox. The 2-D patch-context route identified as most promising was out of reach here.</li>
<li>Local instruments are proxies: hidden expert labels are unavailable by design; Instrument A measures catalogue recovery, B′/C76 measure SGMC-like geography. Both are shown to mis-track live at the top of the range.</li>
<li>Score attributions in the family ledger are USER-REPORTED; file↔score links cannot be organizer-verified from here.</li>
<li>GitHub Pages serving depends on repo settings (Settings → Pages → main /docs); this session could not confirm it is enabled.</li>
</ul></div>

<footer>GEMSDOE76 · Lane G76 negative result · evidence in <code>evidence/</code> ·
run card <a href="lane-g76-run-card.json">lane-g76-run-card.json</a> · built by <code>scripts/build_lane_g76_pages.py</code> · canonical blocked-status site: <a href="index.html">index.html</a> ·
Core decision rule applied throughout: maximize P(Win) — which here meant not spending a slot.</footer>
</div></body></html>"""
    (DOCS / "lane-g76.html").write_text(index)

    exec_summary = f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>GEMSDOE76 — Executive summary: how to submit (and why not this file)</title><style>{CSS}</style></head><body><div class=wrap>
<header><h1>Executive summary</h1><p class=sub>Exactly how a submission is made in this competition — and this session's status.</p></header>

<div class=verdict><h2>⛔ THIS SESSION'S FILE: DO NOT SUBMIT</h2>
<p><code>gems76-piedmont-dipole-exp2-27569dots-DO-NOT-SUBMIT.tif</code> (SHA-256 <code>{run_card['raster_sha256'][:16]}…</code>)
failed its pre-registered promotion gate: HOLDOUT-DTI {fmt(e2s['candidate_dots']['dti'])} vs fair-H33
{fmt(e2s['fair_h33']['dti'])} (paired Δ {fmt(exp2['paired_differences']['fair_h33']['delta'])}), below random dots.
It is format-valid but failed the holdout promotion gate. <strong>Do not spend a weekly slot on it.</strong>
The instructions below are the general, verified procedure for when a file <em>is</em> promoted by the
separate human selector step.</p></div>

<h2>Submission format and procedure (check current official instructions)</h2>
<div class=card><ol>
<li><strong>File:</strong> one single-band <code>float32</code> GeoTIFF (<code>.tif</code>), or a <code>.zip</code>
containing exactly one GeoTIFF. It must match the sample submission exactly: CRS EPSG:32611 (UTM 11N),
100&nbsp;m pixels, 3730×3292, transform (100, 0, 243350, 0, −100, 4508550), values in [0,&nbsp;1]
(probability/confidence of fault presence). — <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">official submission format</a></li>
<li><strong>Avoid the historical "Predicted values must be in range [0, 1]" rejection:</strong> use the
all-finite "zeros" encoding (0.0 outside the footprint, no NaN anywhere, no nodata tag). Measured root
causes of that error in this project family: float32 sentinel (−3.4×10<sup>38</sup>) pixels leaking from
<code>training_features.tif</code> (3,061 inside the footprint), and NaN left inside the footprint by a
feature-band footprint mask (same 3,061 px). The organizer's own reference writer emits an all-finite,
nodata-free raster. This repo's shared writer fails closed on all three hazards and re-validates the
bytes on disk.</li>
<li><strong>Where:</strong> the competition's submission page ("New submission" → choose file → optional
note → submit). Respect the weekly cap shown on that page at the time (this session could not read the
portal balance — no auth). Record the returned receipt/score against the file's SHA-256; that receipt is
the only ORGANIZER-CONFIRMED evidence class.</li>
<li><strong>Name &amp; note:</strong> give every upload a unique name and a ≤140-character note stating lane,
evidence and counts, e.g. for a hypothetical promoted G76 successor:
<code>{html.escape(run_card['submission_note_max140'])}</code></li>
<li><strong>Remember the prize structure:</strong> one selected submission is scored first against the
private expert set (Initial Prize Round) and then re-scored against the expanded label set (Final Prize
Round). Known-catalogue pixels are masked in both rounds — never spend probability mass on them.</li>
</ol></div>

<h2>What the selector should look at instead</h2>
<div class=card><p>Measurements from this session's 79-raster audit (not picks — slot choice is the human
selector's step): the incumbent family (H33-B2 and near-duplicates) remains the only group with
USER-REPORTED live ≥0.26. Among <em>unscored</em> files measured here, GEMSDOE70's P9 hero
(<code>gems70-p5-multiphysics-submodular-37654-20261020</code>) has the highest C76-piedmont proxy
(0.1079) of any 37,654-dot candidate and beat H33 on GEMSDOE70's own three instruments; it has no live
score yet. The single biggest identified upside remains a properly trained 2-D spatial-context model
(reference-solution architecture at scale), which needs GPU time this sandbox does not have. Details:
<a href="research/why-02778.md">why-02778.md</a>, <a href="score-ledger.csv">score-ledger.csv</a>.</p></div>

<footer><a href="lane-g76.html">← Back to Lane G76</a> · <a href="index.html">canonical status page</a></footer>
</div></body></html>"""
    (DOCS / "lane-g76-executive-summary.html").write_text(exec_summary)
    (DOCS / ".nojekyll").write_text("")
    print("site built:", [p.name for p in DOCS.glob("*.html")])
    return 0


if __name__ == "__main__":
    sys.exit(main())
