<div align="center">

# Glaze by Sugarcoat

**A clear view of your services.**

Lightweight, self-hosted monitoring with an understandable dashboard.
Built for small teams, independent developers and modest Linux machines.

[Quick start](#quick-start) · [Existing Jetson setup](#migrate-the-existing-jetson-monitor) · [Security](SECURITY.md) · [Contributing](CONTRIBUTING.md) · [Sugarcoat](https://sugarcoat.tech/)

</div>

## Why Glaze exists

When you are building a website, portal and mobile app at the same time, it is
hard to notice when a deployment breaks a public page. Raw logs are useful for
debugging but difficult to inspect from a phone. Glaze turns a few repeatable,
low-frequency checks into a readable report: what passed, what failed, how long
requests took, and whether the monitor is still reporting.

Glaze grew from a Sugarcoat monitoring workflow running on a Jetson. It does not
need an AI model, GPU, cloud database, paid dashboard service or build toolchain.
It runs independently of the product it monitors. Viewing the dashboard reads
local reports; it does not send extra checks to your applications.

**Status: 0.1.0, early release.** This is a small private monitoring tool, not a
security scanner, a full observability platform, or a guarantee of availability.
It is a custom dashboard inspired by BI reporting, not Microsoft Power BI.

## What you get

| Feature | What it tells you |
| --- | --- |
| HTTPS checks | Whether an expected status and exact redirect were returned |
| Optional browser check | Whether configured input fields appeared in Chromium's DOM |
| KPI cards | Recorded checks, sample pass rate, failures/blocked, mean and P95 request time |
| Response-time chart | Total HTTP request duration by page; gaps over 10 minutes are not connected |
| Outcome chart | Counts of PASS, FAIL and BLOCKED samples |
| Latest-status table | Per-check evidence, timestamps, HTTP status and stale/missing states |
| Time filters | Last hour, 24 hours or 7 days |
| Exception list | Most recent 20 failures or blocked checks in the selected period |
| Private viewing | Loopback-only server, random token and SSH forwarding |
| Deployment | Standard-library Python, curl and optional user-level systemd timers |

No form submissions, automatic remediation, deployments, Git merges or production
database connections are part of Glaze. Browser pages still execute JavaScript;
only monitor sites you trust and are authorized to access.

## How it works

The HTTP collector uses curl; the optional browser collector starts a fresh
Chromium profile. Each writes timestamped reports outside the Git checkout.
The dashboard reads those reports and builds charts in your browser using local
Canvas code. There are no CDNs, tracking scripts, remote fonts or telemetry.

| Component | Default location / behavior |
| --- | --- |
| Configuration | `~/.config/glaze/config.json` |
| Runtime data | `~/.local/state/glaze/` |
| Reports | `<data directory>/reports/YYYY-MM-DD.log` and `browser-YYYY-MM-DD.log` |
| Access token | `<data directory>/dashboard/access-token` |
| Dashboard listener | `127.0.0.1:18765` only |
| HTTP schedule | Every 5 minutes when timers are enabled |
| Browser schedule | Every 15 minutes; only executes if enabled in config |

`GLAZE_CONFIG` and `GLAZE_DATA_DIR` can override paths for manual runs. The installer
uses the standard config location and captures `GLAZE_DATA_DIR` into its units.

## Requirements

- Linux, Python 3.10+ and system timezone data (`tzdata`).
- `curl` for HTTP checks. No pip dependencies.
- Optional Chromium and `/usr/bin/timeout` for browser checks.
- Optional systemd user services for background operation.
- SSH client on the device used to view the dashboard remotely.

The code is architecture-independent Python. ARM64 Jetson and x86-64 Linux are
intended targets; the new packaged deployment has not yet been device-validated
on every platform. Prior iterations were exercised on an ARM64 Jetson. Browser
support depends on your Chromium packaging and sandbox support.

## Quick start

Run as a normal user, not root:

```bash
git clone https://github.com/anandchauhan21/Glaze.git
cd Glaze
umask 077
mkdir -p ~/.config/glaze
# Copy only when a config does not already exist:
[ -f ~/.config/glaze/config.json ] || cp config.example.json ~/.config/glaze/config.json
nano ~/.config/glaze/config.json
```

Replace the example target with your own authorized HTTPS URL. Then run:

```bash
python3 -m glaze.monitor http
python3 -m glaze.dashboard
```

The server prints a private URL. Keep its token secret. On the same machine,
open the printed URL directly. On a laptop, establish a tunnel first:

```bash
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
  -L 127.0.0.1:18765:127.0.0.1:18765 USER@MONITOR_HOST
```

Keep that session open, then open the private URL in the laptop browser. Local
HTTP is carried inside encrypted SSH for remote transport. No inbound dashboard
firewall rule is required. A phone needs its own tunnel; the laptop's tunnel does
not serve the phone.

A missing/wrong token returns 403. `ERR_CONNECTION_REFUSED` usually means the
local tunnel or dashboard is not listening; it does not establish that the
monitored product is down. See [deployment notes](docs/DEPLOYMENT.md).

## Configure checks

```json
{
  "timezone": "Asia/Kolkata",
  "targets": [
    {"label": "Homepage", "url": "https://your-domain.example/", "expected_status": 200},
    {"label": "Login", "url": "https://your-domain.example/login/", "expected_status": 200},
    {"label": "Signed-out dashboard", "url": "https://your-domain.example/dashboard", "expected_status": 302,
     "expected_redirect": "https://your-domain.example/login/?next=/dashboard"}
  ],
  "browser": {
    "enabled": true,
    "label": "Login form rendering",
    "url": "https://your-domain.example/login/",
    "executable": "/snap/bin/chromium",
    "fields": [{"name": "username", "type": "text"}, {"name": "password", "type": "password"}]
  }
}
```

Use an absolute HTTPS redirect as curl reports it. With no `expected_redirect`,
Glaze expects no redirect. Targets are not followed by curl. There is one optional
browser target, which must also be in the HTTP target list. The browser check
matches input names and types; it does not prove authentication or visual layout.
To disable it, set `browser.enabled` to `false`.

Keep real config outside Git. URLs may contain internal names or query secrets;
never put credentials or sensitive query parameters into targets.

## Run continuously

From the reviewed checkout:

```bash
bash scripts/install.sh viewer
```

This installs and starts only the viewer. To also schedule new collectors:

```bash
bash scripts/install.sh monitor
```

**Do not enable duplicate collectors if your previous cron jobs are still running.**
The installer does not alter or remove existing cron entries or other products.
It writes only `glaze-*` user service/timer files, then enables requested units.
If port 18765 is already occupied by the foreground viewer, stop that viewer with
Ctrl+C first. Do not terminate an unidentified process.

For user services to continue after logout and start without a login, an
administrator may enable lingering:

```bash
sudo loginctl enable-linger "$USER"
```

Check and operate services:

```bash
systemctl --user status glaze-dashboard.service
systemctl --user list-timers 'glaze-*'
python3 -m glaze.link
journalctl --user -u glaze-dashboard.service -n 30 --no-pager
```

Stop only Glaze:

```bash
systemctl --user disable --now glaze-dashboard.service glaze-http.timer glaze-browser.timer
```

User-level sandbox features depend on your systemd/kernel configuration. If a
unit fails, inspect its journal rather than disabling platform security globally.

## Migrate the existing Jetson monitor

The legacy `~/sugarcoat-monitor/reports/` format is supported. Keep the old HTTP
and browser cron jobs and migrate only the viewer first:

1. Clone this repository and configure the same Sugarcoat URLs/labels and enabled
   browser check in `~/.config/glaze/config.json`.
2. Stop the old foreground viewer with Ctrl+C. This does not stop cron or SSH.
3. Back up its script and token locally; never commit them.
4. Start Glaze against existing reports:

```bash
GLAZE_DATA_DIR="$HOME/sugarcoat-monitor" python3 -m glaze.dashboard
```

5. For a background viewer instead:

```bash
GLAZE_DATA_DIR="$HOME/sugarcoat-monitor" bash scripts/install.sh viewer
GLAZE_DATA_DIR="$HOME/sugarcoat-monitor" python3 -m glaze.link
```

An existing valid token is reused. If a URL appeared in a shared screenshot,
rotate it and restart the viewer:

```bash
GLAZE_DATA_DIR="$HOME/sugarcoat-monitor" python3 -m glaze.link --rotate
systemctl --user restart glaze-dashboard.service
```

To switch collectors later, back up `crontab -l`, remove only the two legacy
Sugarcoat monitoring entries, then install Glaze's monitor timers against the same
data directory. Review the resulting schedule so each check runs only once.
Glaze never migrates or changes production applications.

## Interpret the numbers correctly

- **PASS:** the configured check matched at that recorded time.
- **FAIL:** the request/rendering outcome did not match expectations.
- **BLOCKED:** a required execution could not complete (for example Chromium
  unavailable). Existing legacy curl failures may be recorded as FAIL.
- **STALE:** last HTTP evidence is older than 10 minutes, or browser evidence
  older than 20 minutes. Thresholds are fixed in 0.1.
- **NO DATA:** no matching sample was found in the selected report period.

Sample pass rate = PASS / (PASS + FAIL + BLOCKED). Missing scheduled runs are not
part of that denominator. This is **not a measured uptime SLA**. Mean and P95 use
all finite non-negative HTTP timings, including recorded failed attempts. P95
uses the nearest-rank method. Browser timing is not measured. Response time is
curl total duration, not full browser page-load speed.

Each report file read is capped at 2 MB. Under unusually high-frequency/custom
logging, charts may reflect only a tail of that file. Malformed lines are counted
and excluded. Future-dated records are excluded; keep the host clock accurate.
URLs are the identity for HTTP history: changing a URL starts a new series. The
single browser stream has no historical target ID; use a new data directory or
archive browser logs when changing that target. Data retention is manual in 0.1.

## Security and privacy

See [SECURITY.md](SECURITY.md) for the threat model and reporting process.

- The viewer is read-only by behavior, not a separate OS account boundary.
- No application credentials, cookies or production database access are needed.
- TLS verification and Chromium sandboxing remain enabled.
- Page content, cookies and browser profiles are temporary; reports contain
  check results rather than page bodies. Crashes can leave temporary files.
- Viewer token paths must not appear in public screenshots or support issues.
- Keep the system, curl and Chromium updated through supported packages.
- No claim of security certification, penetration testing or tenant-isolation
  verification follows from a green dashboard.

## Why open source?

Small teams should be able to inspect how their monitoring works, run it on
hardware they own, and improve it without paying per dashboard or AI token.
Publishing Glaze makes its checks and limitations visible, enables contributions,
and makes deployment repeatable rather than depending on pasted terminal commands.

The code is MIT licensed: modification, redistribution and commercial use are
permitted under the license terms. Glaze and Sugarcoat branding must not be used
to imply endorsement of a third-party fork. There is no hosted service or support
SLA included.

## Development and validation

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q glaze
bash -n scripts/install.sh
```

Tests use synthetic data and mocked requests, never production endpoints.
GitHub Actions runs the Python checks when available; a configured workflow is
not proof that it has run. Browser appearance and systemd/Jetson operation require
an environment-level smoke test before relying on this release.

## Roadmap — not implemented yet

- Notifications with failure deduplication and recovery messages.
- Automated retention and richer historical storage.
- Screenshot evidence and visual-regression tests.
- Authenticated journeys with dedicated restricted test accounts.
- GitHub commit/PR test integration and Android app checks.
- Exportable reports and configuration UI.

## Project layout

| Path | Purpose |
| --- | --- |
| `glaze/config.py` | Local configuration validation |
| `glaze/monitor.py` | HTTP and optional browser collectors |
| `glaze/dashboard.py` | Private report API, dashboard and charts |
| `glaze/link.py` | Local link display and token rotation |
| `scripts/install.sh` | User-service deployment |
| `tests/` | Offline regression and access-control tests |
| `docs/` | Branding and deployment guidance |

Built by **Anand Chauhan / Sugarcoat**. [sugarcoat.tech](https://sugarcoat.tech/)
