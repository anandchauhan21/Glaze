# Private deployment and recovery

## A direct SSH route

Run Glaze on the monitor machine. On your viewing laptop:

```bash
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
  -L 127.0.0.1:18765:127.0.0.1:18765 USER@MONITOR_HOST
```

Open the exact private URL printed by `python3 -m glaze.link` on the monitor
machine. Keep the SSH connection open. A phone needs its own local-forward rule:
local bind 127.0.0.1, local port 18765, SSH host the monitor host, destination
127.0.0.1, destination port 18765. Use Local, not Remote or Dynamic.

## A VPS relay with Cloudflare SSH

If the existing route is laptop → VPS → Jetson through cloudflared, both hops
need a loopback-only forward. Keep existing host keys and authentication checks.
Do not disable host verification. Use your own known hostnames/accounts below.

On the VPS:

```bash
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
  -L 127.0.0.1:18765:127.0.0.1:18765 \
  -o 'ProxyCommand=cloudflared access ssh --hostname %h' \
  JETSON_USER@JETSON_SSH_HOSTNAME
```

In a separate local laptop terminal:

```bash
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
  -L 127.0.0.1:18765:127.0.0.1:18765 VPS_USER@VPS_HOST
```

Termius's intermediate host in this two-hop case is the VPS. The VPS-to-Jetson
forward must also be running. These forwards do not install a dashboard, alter
SSH configuration, open public firewall rules, or restart product containers.
A relay's privileged users remain within your trust boundary.

## Diagnose without changing production

On the monitor machine:

```bash
ss -ltn 'sport = :18765'
systemctl --user status glaze-dashboard.service
journalctl --user -u glaze-dashboard.service -n 30 --no-pager
```

From the viewing laptop (Windows):

```powershell
curl.exe --noproxy "*" --max-time 10 -s -o NUL -w "HTTP: %{http_code}\n" http://127.0.0.1:18765/
```

Expected **403** on the tokenless URL means a guarded endpoint is reachable;
it is not a complete dashboard verification. The valid private URL should show
Glaze and current refresh timestamps. A connection refusal points to a missing
listener/tunnel; a 403 with the full URL can indicate an old token. Browser
refresh errors must not be mistaken for product outages.

If a dashboard process already owns 18765, identify it before stopping it. Do
not use broad `pkill python`, change SSH ports, disable firewalls, or reboot a
production VPS to fix a local-forward issue.

## Update and rollback

Record the current commit and back up your local config before an update:

```bash
git rev-parse HEAD
git status --short
git pull --ff-only
python3 -m unittest discover -s tests -v
systemctl --user restart glaze-dashboard.service
```

Only update a clean checkout. To roll back, check out the recorded known-good
commit in a clean working tree and restart only Glaze. Runtime logs and tokens
are outside the repository and are not overwritten by git updates. Review
installer changes before re-running `scripts/install.sh`.

## Resource and operational limits

The viewer does no inference and launches no checks. Chromium is the main
variable resource cost. The collectors use per-kind locks, bounded request
timeouts and a temporary browser profile. Different collector kinds can run
concurrently. Keep the browser disabled on machines that cannot safely handle
it. External request load depends on configured targets and page resources.

There is no automated retention in 0.1. Review disk use and archive logs manually.
The viewer reads at most 2 MB per daily file over eight calendar dates. Existing
logging systems may have different clocks/timezones; match the config timezone
to log file naming before interpreting midnight boundaries.

Systemd user services may require lingering and supported user namespaces for
sandbox directives. The installer does not change global security settings.
Chromium's own sandbox is never disabled by Glaze.
