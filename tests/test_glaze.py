import unittest, tempfile, json, threading, urllib.request, urllib.error, subprocess
from pathlib import Path
from datetime import datetime,timedelta
from unittest.mock import patch
from glaze import dashboard as d, config, monitor

class GlazeTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.reports=self.root/'reports';self.reports.mkdir()
  self.c={'timezone':'UTC','targets':[{'label':'Home','url':'https://example.com/','expected_status':200}], 'browser':{'enabled':True,'url':'https://example.com/','fields':[{'name':'username','type':'text'}]}}
  self.cfg=self.root/'config.json';self.cfg.write_text(json.dumps(self.c))
  for module,attr,value in [(d,'ROOT',self.root),(d,'URLS',{'https://example.com/':'Home'}),(d,'BROWSER',self.c['browser']),(config,'CONFIG',self.cfg),(monitor,'ROOT',self.root)]:
   p=patch.object(module,attr,value);p.start();self.addCleanup(p.stop)
  self.now=datetime.now(d.TZ);self.date=self.now.strftime('%Y-%m-%d')
 def log(self,body,browser=False):
  (self.reports/(('browser-' if browser else '')+self.date+'.log')).write_text(body)
 def row(self,status='PASS',seconds='1.0',when=None):
  return f'{(when or self.now).isoformat()} | {status} | https://example.com/ | HTTP=200 | seconds={seconds} | curl=0\n'
 def test_config_valid(self):self.assertEqual(config.load()['targets'][0]['label'],'Home')
 def test_reject_credentials_and_http(self):
  for url in ['http://example.com/','https://user:pass@example.com/']:
   self.c['targets'][0]['url']=url;self.cfg.write_text(json.dumps(self.c))
   with self.assertRaises(ValueError):config.load()
 def test_duplicate_targets(self):
  self.c['targets']*=2;self.cfg.write_text(json.dumps(self.c))
  with self.assertRaises(ValueError):config.load()
 def test_metrics_and_malformed(self):
  self.log(self.row(seconds='1')+self.row('FAIL','3')+'bad line\n')
  data=d.collect();self.assertEqual(data['counts'],{'PASS':1,'FAIL':1,'BLOCKED':0});self.assertEqual(data['average'],2);self.assertEqual(data['p95'],3);self.assertEqual(data['skipped'],1)
 def test_stale_and_missing(self):
  self.log(self.row(when=self.now-timedelta(minutes=11)))
  data=d.collect();self.assertEqual(data['latest'][0]['state'],'STALE');self.assertEqual(data['latest'][1]['state'],'NO DATA')
 def test_nonfinite_time_and_future(self):
  self.log(self.row(seconds='nan')+self.row(when=self.now+timedelta(days=1)))
  data=d.collect();self.assertEqual(len(data['rows']),1);self.assertIsNone(data['average']);json.dumps(data,allow_nan=False)
 def test_symlink_report_ignored(self):
  target=self.root/'secret';target.write_text(self.row());(self.reports/(self.date+'.log')).symlink_to(target)
  self.assertEqual(d.collect()['rows'],[])
 def test_browser_disabled_excluded(self):
  self.log(f'{self.now.isoformat()} | PASS | fields rendered\n',True)
  with patch.object(d,'BROWSER',{'enabled':False}):self.assertEqual(len(d.collect()['latest']),1);self.assertEqual(d.collect()['rows'],[])
 def test_fields(self):
  p=monitor.Fields();p.feed('<input name="username"><input type="password" name="password">');self.assertIn(('password','password'),p.found);self.assertIn(('username','text'),p.found)
 def test_http_failure_and_https_flags(self):
  with patch('glaze.monitor.shutil.which',return_value='/usr/bin/curl'),patch('glaze.monitor.subprocess.run',return_value=subprocess.CompletedProcess([],60,'000|0.2|','')) as run:
   monitor.http(self.c)
  args=run.call_args.args[0];self.assertIn('--proto',args);self.assertIn('=https',args);self.assertNotIn('-k',args);self.assertEqual(args[1],'-q')
  self.assertIn(' | FAIL | ',next(self.reports.glob('*.log')).read_text())
 def test_access_and_api(self):
  self.log(self.row())
  with patch.object(d,'TOKEN','x'*43,create=True):
   server=d.ThreadingHTTPServer(('127.0.0.1',0),d.Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
   def get(path,host='127.0.0.1:18765'):
    q=urllib.request.Request(f'http://127.0.0.1:{server.server_port}'+path,headers={'Host':host})
    try:
     with urllib.request.urlopen(q) as r:return r.status,r.read(),r.headers
    except urllib.error.HTTPError as e:return e.code,e.read(),e.headers
   try:
    self.assertEqual(get('/')[0],403);self.assertEqual(get('/'+'x'*43,'evil.test')[0],403);self.assertEqual(get('/../../reports')[0],403)
    code,body,headers=get('/'+'x'*43);self.assertEqual(code,200);self.assertIn(b'Glaze',body);self.assertEqual(headers['Cache-Control'],'no-store')
    code,body,_=get('/'+'x'*43+'?hours=24');self.assertEqual(code,200);self.assertEqual(json.loads(body)['counts']['PASS'],1)
   finally:server.shutdown();server.server_close();thread.join()
if __name__=='__main__':unittest.main()
