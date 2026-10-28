"""Narrow control of Glaze's own user service; never accepts unit names or shell code."""
import os
import subprocess
UNIT = 'glaze-dashboard.service'
class SetupRequired(Exception): pass
class ControlUnavailable(Exception): pass

def run(args):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=8)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ControlUnavailable('Cannot reach the local service manager.') from exc

def status():
    r=run(['/usr/bin/systemctl','--user','--no-ask-password','show',UNIT,'--property=LoadState,ActiveState,UnitFileState'])
    if r.returncode: raise ControlUnavailable('Cannot read the Glaze user service.')
    props=dict(line.split('=',1) for line in r.stdout.splitlines() if '=' in line)
    linger=run(['/usr/bin/loginctl','--no-ask-password','show-user',str(os.getuid()),'--property=Linger','--value'])
    installed=props.get('LoadState')=='loaded'
    enabled=props.get('UnitFileState')=='enabled'
    lingering=linger.returncode==0 and linger.stdout.strip()=='yes'
    return dict(installed=installed,enabled=enabled,linger=lingering,
                boot_ready=installed and enabled and lingering,
                active=props.get('ActiveState','unknown'))

def set_enabled(enabled):
    if type(enabled) is not bool: raise ValueError('enabled must be a boolean')
    before=status()
    if not before['installed']: raise SetupRequired('Install the Glaze viewer service first.')
    if enabled and not before['linger']: raise SetupRequired('One-time boot setup required: enable lingering from the Jetson terminal.')
    action='enable' if enabled else 'disable'
    result=run(['/usr/bin/systemctl','--user','--no-ask-password',action,UNIT])
    if result.returncode: raise ControlUnavailable('Could not change Glaze auto-start. Check its service permissions.')
    after=status()
    if after['enabled']!=enabled: raise ControlUnavailable('Auto-start change could not be verified.')
    return after
