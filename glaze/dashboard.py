#!/usr/bin/env python3
"""Private log-only monitoring dashboard. Python standard library only."""
import os, re, json, math, secrets, hmac
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from urllib.parse import urlsplit, parse_qs
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from .config import ROOT, load
from . import autostart
CSRF = secrets.token_urlsafe(32)
CONFIG = {}
TZ = ZoneInfo('UTC')
URLS = {}
BROWSER = {}

def collect(hours=24):
    now = datetime.now(TZ); start = now-timedelta(hours=hours)
    rows=[]; skipped=0
    for day in range(8):
        date=(now-timedelta(days=day)).strftime('%Y-%m-%d')
        for kind, name in [('http',date+'.log'),('browser','browser-'+date+'.log')]:
            p=ROOT/'reports'/name
            if p.is_symlink() or not p.is_file(): continue
            # Bound reads; never expose arbitrary paths or raw log content.
            with p.open('rb') as f:
                size=os.fstat(f.fileno()).st_size
                offset=max(0,size-2_000_000); f.seek(offset)
                if offset: f.readline()
                lines=f.read(2_000_000).decode('utf-8','replace').splitlines()
            for line in lines:
                try:
                    a=line.split(' | '); t=datetime.fromisoformat(a[0])
                    if t.tzinfo is None: raise ValueError()
                    if not start <= t <= now: continue
                    status=a[1]
                    if status not in ('PASS','FAIL','BLOCKED'): raise ValueError()
                    key=a[2] if kind=='http' else 'browser'
                    if kind=='http' and key not in URLS: continue
                    if kind=='browser' and not BROWSER.get('enabled'): continue
                    vals=dict(x.split('=',1) for x in a[3:] if '=' in x)
                    seconds=None
                    if kind=='http':
                        seconds=float(vals.get('seconds','nan'))
                        if not math.isfinite(seconds) or seconds<0: seconds=None
                    rows.append(dict(time=t.isoformat(),stamp=t.timestamp(),status=status,key=key,kind=kind,seconds=seconds,code=vals.get('HTTP','—')))
                except (ValueError,IndexError): skipped+=1
    rows.sort(key=lambda r:r['stamp'])
    latest=[]
    for key,label in list(URLS.items())+([('browser',BROWSER.get('label','Browser rendering'))] if BROWSER.get('enabled') else []):
        rr=[r for r in rows if r['key']==key]; last=rr[-1] if rr else None
        age=(now.timestamp()-last['stamp']) if last else None
        limit=1200 if key=='browser' else 600
        state='NO DATA' if not last else ('STALE' if age>limit else last['status'])
        latest.append(dict(label=label,key=key,state=state,last=last,age=age))
    counts={s:sum(r['status']==s for r in rows) for s in ('PASS','FAIL','BLOCKED')}
    timing=sorted(r['seconds'] for r in rows if r['kind']=='http' and r['seconds'] is not None)
    return dict(timezone=str(TZ),now=now.isoformat(),hours=hours,rows=rows,latest=latest,counts=counts,skipped=skipped,
                average=sum(timing)/len(timing) if timing else None,p95=timing[max(0,math.ceil(len(timing)*.95)-1)] if timing else None)

PAGE=r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Glaze by Sugarcoat | Service overview</title><style>
:root{font-family:Segoe UI,Arial,sans-serif;color:#203047;background:#f4f4fa}*{box-sizing:border-box}body{margin:0}.top{background:#16182f;color:white;padding:20px 28px;display:flex;justify-content:space-between;align-items:center;border-bottom:4px solid #8070e8}.brand{font-size:19px;font-weight:750}.sub{font-size:12px;color:#c5d0dc;margin-top:5px}main{max-width:1480px;margin:auto;padding:24px}.head{display:flex;justify-content:space-between;align-items:center;gap:16px}h1{font-size:27px;margin:0 0 6px}h2{font-size:16px;margin:0 0 6px}p{color:#68788c;font-size:13px;margin:5px 0 16px}select,button{border:1px solid #ccd5e1;border-radius:6px;background:white;padding:10px;color:#233750}button{cursor:pointer}.banner{padding:12px 16px;background:#e7f4ee;border-left:4px solid #168760;margin:18px 0;border-radius:5px;font-size:14px}.banner.warn{background:#fff0d4;border-color:#cd850a}.kpis{display:grid;grid-template-columns:repeat(5,1fr);gap:14px}.card,.panel{background:white;border:1px solid #e2e7ee;border-radius:9px;box-shadow:0 2px 4px #182e4810}.card{padding:19px}.label{font-size:12px;color:#6c7a8c;text-transform:uppercase;letter-spacing:.6px}.big{font-size:32px;font-weight:750;margin:12px 0 6px}.small{font-size:12px;color:#78889b}.grid{display:grid;grid-template-columns:2fr 1fr;gap:16px;margin-top:18px}.panel{padding:20px;min-width:0}.chart{height:260px;position:relative}canvas{width:100%;height:100%;display:block}.legend{display:flex;gap:15px;flex-wrap:wrap;font-size:12px;margin:10px 0}.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px}.status{padding:5px 9px;border-radius:5px;font-size:11px;font-weight:750;display:inline-block;background:#e9eef4;color:#677586}.PASS{background:#e4f4ec;color:#167752}.FAIL{background:#fde8e8;color:#b43b3b}.BLOCKED,.STALE{background:#fff1d5;color:#94600b}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:13px}th{text-align:left;color:#758399;font-size:11px;text-transform:uppercase;padding:13px 10px;border-bottom:1px solid #e3e9f0}td{padding:13px 10px;border-bottom:1px solid #eef1f5;white-space:nowrap}.foot{padding:18px 0;font-size:12px;color:#738195;line-height:1.6}.twocol{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:18px}.events{max-height:290px;overflow:auto}.empty{padding:45px;text-align:center;color:#7c8899}.controls{display:flex;gap:8px}#updated{font-size:12px;color:#bac9d8}.bar{height:9px;background:#edf1f6;border-radius:8px;overflow:hidden;margin-top:10px}.bar i{display:block;height:100%;background:#8070e8}.endpoint{margin-top:15px} @media(max-width:900px){.kpis{grid-template-columns:repeat(2,1fr)}.grid,.twocol{grid-template-columns:1fr}}@media(max-width:540px){main{padding:14px}.top{padding:16px}.head{align-items:flex-start;flex-direction:column}.big{font-size:27px}.card{padding:14px}#updated{max-width:130px;text-align:right}.chart{height:230px}}
</style></head><body><header class="top"><div><div class="brand"><span style="font-size:28px;letter-spacing:-1px">Glaze<span style="color:#a99aff">.</span></span> <span style="font-size:13px;font-weight:400;margin-left:10px">by Sugarcoat.tech</span></div><div class="sub">A clear view of your services · Read-only monitoring</div></div><div id="updated">Connecting…</div></header><main><div class="head"><div><h1>Service overview</h1><p>Availability, response time and browser checks in one view.</p></div><div class="controls"><select id="range" aria-label="Report period"><option value="1">Last hour</option><option value="24" selected>Last 24 hours</option><option value="168">Last 7 days</option></select><button id="refresh">Refresh</button></div></div><section class="panel" style="margin-top:16px"><div class="head"><div><h2>Auto-start Glaze</h2><p>Start this dashboard when the Jetson boots. Existing monitoring schedules are unchanged.</p></div><button id="autostart" role="switch" aria-checked="false" disabled>Checking…</button></div><p id="autostart-status" role="status" aria-live="polite">Checking local service…</p></section><div id="banner" class="banner">Loading recorded results…</div><div id="kpis" class="kpis"></div><div class="grid"><section class="panel"><h2>HTTP response time</h2><p>Total request duration in seconds · includes failed attempts with recorded timing</p><div class="legend" id="lines"></div><div class="chart"><canvas id="trend" aria-label="HTTP response-time line chart"></canvas></div></section><section class="panel"><h2>Recorded check outcomes</h2><p>HTTP and browser checks combined</p><div class="chart"><canvas id="donut" aria-label="Check outcomes doughnut chart"></canvas></div><div class="legend" id="outcomes"></div></section></div><section class="panel" style="margin-top:18px"><h2>Latest status by check</h2><p>HTTP becomes stale after 10 minutes; browser after 20 minutes.</p><div class="scroll"><table><thead><tr><th>Check</th><th>Current evidence</th><th>Last recorded</th><th>Response</th><th>HTTP</th></tr></thead><tbody id="latest"></tbody></table></div></section><div class="twocol"><section class="panel"><h2>Average response by page</h2><p>Measured request duration, not full page-load speed</p><div id="averages"></div></section><section class="panel"><h2>Recent failures & blocked checks</h2><p>Most recent 20 recorded exceptions in the selected period</p><div class="events" id="events"></div></section></div><div class="foot">Pass rate describes recorded samples, not guaranteed uptime. Missing runs are not counted as passes. Login tests only verify rendered fields; authentication, tenant isolation and application security are not tested. Times use the configured timezone. Refreshes every 60 seconds. <span id="parse"></span></div></main><script>
const $=id=>document.getElementById(id), colors=['#5b5bd6','#9673e8','#209baf','#c47732','#5d7cb9'];let data=null;
const el=(tag,text,cls)=>{let n=document.createElement(tag);n.textContent=text;if(cls)n.className=cls;return n};
const fmt=n=>n==null?'—':n.toFixed(2)+' s';const time=t=>new Date(t).toLocaleString('en-IN',{timeZone:data?.timezone||'UTC',day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit',second:'2-digit'});
function legend(id,items){$(id).replaceChildren();items.forEach(([label,color])=>{let s=el('span','');let d=el('i','','dot');d.style.background=color;s.append(d,document.createTextNode(label));$(id).append(s)})}
function canvas(id){let c=$(id),r=c.getBoundingClientRect(),d=devicePixelRatio||1;c.width=r.width*d;c.height=r.height*d;let x=c.getContext('2d');x.scale(d,d);return [x,r.width,r.height]}
function draw(){if(!data)return;let [x,w,h]=canvas('trend');let rr=data.rows.filter(r=>r.kind==='http'&&r.seconds!=null), left=42,right=w-14,top=15,bottom=h-30;
x.font='11px Segoe UI';if(!rr.length){x.fillStyle='#7b8898';x.fillText('No HTTP timing data in this period',20,80)}else{let max=Math.max(.1,...rr.map(r=>r.seconds))*1.15;let first=Math.min(...rr.map(r=>r.stamp)),last=Math.max(...rr.map(r=>r.stamp));if(first===last)last+=300;for(let i=0;i<=4;i++){let y=bottom-(bottom-top)*i/4;x.strokeStyle='#e7edf4';x.beginPath();x.moveTo(left,y);x.lineTo(right,y);x.stroke();x.fillStyle='#78879a';x.fillText((max*i/4).toFixed(1),4,y+4)}data.latest.filter(s=>s.key!=='browser').forEach((item,index)=>{let series=rr.filter(r=>r.key===item.key);x.strokeStyle=colors[index%colors.length];x.lineWidth=2;x.beginPath();let prev=null;series.forEach(r=>{let px=left+(r.stamp-first)/(last-first)*(right-left),py=bottom-r.seconds/max*(bottom-top);if(prev==null||r.stamp-prev>600)x.moveTo(px,py);else x.lineTo(px,py);prev=r.stamp});x.stroke();if(series.length===1){let r=series[0];x.fillStyle=colors[index%colors.length];x.beginPath();x.arc(left+(r.stamp-first)/(last-first)*(right-left),bottom-r.seconds/max*(bottom-top),3,0,Math.PI*2);x.fill()}});x.fillStyle='#78879a';x.fillText(time(first*1000),left,h-6);x.textAlign='right';x.fillText(time(last*1000),right,h-6);x.textAlign='left'}
let [c,cw,ch]=canvas('donut'),total=data.rows.length,vals=Object.values(data.counts),cs=['#1b9970','#dc5555','#e3aa2f'],start=-Math.PI/2,r=Math.min(cw,ch)*.32;c.lineWidth=25;vals.forEach((v,i)=>{if(!v)return;c.strokeStyle=cs[i];c.beginPath();c.arc(cw/2,ch/2,r,start,start+v/total*Math.PI*2);c.stroke();start+=v/total*Math.PI*2});if(!total){c.strokeStyle='#e8edf3';c.beginPath();c.arc(cw/2,ch/2,r,0,Math.PI*2);c.stroke()}c.fillStyle='#203047';c.font='bold 30px Segoe UI';c.textAlign='center';c.fillText(total,cw/2,ch/2+5);c.font='12px Segoe UI';c.fillStyle='#78879a';c.fillText('recorded checks',cw/2,ch/2+27)}
function render(d){data=d;let total=d.rows.length,pass=total?(100*d.counts.PASS/total).toFixed(1)+'%':'—';$('kpis').replaceChildren();[['Recorded checks',total,'Selected report period'],['Sample pass rate',pass,'Not an uptime guarantee'],['Failures / blocked',d.counts.FAIL+' / '+d.counts.BLOCKED,'Recorded outcomes'],['Average HTTP time',fmt(d.average),'All timed HTTP attempts'],['95th percentile',fmt(d.p95),'HTTP request duration']].forEach(([a,b,c])=>{let card=el('div','','card');card.append(el('div',a,'label'),el('div',String(b),'big'),el('div',c,'small'));$('kpis').append(card)});let attention=d.latest.filter(s=>s.state!=='PASS');$('banner').className='banner'+(attention.length?' warn':'');$('banner').textContent=attention.length?attention.length+' of '+d.latest.length+' checks need attention: failure, blocked, stale or no data.':'All '+d.latest.length+' configured checks have recent PASS evidence. Limited checks only.';$('updated').textContent='Updated '+time(d.now)+' '+d.timezone;$('latest').replaceChildren();d.latest.forEach(s=>{let tr=el('tr','');let status=el('td','');status.append(el('span',s.state,'status '+s.state));tr.append(el('td',s.label),status,el('td',s.last?time(s.last.time):'No data'),el('td',s.last?fmt(s.last.seconds):'—'),el('td',s.last&&s.key!=='browser'?s.last.code:'—'));$('latest').append(tr)});legend('lines',d.latest.filter(s=>s.key!=='browser').map((s,i)=>[s.label,colors[i%colors.length]]));legend('outcomes',Object.entries(d.counts).map(([k,v],i)=>[k+' '+v,['#1b9970','#dc5555','#e3aa2f'][i]]));let means=d.latest.filter(s=>s.key!=='browser').map(s=>{let a=d.rows.filter(r=>r.key===s.key&&r.seconds!=null);return [s.label,a.length?a.reduce((n,r)=>n+r.seconds,0)/a.length:null]});let max=Math.max(.01,...means.map(a=>a[1]||0));$('averages').replaceChildren();means.forEach(([name,v])=>{let n=el('div',name+' · '+fmt(v),'endpoint'),bar=el('div','','bar'),fill=el('i','');fill.style.width=(v==null?0:v/max*100)+'%';bar.append(fill);n.append(bar);$('averages').append(n)});let fails=d.rows.filter(r=>r.status!=='PASS').slice(-20).reverse();$('events').replaceChildren();if(!fails.length)$('events').append(el('div',total?'No recorded exceptions in this period.':'No data in this period.','empty'));fails.forEach(r=>{let n=el('p',time(r.time)+' · '+(d.latest.find(s=>s.key===r.key)?.label||'Check')+' · '+r.status);$('events').append(n)});$('parse').textContent=d.skipped?d.skipped+' unrecognized log lines excluded.':'';draw()}
let autoBusy=false,autoState=null;
const csrf='__GLAZE_CSRF__';
function showAuto(s){autoState=s;const b=$('autostart');b.setAttribute('aria-checked',String(s.enabled));b.textContent=s.enabled?'ON':'OFF';b.style.background=s.enabled?'#e4f4ec':'#eef1f5';b.disabled=autoBusy||!s.installed||(!s.linger&&!s.enabled);$('autostart-status').textContent=!s.installed?'One-time setup needed: install the Glaze viewer service.':!s.linger?'Boot setup incomplete: enable user lingering from the Jetson terminal.':s.enabled?'Auto-start enabled. Dashboard service: '+s.active+'.':'Auto-start disabled. The current dashboard stays running.';}
async function readAuto(){if(autoBusy)return;try{const r=await fetch(location.pathname+'?autostart=1',{cache:'no-store'});const s=await r.json();if(!r.ok)throw Error(s.error||'Service status unavailable');showAuto(s)}catch(e){$('autostart').disabled=true;$('autostart-status').textContent=e.message}}
$('autostart').onclick=async()=>{if(!autoState||autoBusy)return;autoBusy=true;$('autostart').disabled=true;try{const r=await fetch(location.pathname+'?autostart=1',{method:'POST',headers:{'Content-Type':'application/json','X-Glaze-CSRF':csrf},body:JSON.stringify({enabled:!autoState.enabled})});const s=await r.json();if(!r.ok)throw Error(s.error||'Auto-start update failed');autoBusy=false;showAuto(s)}catch(e){autoBusy=false;$('autostart').disabled=false;$('autostart-status').textContent=e.message}};
readAuto();setInterval(readAuto,60000);
async function load(){try{let response=await fetch(location.pathname+'?hours='+$('range').value,{cache:'no-store'});if(!response.ok)throw Error();render(await response.json())}catch(e){$('banner').className='banner warn';$('banner').textContent='Dashboard refresh failed. Displayed results may be old. Check the SSH tunnel.';$('updated').textContent='Refresh failed'}}$('range').onchange=load;$('refresh').onclick=load;window.addEventListener('resize',draw);load();setInterval(load,60000);
</script></body></html>'''

class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup(); self.connection.settimeout(10)
    def log_message(self,*args): pass
    def send_json(self, code, value):
        body=json.dumps(value).encode()
        self.send_response(code)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.end_headers(); self.wfile.write(body)
    def do_POST(self):
        host=self.headers.get('Host','')
        if host not in ('127.0.0.1:18765','localhost:18765'):
            self.send_error(403); return
        if self.headers.get('Origin') != 'http://'+host:
            self.send_error(403); return
        if not hmac.compare_digest(self.headers.get('X-Glaze-CSRF','').encode(),CSRF.encode()):
            self.send_error(403); return
        if not hmac.compare_digest(self.path.encode(),('/'+TOKEN+'?autostart=1').encode()):
            self.send_error(403); return
        if self.headers.get('Content-Type') != 'application/json' or self.headers.get('Transfer-Encoding'):
            self.send_error(415); return
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 1<=size<=256: raise ValueError()
            obj=json.loads(self.rfile.read(size))
            if not isinstance(obj,dict) or set(obj)!={'enabled'} or type(obj['enabled']) is not bool: raise ValueError()
        except (ValueError,UnicodeError):
            self.send_json(400,{'error':'Expected a boolean enabled value.'}); return
        try: self.send_json(200,autostart.set_enabled(obj['enabled']))
        except autostart.SetupRequired as exc: self.send_json(409,{'error':str(exc)})
        except autostart.ControlUnavailable as exc: self.send_json(503,{'error':str(exc)})
    def do_GET(self):
        if self.headers.get('Host') not in ('127.0.0.1:18765','localhost:18765'):
            self.send_error(403); return
        parsed=urlsplit(self.path)
        if not hmac.compare_digest(parsed.path.encode(),('/'+TOKEN).encode()):
            self.send_error(403); return
        if parsed.query == 'autostart=1':
            try: self.send_json(200, autostart.status())
            except autostart.ControlUnavailable as exc: self.send_json(503, {'error':str(exc)})
            return
        if parsed.query:
            args=parse_qs(parsed.query)
            try: hours=int(args.get('hours',['24'])[0])
            except ValueError: hours=24
            if hours not in (1,24,168): hours=24
            body=json.dumps(collect(hours),allow_nan=False).encode(); mime='application/json'
        else: body=PAGE.replace('__GLAZE_CSRF__',CSRF).encode(); mime='text/html; charset=utf-8'
        self.send_response(200)
        for k,v in {'Content-Type':mime,'Content-Length':str(len(body)),'Cache-Control':'no-store','Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"}.items(): self.send_header(k,v)
        self.end_headers(); self.wfile.write(body)

def main():
    global CONFIG, TZ, URLS, BROWSER, TOKEN
    CONFIG=load(); TZ=ZoneInfo(CONFIG.get('timezone','UTC'))
    URLS={t['url']:t['label'] for t in CONFIG['targets']}; BROWSER=CONFIG.get('browser',{})
    os.umask(0o077)
    (ROOT/'dashboard').mkdir(parents=True,exist_ok=True)
    (ROOT/'dashboard').chmod(0o700)
    tokenfile=ROOT/'dashboard/access-token'
    if tokenfile.is_symlink(): raise SystemExit('Refusing symlink token file')
    if not tokenfile.exists(): tokenfile.write_text(secrets.token_urlsafe(32))
    tokenfile.chmod(0o600); TOKEN=tokenfile.read_text().strip()
    if not re.fullmatch(r'[A-Za-z0-9_-]{32,100}',TOKEN): raise SystemExit('Invalid access token')
    server=ThreadingHTTPServer(('127.0.0.1',18765),Handler)
    print('Private browser URL: http://127.0.0.1:18765/'+TOKEN,flush=True)
    print('Glaze dashboard running. Ctrl+C stops the viewer only.',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__=='__main__': main()
