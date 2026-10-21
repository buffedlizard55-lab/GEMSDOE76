#!/usr/bin/env python3
"""Check local navigation, fragment targets, downloads and blocked-state invariants."""
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit
from project import ROOT


class Document(HTMLParser):
    def __init__(self):
        super().__init__();self.links=[];self.ids=set();self.errors=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if 'id' in attrs:
            if attrs['id'] in self.ids:self.errors.append('duplicate id '+attrs['id'])
            self.ids.add(attrs['id'])
        if tag=='a' and 'href' in attrs:self.links.append(attrs['href'])
        if tag=='link' and 'href' in attrs:self.links.append(attrs['href'])
        if tag in ('script','img') and 'src' in attrs:self.links.append(attrs['src'])


def check_site(root=ROOT/'docs'):
    errors=[];documents={}
    for path in root.rglob('*.html'):
        doc=Document();doc.feed(path.read_text());documents[path.resolve()]=doc
        errors.extend(str(path)+': '+e for e in doc.errors)
    for path,doc in documents.items():
        for link in doc.links:
            url=urlsplit(link)
            if url.scheme or url.netloc:continue
            target=(path.parent/unquote(url.path)).resolve() if url.path else path
            if not target.is_relative_to(root.resolve()):
                errors.append(f'Link escapes published site: {path}: {link}');continue
            if not target.is_file():errors.append(f'Missing local link: {path}: {link}');continue
            if url.fragment and target in documents and unquote(url.fragment) not in documents[target].ids:
                errors.append(f'Missing fragment: {path}: {link}')
    for name in ('index.html','executive-summary.html'):
        text=(root/name).read_text()
        if 'OK TO DOWNLOAD' not in text.upper():
            errors.append(f'{name} lacks explicit submission status banner')
    card=json.loads((root/'downloads/run-card.json').read_text())
    if len(card.get('note',''))>140:errors.append('Note exceeds 140 characters')
    # Any raster/archive in docs/downloads must be listed in run-card*.json.
    allowed = set()
    cards = [card]
    for extra in sorted((root/'downloads').glob('run-card-*.json')) + [root/'downloads/run_card.json']:
        if not extra.is_file():
            continue
        try:
            cards.append(json.loads(extra.read_text()))
        except json.JSONDecodeError:
            errors.append(f'Unreadable run card: {extra}')
    for c in cards:
        for key in ('raster', 'raster_zip'):
            v = c.get(key)
            if v:
                allowed.add(v)
                if v.startswith('docs/'):
                    allowed.add(v[len('docs/'):])
    for p in root.rglob('*'):
        if p.suffix.lower() in ('.tif', '.tiff', '.zip'):
            rel = str(p.relative_to(root.resolve()))
            if rel not in allowed:
                errors.append(f'Unexpected raster/archive on blocked site: {rel}')
    return errors


if __name__=='__main__':
    errors=check_site()
    if errors:raise SystemExit('\n'.join(errors))
    print('Site checks passed: local links/fragments/downloads and explicit blocked status.')
