#!/usr/bin/env python3
"""Validate exported links, alternates, hashes, source kit and privacy boundary."""
import hashlib,json,re,sys,zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse,urljoin,unquote
ROOT=Path(__file__).resolve().parents[1];SITE=ROOT/'build/site/distributed-systems-lab'
class Page(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.ids=set();self.h1=0;self.lang='';self.alts={};self.title=False
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='h1':self.h1+=1
        if tag=='html':self.lang=a.get('lang','')
        if tag=='title':self.title=True
        if a.get('id'):self.ids.add(a['id'])
        if tag=='link' and a.get('rel')=='alternate':self.alts[a.get('hreflang')]=a.get('href')
        for k in ('src','href'):
            if a.get(k):self.links.append(a[k])
def check():
    errors=[];pages={}
    for p in SITE.rglob('*.html'):
        q=Page();q.feed(p.read_text());pages[p]=q
        if not q.title or not q.lang:errors.append(f'metadata: {p.name}')
        if p!=SITE/'index.html':
            if q.h1!=1:errors.append(f'h1: {p}')
            if set(q.alts)!={'en-US','zh-CN','x-default'}:errors.append(f'alternates: {p}')
            for link in q.alts.values():
                parsed=urlparse(link);dest=ROOT/'build/site'/parsed.path.lstrip('/')
                if dest.is_dir():dest=dest/'index.html'
                if not dest.exists():errors.append(f'alternate target: {link}')
    for p,q in pages.items():
        for link in q.links:
            u=urlparse(urljoin('https://lynnlee1229.github.io/distributed-systems-lab/'+str(p.relative_to(SITE)),link))
            if u.scheme not in ('https','http') or u.netloc!='lynnlee1229.github.io' or not u.path.startswith('/distributed-systems-lab/'):continue
            dst=ROOT/'build/site'/unquote(u.path).lstrip('/')
            if dst.is_dir():dst=dst/'index.html'
            if not dst.exists():errors.append(f'link: {p.relative_to(SITE)} -> {link}')
            elif u.fragment and dst in pages and unquote(u.fragment) not in pages[dst].ids:errors.append(f'anchor: {link}')
    manifest=json.loads((SITE/'export-manifest.json').read_text())
    actual={str(p.relative_to(SITE)) for p in SITE.rglob('*') if p.is_file() and p.name!='export-manifest.json'}
    if actual!={f['path'] for f in manifest['files']}:errors.append('export file inventory mismatch')
    for f in manifest['files']:
        if hashlib.sha256((SITE/f['path']).read_bytes()).hexdigest()!=f['sha256']:errors.append('hash: '+f['path'])
    forbidden=re.compile(r'/[U]sers/|/[h]ome/[^/\s]+/|gh[op]_[A-Za-z0-9]{20,}|s[k]-proj-|BEGIN [A-Z ]*PRIVATE KEY|m[a]ilto:|t[e]l:|https?://(?:[^\s"<>]+\.)?(?:notion\.so|drive\.google\.com)/')
    def scan(name,raw):
        if forbidden.search(raw.decode('utf-8',errors='replace')):errors.append('privacy pattern: '+name)
    for p in SITE.rglob('*'):
        if p.is_file() and p.suffix in {'.html','.json','.mjs','.css','.svg','.xml'}:scan(str(p.relative_to(SITE)),p.read_bytes())
    with zipfile.ZipFile(SITE/'downloads/distributed-systems-lab.zip') as z:
        names=z.namelist()
        for n in names:
            if not n.startswith('distributed-systems-lab/') or '..' in Path(n).parts or any(x in Path(n).parts for x in ('build','.git','.venv','__pycache__')):errors.append('unsafe zip member: '+n)
            scan(n,z.read(n))
        for required in ('lab/runtime.py','scripts/run_all.py','scripts/check_site.py','tests/checker.test.mjs','results/experiments.json'):
            if 'distributed-systems-lab/'+required not in names:errors.append('missing kit source: '+required)
    report=json.loads((SITE/'results/experiments.json').read_text())
    if len(report['repetitions'])!=3:errors.append('baseline must have 3 repetitions')
    if any(not r[k].get('assertions_passed') for r in report['repetitions'] for k in ('quorum','retry','fencing')):errors.append('failed evidence assertion')
    if len(pages)!=25:errors.append(f'expected 24 bilingual pages + redirect, got {len(pages)}')
    if errors:raise SystemExit('\n'.join(errors))
    print(f'PASS: {len(pages)} pages, bilingual deep links, alternates, privacy patterns, manifest hashes, complete standalone ZIP, three real repetitions.')
if __name__=='__main__':check()
