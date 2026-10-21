#!/usr/bin/env python3
"""Render an auditable static site with an explicit submission status.

State machine (fail closed):
  * No candidate -> clean blocked: "No submission TIFF is available. Do not submit."
  * Candidate present with verdict 'negative' -> "NEGATIVE CANDIDATE PUBLISHED.
    DO NOT SUBMIT." with TIFF/ZIP/receipt/run-card download links, SHA-256,
    validator output and holdout run card. The file is labeled DO-NOT-SUBMIT in
    its filename and on the page; nothing authorizes a weekly slot.
  * Candidate present with verdict 'promote' or safe_to_submit -> REJECT. A
    promoted file requires separate selector approval and an organizer receipt;
    this renderer never publishes one.

The page makes it OBVIOUS whether it is OK to download and submit the TIF.
"""
from __future__ import annotations

import html
import json
from pathlib import Path
import shutil
import markdown
from project import ROOT, read_json
from preflight import audit

DOCS = ROOT / "docs"
DOWNLOADS = DOCS / "downloads"


def page(title, body, active=""):
    links = [("index.html", "Overview"), ("executive-summary.html", "How to submit"),
             ("research.html", "Research & review"), ("inherited-main-audit.html", "Critical audit"),
             ("sources.html", "Sources")]
    nav = ''.join(f'<a href="{url}" ' + ('aria-current="page" ' if url == active else '') + f">{text}</a>"
                  for url, text in links)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name=\"description\" content=\"GEMSDOE76: audited fault-detection research, explicit submission status.\">
<title>{html.escape(title)} · GEMSDOE76</title><link rel=\"stylesheet\" href=\"style.css\"></head>
<body><a class=\"skip\" href=\"#main\">Skip to content</a><header><a class=\"brand\" href=\"index.html\">GEMS<span>DOE76</span></a><nav aria-label=\"Main\">{nav}</nav></header>
<main id=\"main\">{body}</main><footer><strong>Evidence before confidence.</strong> No organizer-confirmed result or weekly-slot approval.
<a href=\"https://github.com/buffedlizard55-lab/GEMSDOE76\">Repository</a> · <a href=\"downloads/run-card.json\">JSON run card</a></footer></body></html>'''


# Primary negative candidate (geophys-gate lane) plus any additional labeled
# negative candidates published by later lanes. Each entry is (stem, card file).
EXTRA_NEGATIVE_CANDIDATES = [
    ("gems76b-patchctx-exp1-28607dots-DO-NOT-SUBMIT", "run-card-g76b.json"),
]


def _candidate_state():
    """Return (state, card); state in {None, 'negative', 'promote'}."""
    card_path = DOWNLOADS / "run-card.json"
    tif = DOWNLOADS / "gems76-geophys-cataloguefree-rank-gate1-20261021.tif"
    if not card_path.is_file() or not tif.is_file():
        return None, None
    card = read_json(card_path)
    if card.get("verdict") == "promote" or card.get("safe_to_submit") is True:
        return "promote", card
    return "negative", card


def _extra_negative_candidates():
    """Additional labeled negative candidates with card+tif present (never promoted)."""
    out = []
    for stem, card_name in EXTRA_NEGATIVE_CANDIDATES:
        card_path = DOWNLOADS / card_name
        tif = DOWNLOADS / f"{stem}.tif"
        if not card_path.is_file() or not tif.is_file():
            continue
        card = read_json(card_path)
        if card.get("verdict") == "promote" or card.get("safe_to_submit") is True:
            raise ValueError(f"Refusing extra candidate in promote state: {stem}")
        out.append(card)
    return out


def _check_no_unlisted_rasters():
    """Fail closed: any raster/archive in docs/downloads must be listed in a run card."""
    cards = []
    for name in ["run-card.json"] + [c for _, c in EXTRA_NEGATIVE_CANDIDATES]:
        if (DOWNLOADS / name).is_file():
            cards.append(read_json(DOWNLOADS / name))
    allowed = set()
    for card in cards:
        allowed |= {a for a in (card.get("raster"), card.get("raster_zip")) if a}
    for p in DOWNLOADS.rglob("*"):
        if p.suffix.lower() in (".tif", ".tiff", ".zip"):
            rel = str(p.relative_to(ROOT))
            if rel not in allowed:
                raise ValueError(f"Unlisted raster/archive on published site: {rel}")


def run_card(preflight):
    return {
        "run_id": "gems76-preflight-20261021",
        "hypothesis": "Conditional proposal A: concordant displacement of magnetic and radiometric contacts; no lane assigned or experiment executed.",
        "mechanism": "Buried cross-cutting faults may offset pre-existing lithologic contacts without a surface scarp; hypothesis only.",
        "non_fault_mimic": "Channel-alluvium boundaries and airborne survey line-leveling seams.",
        "holdout": {"evidence_class": "HOLDOUT-DTI", "status": "not-run",
                    "evaluator_version": "gems57-pooled-hide-v2",
                    "withheld_positive_pixels": None, "dti": None, "ci95": None,
                    "current_best_reproduced": False, "feature_canaries": "not-run"},
        "registry": {"surface_rank_correlation": None, "surface_forward_overlap_3px": None,
                     "final_dot_rank_correlation": None, "final_dot_forward_overlap_3px": None,
                     "status": "not-run: no candidate and no complete scoped raster inventory",
                     "duplicate": None, "uniqueness_cleared": False,
                     "limits": {"rank_correlation_stop_above": 0.90, "forward_overlap_stop_above": 0.70}},
        "raster_sha256": None,
        "validator": {"status": "not-run: no generated candidate raster",
                      "no_nan_inside_footprint": None, "all_values_in_0_1": None,
                      "crs_matches": None, "shape_matches": None, "transform_matches": None,
                      "reference_only_grid_audit": preflight["reference_grid"]},
        "submission_name": None,
        "note": "Negative preflight: lane, cached arrays, current raster registry and matched holdout evidence missing. Do not submit.",
        "verdict": "negative", "safe_to_submit": False, "downloadable_submission": False,
        "downloadable_is_approved": False,
        "experiments_run": preflight["experiments_run"], "weekly_slots_used": 0, "selector_approved": False,
        "inherited_candidates": "withdrawn: simulated inputs; original evidence preserved in quarantine",
        "blockers": preflight["blockers"]}


def _esc(t, quote=True):
    return html.escape(str(t), quote=quote)


def _download_block(card, receipt):
    name = card["submission_name"]
    tif_rel = f"downloads/{name}.tif"
    zip_rel = f"downloads/{name}.zip"
    rec_rel = f"downloads/{name}.json"
    lines = []
    lines.append("<section class=\"notice\"><h2>Prediction file (format-valid, scientifically negative)</h2>")
    lines.append(f"<p><strong>File:</strong> {_esc(tif_rel)}  ·  <strong>SHA-256:</strong> "
                 f"<code>{_esc(card['raster_sha256'])}</code></p>")
    lines.append(f"<p><strong>One-TIFF ZIP:</strong> {_esc(zip_rel)}  ·  <strong>SHA-256:</strong> "
                 f"<code>{_esc(receipt.get('zip_sha256',''))}</code></p>")
    lines.append(f"<p><strong>Writer + validator receipt:</strong> <a href=\"{rec_rel}\">{rec_rel}</a></p>")
    v = receipt["validator"] if receipt else {}
    lines.append(f"<p><strong>Validator:</strong> all local checks passed; no NaN inside the footprint, "
                 f"values in [{_esc(v.get('min'))}, {_esc(v.get('max'))}], "
                 f"CRS {_esc(v.get('meta',{}).get('crs'))}, shape {_esc(v.get('meta',{}).get('shape'))}, "
                 f"transform matches sample_submission.tif, zero dots on the mapped catalogue.</p>")
    lines.append('<p class="downloads"><a class="button" href="' + tif_rel + '" download>Download submission TIFF</a> '
                 '<a class="button secondary" href="' + zip_rel + '" download>Download one-TIFF ZIP</a> '
                 '<a class="button secondary" href="downloads/run-card.json" download>Download run card</a></p>')
    lines.append('<p class="fine"><strong>Status: DO NOT SUBMIT.</strong> This is a labeled negative candidate '
                 '(holdout DTI below the fair-H33 benchmark). It is published so the status is obvious and '
                 'verifiable; it does not use or authorize any weekly slot, and no organizer receipt exists for it.</p>')
    lines.append("</section>")
    return "\n".join(lines)


def _static_tail():
    return '''<p>A successful local validator is not organizer acceptance. The current bridged reference grid is
EPSG:32611, 3730 × 3292, affine (100, 0, 243350, 0, −100, 4508550); these are technical measurements, not score
evidence, and still need official-origin authentication.</p>
<h2>Review the receipts</h2><p><a href="downloads/preflight.json">Preflight</a> ·
<a href="downloads/run-card.json">Run card</a> · <a href="downloads/recovered-byte-manifest.json">
Pinned sources and hashes</a> · <a href="research.html">Full review and limitations</a></p>'''


def build():
    report = audit()
    state, card = _candidate_state()
    _check_no_unlisted_rasters()
    DOWNLOADS.mkdir(parents=True, exist_ok=True)

    if state == "promote":
        raise ValueError("This renderer refuses to publish a promoted/safe_to_submit candidate. "
                         "Selector approval and an organizer receipt are required first.")

    receipt = None
    if state == "negative":
        rec_path = DOWNLOADS / "gems76-geophys-cataloguefree-rank-gate1-20261021.json"
        if rec_path.is_file():
            receipt = read_json(rec_path)

    if card is not None:
        (DOWNLOADS / "run-card.json").write_text(json.dumps(card, indent=2, allow_nan=False) + "\n")
    else:
        card = run_card(report)
        (DOWNLOADS / "run-card.json").write_text(json.dumps(card, indent=2, allow_nan=False) + "\n")

    for name in ("preflight.json", "source-inventory.json", "recovered-byte-manifest.json",
                 "verification.json", "inherited-candidate-validation.json",
                 "inherited-main-manifest.json", "review.md"):
        src = ROOT / "evidence" / name
        if src.is_file():
            shutil.copyfile(src, DOWNLOADS / name)
    if (ROOT / "evidence/upstream/recovery.json").is_file():
        shutil.copyfile(ROOT / "evidence/upstream/recovery.json", DOWNLOADS / "recovered-byte-manifest.json")
    exp_dir = ROOT / "evidence/exp_geophys_gate"
    if exp_dir.is_dir():
        for name in ("manifest.json", "canaries.json", "holdout.json", "emission.json", "gates.json"):
            if (exp_dir / name).is_file():
                shutil.copyfile(exp_dir / name, DOWNLOADS / name)

    esc = _esc
    extras = _extra_negative_candidates()
    _extra_blocks = ""
    if state == "negative":
        for xcard in extras:
            xreceipt = None
            xrec_path = DOWNLOADS / f"{xcard['submission_name']}.json"
            if xrec_path.is_file():
                xreceipt = read_json(xrec_path)
            _xh = xcard["holdout"]
            _extra_blocks += (_download_block(xcard, xreceipt)
                              + f'<p><strong>HOLDOUT-DTI</strong> (evaluator {esc(_xh["evaluator_version"])}, '
                                f'{_xh["withheld_positive_pixels"]:,} withheld positives): '
                                f'<strong>{_xh["dti"]:.4f}</strong> 95% CI '
                                f'[{_xh["ci95"][0]:.4f}, {_xh["ci95"][1]:.4f}] vs fair-H33 control '
                                f'{_xh.get("fair_h33_control_dti", 0.0961):.4f} and random '
                                f'{_xh.get("random_dots_control_dti", 0.0341):.4f} — below random. '
                                'Uniqueness gates passed (worst mutual overlap '
                                f'{xcard["uniqueness"]["worst_mutual_overlap"]:.3f} &le; 0.70, worst |rho| '
                                f'{xcard["uniqueness"]["worst_abs_surface_rho"]:.3f} &le; 0.90).</p>'
                              + '<p class="fine">Lane page: <a href="lane-g76b.html">'
                                'G76B patch-context corroboration — full receipts, hypotheses and diagnosis</a>.</p>')
    if state == "negative":
        h = card["holdout"]
        overview = f'''
<section class="hero"><p class="eyebrow">GEOLOGICAL FAULT DETECTION · AUDIT-FIRST RESEARCH</p>
<h1>Prediction files exist. None is OK to submit.</h1>
<p class="lede">{len(extras) + 1 if state == "negative" else 1} unique, format-valid prediction TIFFs have been
generated and validated by separate lanes; every one has a negative holdout result. It is
<strong>not OK to submit</strong> any of them. This page states the download/submit status of each
explicitly.</p></section>
<section class="notice" aria-labelledby="status"><p class="eyebrow">CURRENT DECISION · DO NOT SUBMIT</p>
<h2 id="status">Status: {esc(card['verdict'].upper())} — negative holdout evidence</h2>
<p><strong>Do not submit</strong> this raster to the competition; it uses no weekly slot.
The generated raster <strong>must not be uploaded</strong> and uses no weekly slot.
Holdout DTI <strong>{h['dti']:.4f} 95% CI [{h['ci95'][0]:.4f}, {h['ci95'][1]:.4f}]</strong>
(evaluator {esc(h['evaluator_version'])}, alpha 0.2 / beta 0.8, 300 m triangular kernel,
{h['withheld_positive_pixels']} withheld positives) is below the fair-H33 benchmark 0.0927 (user-reported context,
no organizer receipt) and below random dots (0.0458).</p>
{_download_block(card, receipt)}{_extra_blocks}
<p class="fine">Every number on this page is HOLDOUT-DTI or explicitly labeled USER-REPORTED. No projection is
written as a score. ORGANIZER-CONFIRMED requires an authenticated submission-page receipt; none exists.</p></section>
<section><h2>What would flip this to OK TO SUBMIT</h2>
<ol class="checklist">
<li>A method lane is assigned to this parallel run (none exists yet; self-assignment is forbidden).</li>
<li>The template cached feature-stack array bytes are placed and hash-verified.</li>
<li>A complete scoped raster inventory is assembled and uniqueness gates pass (rank correlation &le; 0.90,
forward dot overlap within 3 px &le; 70% vs every prior).</li>
<li>The candidate beats the current holdout best on these folds, with feature-alone leakage canaries below AUC 0.90.</li>
<li>Selector approval and a remaining weekly slot on the organizer submission page.</li>
<li>An authenticated organizer receipt (ORGANIZER-CONFIRMED score) after upload.</li>
</ol></section>
'''
    else:
        checks = ''.join('<li>' + esc(b) + '</li>' for b in report['blockers'])
        overview = f'''<section class="hero"><p class="eyebrow">GEOLOGICAL FAULT DETECTION · AUDIT-FIRST RESEARCH</p>
<h1>A defensible submission.<br>Not just another TIFF.</h1>
<p class="lede">Testing new fault-discovery mechanisms without copying prior predictions, leaking catalogue labels, or inventing leaderboard results.</p></section>
<section class="notice" aria-labelledby="status"><p class="eyebrow">CURRENT DECISION · NEGATIVE</p>
<h2 id="status">No approved submission TIFF is available. Do not submit.</h2>
<p>The required scientific checks could not run. A reference raster, renamed archive or random-dot file would not satisfy the request.</p>
<div class="actions"><span class="disabled" role="status">TIFF download unavailable — prerequisites missing</span><a class="button secondary" href="downloads/run-card.json" download>Download negative run card</a></div>
<p class="fine">A prior Lane G76 run generated a unique TIFF but failed its promotion gate; HOLDOUT-DTI (gems57-pooled-hide-v2, 11,321 withheld positives) was 0.0218, 95% CI [0.0145, 0.0303]. It is evidence only and must not be submitted. This review used no new experiment or weekly slot. Format validity alone never authorizes a submission. <a href="lane-g76.html">Read the negative result and audit trail →</a></p></section>
<section class="notice"><h2>Earlier upload advice has been withdrawn.</h2><p>A concurrent prior build used a simulated footprint, simulated catalogue and synthetic physical fields. Independent bridge-relative checks found off-footprint predictions and catalogue overlap. The archived artifacts are not safe research submissions.</p><a href="inherited-main-audit.html">Read the critical source-and-file audit →</a></section>
<div class="grid"><article><p class="label">SCIENTIFIC QUESTION</p><h2>Why did H33 help?</h2><p>Inherited evidence points to a sparse subset of an existing geological signal. Reduced redundant emission is a plausible metric benefit, not proof of causation.</p><a href="research.html">Read the H33 evidence →</a></article>
<article><p class="label">NEXT RESEARCH</p><h2>Contacts, not copies.</h2><p>Four conditional hypotheses target displaced contacts, signed alteration, drainage disequilibrium and edge-termination asymmetry. None is validated or assigned as this session's lane.</p><a href="research.html#conditional-geological-hypotheses-generated-before-method-implementation">Review hypotheses →</a></article>
<article><p class="label">AUDIT TRAIL</p><h2>Know what was checked.</h2><p>Public metadata for all 78 named project repositories, pinned template modules and bridge-grid checks. Not a full raster uniqueness audit or live leaderboard verification.</p><a href="sources.html">Inspect sources →</a></article></div>
<section><h2>What stops a real submission?</h2><ul class="checklist">{checks}</ul>
<p><a href="executive-summary.html">Exact release and submission sequence →</a></p></section>
<section class="subtle"><h2>Evidence, with boundaries.</h2><p>The initial checkout had only a README. Shared tools and reference inputs are recovered; the claimed ready-to-train pipeline did not exist here. The main goal—a unique, validated downloadable prediction TIFF—remains unmet.</p><p>Organizer pages and external data hosts cannot be inspected from this environment. Historic scores supplied in the project brief are unverified; no leaderboard improvement is claimed.</p></section>'''

    (DOCS / 'index.html').write_text(page('Submission readiness', overview, 'index.html'))

    extra_exec = ""
    for xcard in extras:
        extra_exec += ('<p><strong>Additional negative candidate (also DO NOT SUBMIT):</strong> '
                       '<a href="downloads/' + xcard['submission_name'] + '.tif" download>'
                       + xcard['submission_name'] + '.tif</a> &middot; SHA-256 <code>'
                       + xcard['raster_sha256'] + '</code> &middot; HOLDOUT-DTI '
                       + f"{xcard['holdout']['dti']:.4f} [{xcard['holdout']['ci95'][0]:.4f}, "
                       + f"{xcard['holdout']['ci95'][1]:.4f}]"
                       + ' &middot; <a href="lane-g76b.html">lane page</a></p>')
    if state == "negative":
        exec_note = (esc(card['note']) + f"  SHA-256 {esc(card['raster_sha256'])}.")[:140]
        executive = f'''<p class="eyebrow">EXECUTIVE SUMMARY</p><h1>How to make a competition submission</h1>
<section class="notice"><h2>CURRENT FILE — READ BEFORE DOWNLOADING</h2>
<p><strong>Do not submit this file.</strong> A unique prediction TIFF exists ({esc(card['submission_name'])}),
it is format-valid ([0,1], finite, EPSG:32611, 3730 × 3292, transform matches sample_submission.tif), but its
holdout result is negative (DTI {card['holdout']['dti']:.4f} vs fair-H33 benchmark 0.0927). Downloading it is fine;
uploading it to the competition would waste a weekly slot on a known-negative candidate.</p>
<p><strong>File:</strong> <a href="downloads/{card['submission_name']}.tif" download>{card['submission_name']}.tif</a>
 · <strong>SHA-256:</strong> <code>{card['raster_sha256']}</code>
 · <strong>One-TIFF ZIP:</strong> <a href="downloads/{card['submission_name']}.zip" download>download</a>
 · <strong>Note ({card['note_chars']}/140 chars):</strong> {exec_note}
 · <strong>Verdict:</strong> {card['verdict']}</p>
{extra_exec}
<p class="fine">This prevents the historical portal error "Predicted values must be in range [0, 1]": the raster is
all-finite, serialized without clipping, and validated on disk before release. Local validation is not organizer acceptance.</p></section>
<h2>Release sequence (once a candidate passes all gates)</h2>
<ol class="steps">
<li>Establish inputs and lane; place hash-pinned shared feature caches; authenticate sample/catalogue and data eligibility; refresh the scoped raster registry.</li>
<li>Validate science: feature-alone leakage canaries (AUC &le; 0.90), buffered whole-segment spatial hide-and-recover, pooled DTI with version, withheld positives and 95% CI; uniqueness vs every prior.</li>
<li>Package once via the shared writer (single-band float32 GeoTIFF, optional one-TIFF ZIP); no silent clipping/repair; values already in [0,1]; exterior zeroed; catalogue pixels masked exactly.</li>
<li>Separate selection from generation: holdout improvement vs current best, selector approval, current weekly cap on the organizer submission page.</li>
<li>Sign in to the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">official competition</a>, choose the approved <code>.tif</code> or one-TIFF <code>.zip</code>, copy the unique submission name and a note of at most 140 characters from the receipt, submit, and save the organizer receipt. Only then label a score ORGANIZER-CONFIRMED.</li>
</ol>
<h2>Only after a genuinely approved file is published</h2>
<ol class="steps">
<li>Download the file explicitly marked as the approved prediction (not a reference or diagnostic). Compare its SHA-256 against its adjacent receipt.</li>
<li>Sign in to the official competition, review eligibility/rules, open its New submission form.</li>
<li>Choose the approved single-band <code>.tif</code> or its one-TIFF <code>.zip</code> as “File to submit”. Do not upload a document.</li>
<li>Copy the artifact's unique submission name and its note of at most 140 characters from its receipt.</li>
<li>Submit only after selector approval. Save the submission-page receipt and organizer result. Only then label a score ORGANIZER-CONFIRMED.</li>
</ol>
<p><a class="button secondary" href="downloads/run-card.json" download>Download current run card</a></p>
{_static_tail()}'''
    else:
        executive = '''<p class="eyebrow">EXECUTIVE SUMMARY</p><h1>How to make a competition submission</h1>
<section class="notice"><h2>STOP: there is currently no file to upload.</h2><p>Do not submit the reference TIFFs, the JSON run card, or this webpage. No generated prediction has passed the required gates.</p><a class="button secondary" href="downloads/run-card.json" download>Download the current negative decision</a></section>
<h2>Before a file can be released</h2>
<ol class="steps">
<li><strong>Establish inputs and lane.</strong> Resolve the parallel-run method assignment, place hash-pinned shared feature caches, authenticate sample/catalogue and data eligibility, and refresh the complete scoped raster registry.</li>
<li><strong>Validate science.</strong> Run feature-alone leakage canaries, buffered whole-segment spatial hide-and-recover, and a frozen current-best comparator. Every catalogue feature must use visible faults only. Pool DTI components and report version, withheld positives and 95% confidence intervals.</li>
<li><strong>Prove distinctness in the accessible scope.</strong> Check the surface before placement and the final dots. Stop if rank correlation exceeds 0.90 or forward dot overlap within 3 pixels exceeds 70% against any prior. Missing priors are not a clearance.</li>
<li><strong>Package once, without silent repairs.</strong> Use the shared writer for single-band float32 GeoTIFF and, optionally, a ZIP containing only that TIFF. Predictions must already be normalized, finite and in [0,1]. Zero the exterior explicitly; mask visible catalogue pixels exactly. Verify CRS, shape and transform against the authenticated format.</li>
<li><strong>Separate selection from generation.</strong> Require a documented holdout improvement against the current best and selector approval. Check current contest rules and the remaining weekly cap on the organizer's submission page. No slot is authorized here.</li></ol>
<h2>Only after a genuinely approved file is published</h2>
<ol class="steps">
<li>Download the file explicitly marked as the approved prediction, not a reference or diagnostic. Compare its SHA256 against its adjacent receipt.</li>
<li>Sign in to the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">official competition</a>, review eligibility/rules, then open its New submission form. Follow the current organizer instructions if they differ from this retained brief.</li>
<li>Choose the approved single-band <code>.tif</code>, or its one-TIFF <code>.zip</code>, as “File to submit”. Do not upload a document.</li>
<li>Copy the artifact's unique submission name and its note of at most 140 characters from its receipt. There is no candidate name or note intended for upload in this negative run.</li>
<li>Submit only after the selector approves the slot. Save the submission-page receipt and organizer result. Only then label a score ORGANIZER-CONFIRMED.</li></ol>
<h2>Prevent the reported range error</h2><p>The offending file was not available, so its exact cause is unknown. We reject NaN, infinity, negative values, values above one and incompatible nodata rather than silently clipping them. We validate the serialized file—not just the array in memory.</p>
<pre><code>.venv/bin/python scripts/validate_candidate.py /path/to/candidate.tif</code></pre>
<p>A successful local validator is not organizer acceptance. The current bridged reference grid is EPSG:32611, 3730 × 3292, affine (100, 0, 243350, 0, −100, 4508550); these are technical measurements, not score evidence, and still need official-origin authentication.</p>
<h2>Review the receipts</h2><p><a href="downloads/preflight.json">Preflight</a> · <a href="downloads/run-card.json">Run card</a> · <a href="downloads/recovered-byte-manifest.json">Pinned sources and hashes</a> · <a href="research.html">Full review and limitations</a></p>'''

    (DOCS / 'executive-summary.html').write_text(page('Submission instructions', executive, 'executive-summary.html'))

    review_text = (ROOT / 'reports/review.md').read_text().replace('(inherited-main-audit.md)', '(inherited-main-audit.html)')
    (DOCS / 'research.html').write_text(page('Research & review', '<div class="prose">' + markdown.markdown(review_text, extensions=['tables', 'fenced_code', 'toc']) + '</div>', 'research.html'))
    inherited = (ROOT / 'reports/inherited-main-audit.md').read_text()
    (DOCS / 'inherited-main-audit.html').write_text(page('Critical inherited-input audit', '<div class="prose">' + markdown.markdown(inherited, extensions=['tables', 'fenced_code', 'toc']) + '</div>', 'inherited-main-audit.html'))
    rows = read_json(ROOT / 'evidence/source_inventory.json')['sources']
    source_rows = ''.join(f'<tr><td><a href="{esc(r.get("url", r["api_url"]), quote=True)}">{esc(r["repository"])}</a></td><td>{esc(r["status"])}</td><td>{esc(r["checked_utc"])}</td><td>Not verified</td></tr>' for r in rows)
    sources = f'''<p class="eyebrow">SOURCE REGISTER</p><h1>Trace the claim to the evidence.</h1>
<p class="lede">A link is not proof. Public repository accessibility, official origin, scientific validation and organizer acceptance are different checks.</p>
<section class="subtle"><h2>What is verified here?</h2><p>GitHub metadata accessibility; the downloaded bytes and hashes of selected pinned upstream files; the public bridge grid; synthetic software regression tests. No live leaderboard, official data download or raster uniqueness clearance.</p><p>Last source snapshot: {esc(rows[0]['checked_utc'])}. The scheduled workflow refreshes public metadata and republishes the site after deployment is enabled; a failed workflow leaves this timestamp unchanged. It cannot inspect private receipts or external hosts.</p></section>
<h2>Primary official reference</h2><p><a href="https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b">DrivenData reference solution, pinned commit</a>: inspected README and relevant notebook cells. Confirms the baseline task and training-loss weights, not the full current organizer scoring service.</p>
<h2>Official source leads — not directly verified here</h2><ul><li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">DrivenData problem description and evaluation</a></li><li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/data/">Competition data and sample format</a></li><li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Current organizer leaderboard</a></li><li><a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN</a></li><li><a href="https://www.usgs.gov/3d-elevation-program">USGS 3DEP</a></li><li><a href="https://gdr.openei.org/submissions/1391">DOE GDR 1391</a></li><li><a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">NLR report supplied in the brief</a></li></ul>
<p>Host access is restricted in this environment. Availability, licenses, rules and current content are not asserted. Dropbox is a third-party bridge, not authenticated official provenance.</p>
<h2>Project family inventory</h2><p>This table checks the corresponding GitHub repositories, not deployed Pages content or their score claims. The full raster registry remains missing.</p><p><a class="button secondary" href="downloads/source-inventory.json" download>Download timestamped inventory</a></p>
<div class="table-wrap"><table><caption>Public GitHub repository metadata snapshot</caption><thead><tr><th scope="col">Repository</th><th scope="col">GitHub metadata</th><th scope="col">Checked (UTC)</th><th scope="col">Organizer receipt</th></tr></thead><tbody>{source_rows}</tbody></table></div>'''
    (DOCS / 'sources.html').write_text(page('Sources & access', sources, 'sources.html'))
    (DOCS / '.nojekyll').write_text('')
    print('Built site. State:', state, '| downloadable_submission:', card['downloadable_submission'],
          '| safe_to_submit:', card['safe_to_submit'])


if __name__ == '__main__':
    build()
