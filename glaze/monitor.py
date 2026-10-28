"""One bounded monitoring run. Schedule locally, never through the dashboard."""
import argparse, fcntl, os, subprocess, shutil, tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
TZ=ZoneInfo('UTC')
from html.parser import HTMLParser
from .config import ROOT, load

def write(kind, message):
    reports=ROOT/'reports';reports.mkdir(parents=True,exist_ok=True);reports.chmod(0o700)
    name=('browser-' if kind=='browser' else '')+datetime.now(TZ).strftime('%Y-%m-%d')+'.log'
    p=reports/name
    if p.is_symlink(): raise RuntimeError('Refusing symlink log')
    with p.open('a') as f:f.write(datetime.now(TZ).isoformat()+' | '+message+'\n')
    p.chmod(0o600)

class Fields(HTMLParser):
    def __init__(self): super().__init__();self.found=set()
    def handle_starttag(self,tag,attrs):
        if tag=='input':
            a=dict(attrs);self.found.add((a.get('name',''),a.get('type','text').lower()))

def http(c):
    curl=shutil.which('curl')
    if not curl: raise RuntimeError('curl is required')
    for t in c['targets']:
        try:
            p=subprocess.run([curl,'-q','--proto','=https','--noproxy','*','-sS','-o',os.devnull,'--connect-timeout','10','--max-time','30','-w','%{http_code}|%{time_total}|%{redirect_url}',t['url']],capture_output=True,text=True,timeout=35)
            parts=p.stdout.strip().split('|',2)
            code,seconds,redirect=(parts+['','',''])[:3]
            # curl errors never grant PASS. Do not retain response bodies or stderr.
            status='PASS' if p.returncode==0 and code==str(t['expected_status']) and redirect==t.get('expected_redirect','') else 'FAIL'
            write('http',f'{status} | {t["url"]} | HTTP={code} | seconds={seconds} | curl={p.returncode}')
        except (subprocess.TimeoutExpired,OSError):
            write('http',f'BLOCKED | {t["url"]} | HTTP=000 | seconds=nan | curl=timeout-or-execution-error')

def browser(c):
    b=c.get('browser',{})
    if not b.get('enabled'): return
    # Snap Chromium can access its common directory; each run has a fresh profile.
    work=Path.home()/'snap/chromium/common/glaze';work.mkdir(parents=True,exist_ok=True);work.chmod(0o700)
    with tempfile.TemporaryDirectory(prefix='run-',dir=work) as tmp:
        path=Path(tmp)
        with (path/'page.html').open('w+') as out:
            try:
                p=subprocess.run(['/usr/bin/timeout','-k','5s','60s',b.get('executable','/snap/bin/chromium'),'--headless','--disable-gpu','--no-first-run','--user-data-dir='+str(path/'profile'),'--dump-dom',b['url']],stdout=out,stderr=subprocess.DEVNULL,timeout=70)
                if p.returncode: write('browser','BLOCKED | browser execution failed');return
                out.seek(0);text=out.read(2_000_001)
                if len(text)>2_000_000: write('browser','BLOCKED | page exceeds parser limit');return
                parser=Fields();parser.feed(text)
                ok=all((f['name'],f['type'].lower()) in parser.found for f in b['fields'])
                write('browser',('PASS' if ok else 'FAIL')+' | configured fields '+('rendered' if ok else 'missing'))
            except (OSError,subprocess.TimeoutExpired): write('browser','BLOCKED | browser unavailable or timed out')

def main():
    global TZ
    os.umask(0o077)
    parser=argparse.ArgumentParser();parser.add_argument('kind',choices=['http','browser']);args=parser.parse_args()
    c=load();TZ=ZoneInfo(c.get('timezone','UTC'));ROOT.mkdir(parents=True,exist_ok=True);ROOT.chmod(0o700)
    with (ROOT/(args.kind+'.lock')).open('w') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        (http if args.kind=='http' else browser)(c)
if __name__=='__main__':main()
