#!/usr/bin/env bash
# Run as your normal user from a reviewed checkout; never with sudo.
set -euo pipefail
if [ "$(id -u)" = 0 ]; then echo 'Run as your normal user, not root.'; exit 1; fi
mode="${1:-viewer}"
case "$mode" in viewer|monitor) ;; *) echo 'Usage: bash scripts/install.sh [viewer|monitor]'; exit 1;; esac
repo="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo"
python3 -c 'import sys; assert sys.version_info >= (3,10), "Python 3.10+ required"'
umask 077
mkdir -p "$HOME/.config/glaze" "$HOME/.config/systemd/user"
if [ ! -f "$HOME/.config/glaze/config.json" ]; then
  cp config.example.json "$HOME/.config/glaze/config.json"
  echo 'Created example config. Edit ~/.config/glaze/config.json for your targets, then rerun.'
  exit 0
fi
python3 - <<'PY'
from glaze.config import load
load()
PY
python3 - <<'PY'
from pathlib import Path
import json, os
repo=Path.cwd(); units=Path.home()/'.config/systemd/user'
config=str(Path.home()/'.config/glaze/config.json')
data=str(Path(os.environ.get('GLAZE_DATA_DIR',str(Path.home()/'.local/state/glaze'))).expanduser().resolve())
Path(data).mkdir(parents=True,exist_ok=True)
Path(data).chmod(0o700)
def quote(s): return json.dumps(str(s))
for name,module,args in [('dashboard','glaze.dashboard',''),('http','glaze.monitor','http'),('browser','glaze.monitor','browser')]:
    hardening='NoNewPrivileges=yes\nProtectSystem=strict\n' if name!='browser' else ''
    text='[Unit]\nDescription=Glaze '+name+'\nAfter=network-online.target\n\n[Service]\n'
    text+='Type='+('simple' if name=='dashboard' else 'oneshot')+'\n'
    text+='WorkingDirectory='+quote(repo)+'\n'
    text+='Environment='+quote('GLAZE_CONFIG='+config)+'\nEnvironment='+quote('GLAZE_DATA_DIR='+data)+'\n'
    text+='ExecStart=/usr/bin/python3 -m '+module+' '+args+'\nUMask=0077\n'
    text+=hardening+'ReadWritePaths='+quote(data)+'\nPrivateTmp=yes\n'
    if name=='dashboard': text+='ReadWritePaths='+quote(units)+'\n'
    if name=='dashboard':text+='Restart=on-failure\nRestartSec=5\nStandardOutput=null\n\n[Install]\nWantedBy=default.target\n'
    else:text+='TimeoutStartSec=15min\n'
    (units/('glaze-'+name+'.service')).write_text(text)
for name,interval in [('http','5min'),('browser','15min')]:
    (units/('glaze-'+name+'.timer')).write_text('[Unit]\nDescription=Glaze '+name+' schedule\n[Timer]\nOnBootSec=2min\nOnUnitActiveSec='+interval+'\nUnit=glaze-'+name+'.service\n[Install]\nWantedBy=timers.target\n')
PY
systemctl --user daemon-reload
systemctl --user enable --now glaze-dashboard.service
if [ "$mode" = monitor ]; then
  systemctl --user enable --now glaze-http.timer glaze-browser.timer
fi
systemctl --user --no-pager status glaze-dashboard.service
printf '\nView your private link: python3 -m glaze.link\n'
printf 'For operation after logout/reboot, an administrator must enable user lingering (see README).\n'
