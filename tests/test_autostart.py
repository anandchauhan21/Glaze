import json, threading, unittest, urllib.request, urllib.error
from unittest.mock import patch
from subprocess import CompletedProcess
from glaze import autostart as a, dashboard as d

def result(text='',code=0):return CompletedProcess([],code,text,'')
class AutoTests(unittest.TestCase):
 def test_status(self):
  with patch.object(a,'run',side_effect=[result('LoadState=loaded\nActiveState=active\nUnitFileState=enabled\n'),result('yes\n')]):
   self.assertTrue(a.status()['boot_ready'])
 def test_only_fixed_enable_no_start(self):
  before={'installed':True,'enabled':False,'linger':True};after=dict(before,enabled=True)
  with patch.object(a,'status',side_effect=[before,after]),patch.object(a,'run',return_value=result()) as run:
   self.assertTrue(a.set_enabled(True)['enabled'])
   self.assertEqual(run.call_args.args[0],['/usr/bin/systemctl','--user','--no-ask-password','enable','glaze-dashboard.service'])
 def test_disable_does_not_stop(self):
  before={'installed':True,'enabled':True,'linger':True};after=dict(before,enabled=False)
  with patch.object(a,'status',side_effect=[before,after]),patch.object(a,'run',return_value=result()) as run:
   a.set_enabled(False);self.assertEqual(run.call_args.args[0][-2:],['disable','glaze-dashboard.service'])
 def test_setup_required_no_mutation(self):
  for state in [dict(installed=False,linger=True),dict(installed=True,linger=False)]:
   with patch.object(a,'status',return_value=state),patch.object(a,'run') as run:
    with self.assertRaises(a.SetupRequired):a.set_enabled(True)
    run.assert_not_called()
 def test_verify_failure(self):
  before=dict(installed=True,enabled=False,linger=True)
  with patch.object(a,'status',return_value=before),patch.object(a,'run',return_value=result()):
   with self.assertRaises(a.ControlUnavailable):a.set_enabled(True)
 def test_no_arbitrary_value(self):
  with self.assertRaises(ValueError):a.set_enabled('ssh.service')
 def test_post_guards(self):
  with patch.object(d,'TOKEN','x'*43,create=True),patch.object(a,'set_enabled',return_value={'enabled':True}) as change:
   server=d.ThreadingHTTPServer(('127.0.0.1',0),d.Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
   def request(body=b'{"enabled":true}',overrides=None,path=None):
    headers={'Host':'127.0.0.1:18765','Origin':'http://127.0.0.1:18765','Content-Type':'application/json','X-Glaze-CSRF':d.CSRF}
    headers.update(overrides or {})
    req=urllib.request.Request(f'http://127.0.0.1:{server.server_port}'+(path or '/'+'x'*43+'?autostart=1'),data=body,headers=headers,method='POST')
    try:
     with urllib.request.urlopen(req) as r:return r.status
    except urllib.error.HTTPError as e:return e.code
   try:
    for headers in [{'Origin':'https://evil.test'},{'X-Glaze-CSRF':''},{'Host':'evil.test'}]:self.assertEqual(request(overrides=headers),403)
    self.assertEqual(request(path='/wrong?autostart=1'),403)
    self.assertEqual(request(body=b'{"enabled":true,"unit":"ssh.service"}'),400)
    self.assertEqual(request(body=b'{"enabled":"yes"}'),400)
    self.assertEqual(request(body=b' '*257),400)
    change.assert_not_called()
    self.assertEqual(request(),200);change.assert_called_once_with(True)
   finally:server.shutdown();server.server_close();thread.join()
if __name__=='__main__':unittest.main()
