#!/usr/bin/env python3
"""Render a blocked, auditable static site; never fabricate a submission link."""
from __future__ import annotations
import html
import json
from pathlib import Path
import shutil
import sys
import markdown
from project import ROOT, read_json
from preflight import audit

DOCS=ROOT/'docs'


def page(title, body, active=''):
    links=[('index.html','Overview'),('executive-summary.html','How to submit'),
           ('research.html','Research & review'),('sources.html','Sources')]
    nav=''.join(f'<a href="{url}" '+('aria-current="page" ' if url==active else '')+f'>{text}</a>' for url,text in links)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="GEMSDOE76: audited fault-detection research, scientific prerequisites and explicit submission readiness.">
<title>{html.escape(title)} · GEMSDOE76</title><link rel="stylesheet" href="style.css"></head>
<body><a class="skip" href="#main">Skip to content</a><header><a class="brand" href="index.html">GEMS<span>DOE76</span></a><nav aria-label="Main">{nav}</nav></header>
<main id="main">{body}</main><footer><strong>Evidence before confidence.</strong> No organizer-confirmed result or weekly-slot approval.
<a href="https://github.com/buffedlizard55-lab/GEMSDOE76">Repository</a> · <a href="downloads/run-card.json">JSON run card</a></footer></body></html>'''


def run_card(preflight):
    return {
        'run_id':'gems76-preflight-20261021',
        'hypothesis':'Conditional proposal A: concordant displacement of magnetic and radiometric contacts; no lane assigned or experiment executed.',
        'mechanism':'Buried cross-cutting faults may offset pre-existing lithologic contacts without a surface scarp; hypothesis only.',
        'non_fault_mimic':'Channel-alluvium boundaries and airborne survey line-leveling seams.',
        'holdout':{'evidence_class':'HOLDOUT-DTI','status':'not-run',
                   'evaluator_version':'gems57-pooled-hide-v2',
                   'withheld_positive_pixels':None,'dti':None,'ci95':None,
                   'current_best_reproduced':False,'feature_canaries':'not-run'},
        'registry':{'surface_rank_correlation':None,'surface_forward_overlap_3px':None,
                    'final_dot_rank_correlation':None,'final_dot_forward_overlap_3px':None,
                    'status':'not-run: no candidate and no complete scoped raster inventory',
                    'duplicate':None,'uniqueness_cleared':False,
                    'limits':{'rank_correlation_stop_above':0.90,'forward_overlap_stop_above':0.70}},
        'raster_sha256':None,
        'validator':{'status':'not-run: no generated candidate raster',
                     'no_nan_inside_footprint':None,'all_values_in_0_1':None,
                     'crs_matches':None,'shape_matches':None,'transform_matches':None,
                     'reference_only_grid_audit':preflight['reference_grid']},
        'submission_name':None,
        'note':'Negative preflight: lane, cached arrays, current raster registry and matched holdout evidence missing. Do not submit.',
        'verdict':'negative','safe_to_submit':False,'downloadable_submission':False,
        'experiments_run':0,'weekly_slots_used':0,'selector_approved':False,
        'blockers':preflight['blockers']}


def build():
    report=audit()
    # This site intentionally supports only this negative review. A later release must
    # implement and test an evidence-bound approval flow, not flip a display boolean.
    if report['status']!='blocked' or report['safe_to_submit']:
        raise ValueError('This negative-review renderer cannot publish an approved candidate.')
    downloads=DOCS/'downloads';downloads.mkdir(parents=True,exist_ok=True)
    if any(p.suffix.lower() in ('.tif','.tiff','.zip') for p in DOCS.rglob('*')):
        raise ValueError('Unexpected raster/archive in blocked site. Inspect it; do not publish silently.')
    card=run_card(report)
    (downloads/'run-card.json').write_text(json.dumps(card,indent=2,allow_nan=False)+'\n')
    (downloads/'preflight.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    shutil.copyfile(ROOT/'evidence/source_inventory.json',downloads/'source-inventory.json')
    shutil.copyfile(ROOT/'evidence/upstream/recovery.json',downloads/'recovered-byte-manifest.json')
    if (ROOT/'evidence/verification.json').is_file():
        shutil.copyfile(ROOT/'evidence/verification.json',downloads/'verification.json')
    (downloads/'review.md').write_text((ROOT/'reports/review.md').read_text())
    checks=''.join('<li>'+html.escape(b)+'</li>' for b in report['blockers'])
    overview=f'''<section class="hero"><p class="eyebrow">GEOLOGICAL FAULT DETECTION · AUDIT-FIRST RESEARCH</p>
<h1>A defensible submission.<br>Not just another TIFF.</h1>
<p class="lede">Testing new fault-discovery mechanisms without copying prior predictions, leaking catalogue labels, or inventing leaderboard results.</p></section>
<section class="notice" aria-labelledby="status"><p class="eyebrow">CURRENT DECISION · NEGATIVE</p>
<h2 id="status">No submission TIFF is available. Do not submit.</h2>
<p>The required scientific checks could not run. A reference raster, renamed archive or random-dot file would not satisfy the request.</p>
<div class="actions"><span class="disabled" role="status">TIFF download unavailable — prerequisites missing</span><a class="button secondary" href="downloads/run-card.json" download>Download negative run card</a></div>
<p class="fine">No experiment executed. No weekly slot used. Format validity alone never authorizes a submission.</p></section>
<div class="grid"><article><p class="label">SCIENTIFIC QUESTION</p><h2>Why did H33 help?</h2><p>Inherited evidence points to a sparse subset of an existing geological signal. Reduced redundant emission is a plausible metric benefit, not proof of causation.</p><a href="research.html">Read the H33 evidence →</a></article>
<article><p class="label">NEXT RESEARCH</p><h2>Contacts, not copies.</h2><p>Four conditional hypotheses target displaced contacts, signed alteration, drainage disequilibrium and edge-termination asymmetry. None is validated or assigned as this session’s lane.</p><a href="research.html#conditional-geological-hypotheses-generated-before-method-implementation">Review hypotheses →</a></article>
<article><p class="label">AUDIT TRAIL</p><h2>Know what was checked.</h2><p>Public metadata for all 78 named project repositories, pinned template modules and bridge-grid checks. Not a full raster uniqueness audit or live leaderboard verification.</p><a href="sources.html">Inspect sources →</a></article></div>
<section><h2>What stops a real submission?</h2><ul class="checklist">{checks}</ul>
<p><a href="executive-summary.html">Exact release and submission sequence →</a></p></section>
<section class="subtle"><h2>Evidence, with boundaries.</h2><p>The initial checkout had only a README. Shared tools and reference inputs are recovered; the claimed ready-to-train pipeline did not exist here. The main goal—a unique, validated downloadable prediction TIFF—remains unmet.</p><p>Organizer pages and external data hosts cannot be inspected from this environment. Historic scores supplied in the project brief are unverified; no leaderboard improvement is claimed.</p></section>'''
    (DOCS/'index.html').write_text(page('Submission readiness',overview,'index.html'))
    executive='''<p class="eyebrow">EXECUTIVE SUMMARY</p><h1>How to make a competition submission</h1>
<section class="notice"><h2>STOP: there is currently no file to upload.</h2><p>Do not submit the reference TIFFs, the JSON run card, or this webpage. No generated prediction has passed the required gates. This page is a future procedure, not approval.</p><a class="button secondary" href="downloads/run-card.json" download>Download the current negative decision</a></section>
<h2>Before a file can be released</h2><ol class="steps">
<li><strong>Establish inputs and lane.</strong> Resolve the parallel-run method assignment, place hash-pinned shared feature caches, authenticate sample/catalogue and data eligibility, and refresh the complete scoped raster registry.</li>
<li><strong>Validate science.</strong> Run feature-alone leakage canaries, buffered whole-segment spatial hide-and-recover, and a frozen current-best comparator. Every catalogue feature must use visible faults only. Pool DTI components and report version, withheld positives and 95% confidence intervals.</li>
<li><strong>Prove distinctness in the accessible scope.</strong> Check the surface before placement and the final dots. Stop if rank correlation exceeds 0.90 or forward dot overlap within 3 pixels exceeds 70% against any prior. Missing priors are not a clearance.</li>
<li><strong>Package once, without silent repairs.</strong> Use the shared writer for single-band float32 GeoTIFF and, optionally, a ZIP containing only that TIFF. Predictions must already be finite and in [0,1]. Zero the exterior explicitly; mask visible catalogue pixels exactly. Verify CRS, shape and transform against the authenticated format.</li>
<li><strong>Separate selection from generation.</strong> Require a documented holdout improvement against the current best and selector approval. Check current contest rules and the remaining weekly cap on the organizer’s submission page. No slot is authorized here.</li></ol>
<h2>Only after a genuinely approved file is published</h2><ol class="steps">
<li>Download the file explicitly marked as the approved prediction, not a reference or diagnostic. Compare its SHA256 against its adjacent receipt.</li>
<li>Sign in to the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">official competition</a>, review eligibility/rules, then open its New submission form. Follow the current organizer instructions if they differ from this retained brief.</li>
<li>Choose the approved single-band <code>.tif</code>, or its one-TIFF <code>.zip</code>, as “File to submit”. Do not upload a document.</li>
<li>Copy the artifact’s unique submission name and its note of at most 140 characters from its receipt. There is no candidate name or note intended for upload in this negative run.</li>
<li>Submit only after the selector approves the slot. Save the submission-page receipt and organizer result. Only then label a score ORGANIZER-CONFIRMED.</li></ol>
<h2>Prevent the reported range error</h2><p>The offending file was not available, so its exact cause is unknown. We reject NaN, infinity, negative values, values above one and incompatible nodata rather than silently clipping them. We validate the serialized file—not just the array in memory.</p>
<pre><code>.venv/bin/python scripts/validate_candidate.py /path/to/candidate.tif</code></pre>
<p>A successful local validator is not organizer acceptance. The current bridged reference grid is EPSG:32611, 3730 × 3292, affine (100, 0, 243350, 0, −100, 4508550); these are technical measurements, not score evidence, and still need official-origin authentication.</p>
<h2>Review the receipts</h2><p><a href="downloads/preflight.json">Preflight</a> · <a href="downloads/recovered-byte-manifest.json">Pinned sources and hashes</a> · <a href="research.html">Full review and limitations</a></p>'''
    (DOCS/'executive-summary.html').write_text(page('Submission instructions',executive,'executive-summary.html'))
    research=markdown.markdown((ROOT/'reports/review.md').read_text(),extensions=['tables','fenced_code','toc'])
    (DOCS/'research.html').write_text(page('Research & review','<div class="prose">'+research+'</div>','research.html'))
    rows=read_json(ROOT/'evidence/source_inventory.json')['sources']
    source_rows=''.join(f'<tr><td><a href="{html.escape(r.get("url",r["api_url"]),quote=True)}">{html.escape(r["repository"])}</a></td><td>{html.escape(r["status"])}</td><td>{html.escape(r["checked_utc"])}</td><td>Not verified</td></tr>' for r in rows)
    sources=f'''<p class="eyebrow">SOURCE REGISTER</p><h1>Trace the claim to the evidence.</h1>
<p class="lede">A link is not proof. Public repository accessibility, official origin, scientific validation and organizer acceptance are different checks.</p>
<section class="subtle"><h2>What is verified here?</h2><p>GitHub metadata accessibility; the downloaded bytes and hashes of selected pinned upstream files; the public bridge grid; synthetic software regression tests. No live leaderboard, official data download or raster uniqueness clearance.</p><p>Last source snapshot: {html.escape(rows[0]['checked_utc'])}. The scheduled workflow refreshes public metadata and republishes the site after deployment is enabled; a failed workflow leaves this timestamp unchanged. It cannot inspect private receipts or external hosts.</p></section>
<h2>Primary official reference</h2><p><a href="https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b">DrivenData reference solution, pinned commit</a>: inspected README and relevant notebook cells. Confirms the baseline task and training-loss weights, not the full current organizer scoring service.</p>
<h2>Official source leads — not directly verified here</h2><ul><li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">DrivenData problem description and evaluation</a></li><li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/data/">Competition data and sample format</a></li><li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Current organizer leaderboard</a></li><li><a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN</a></li><li><a href="https://www.usgs.gov/3d-elevation-program">USGS 3DEP</a></li><li><a href="https://gdr.openei.org/submissions/1391">DOE GDR 1391</a></li><li><a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">NLR report supplied in the brief</a></li></ul>
<p>Host access is restricted in this environment. Availability, licenses, rules and current content are not asserted. Dropbox is a third-party bridge, not authenticated official provenance.</p>
<h2>Project family inventory</h2><p>This table checks the corresponding GitHub repositories, not deployed Pages content or their score claims. The full raster registry remains missing.</p><p><a class="button secondary" href="downloads/source-inventory.json" download>Download timestamped inventory</a></p>
<div class="table-wrap"><table><caption>Public GitHub repository metadata snapshot</caption><thead><tr><th scope="col">Repository</th><th scope="col">GitHub metadata</th><th scope="col">Checked (UTC)</th><th scope="col">Organizer receipt</th></tr></thead><tbody>{source_rows}</tbody></table></div>'''
    (DOCS/'sources.html').write_text(page('Sources & access',sources,'sources.html'))
    (DOCS/'.nojekyll').write_text('')
    print('Built four blocked-status pages and audit downloads. No prediction TIFF published.')


if __name__=='__main__':
    build()
