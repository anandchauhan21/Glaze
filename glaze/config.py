"""Local configuration; nothing is read from the network."""
import json, os
from pathlib import Path
from urllib.parse import urlsplit
ROOT = Path(os.environ.get('GLAZE_DATA_DIR', str(Path.home()/'.local/state/glaze'))).expanduser()
CONFIG = Path(os.environ.get('GLAZE_CONFIG', str(Path.home()/'.config/glaze/config.json'))).expanduser()

def load():
    c=json.loads(CONFIG.read_text())
    targets=c.get('targets',[])
    if not 1 <= len(targets) <= 20: raise ValueError('Configure 1–20 HTTPS targets')
    seen=set()
    for t in targets:
        u=urlsplit(t['url'])
        if u.scheme!='https' or not u.hostname or u.username or u.password or u.fragment or any(x in t['url'] for x in ('\n','\r',' | ')):
            raise ValueError('Targets must be HTTPS URLs without credentials, fragments or log delimiters')
        if t['url'] in seen: raise ValueError('Duplicate target URL')
        seen.add(t['url'])
        if not isinstance(t.get('expected_status'),int) or not 100<=t['expected_status']<=599: raise ValueError('Invalid expected_status')
        if not isinstance(t.get('label'),str) or not 1<=len(t['label'])<=80: raise ValueError('Invalid label')
        red=t.get('expected_redirect','')
        if red and (urlsplit(red).scheme!='https' or any(x in red for x in ('\r','\n',' | '))): raise ValueError('Invalid redirect expectation')
    b=c.get('browser',{})
    if b.get('enabled'):
        if b.get('url') not in seen: raise ValueError('Browser URL must be a configured HTTPS target')
        if not isinstance(b.get('fields'),list) or not b['fields']: raise ValueError('Browser fields required')
        for f in b['fields']:
            if not isinstance(f.get('name'),str) or not isinstance(f.get('type'),str): raise ValueError('Each field needs name and type')
        executable=Path(b.get('executable','/snap/bin/chromium'))
        if not executable.is_absolute(): raise ValueError('Browser executable must be absolute')
    return c
