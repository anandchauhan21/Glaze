# Security policy

Glaze 0.2 is an early release, not an independently audited security product.

## Boundary

The dashboard binds only to 127.0.0.1:18765. Use an SSH local forward. It checks
Host and a random bearer token, suppresses access logs, escapes displayed data
through textContent, and uses no remote scripts/fonts/analytics. It has no commands to modify applications, trigger monitoring, edit target
configuration, or read arbitrary paths. One authenticated POST endpoint may
enable/disable only the fixed `glaze-dashboard.service` user unit. It requires
the private URL token, exact same-origin Origin, a per-process CSRF header, and
a size-limited JSON boolean. It accepts no unit names or shell commands, uses
no sudo, and cannot start/stop other services. Turning auto-start off does not
stop the current viewer. Initial service installation and user lingering are
terminal-only administrative setup. Responses use no-store and no-referrer headers.

The URL is a secret: it remains in browser history and may appear in screenshots.
Rotate with `python3 -m glaze.link --rotate`, then restart Glaze. HTTP is only
local; SSH encrypts the remote transport. Do not bind to 0.0.0.0 or publish the
viewer behind an unauthenticated tunnel. Host and token checks are defense in
depth, not a replacement for network isolation. Other privileged users on a
machine or SSH relay may be able to access local services.

Run as an unprivileged account. The viewer does not write reports, but a process
running as the same account as a collector is not an OS-enforced read-only
boundary. For hostile multi-user environments, use separate accounts and
read-only report permissions. The standard-library server is intended for a
small private deployment, not public-facing or high-concurrency service.

HTTP collectors use certificate-verifying curl, explicit HTTPS, no redirects,
no curlrc, no proxy environment routing and no request credentials. Browser
checks retain Chromium sandboxing and certificates but execute the target's
JavaScript and may request external resources or encounter redirects. They are
only for trusted, authorized sites. Configuration is local administrative input,
not a public API. The configured Chromium binary must be trusted and patched.
GET requests may still create sessions, access logs or server-side effects; do
not configure state-changing URLs. Browser checks do not submit forms.

Temporary browser data is deleted after normal completion; hard crashes or
power loss can leave private temporary directories. Reports are private by
filesystem mode but not encrypted. Log retention is manual in 0.2; monitor disk
space. HTTP and browser jobs have separate overlap locks and may overlap each
other. Resource usage depends on target pages.

## Reporting

Use GitHub's private vulnerability reporting if enabled for this repository.
If unavailable, contact the maintainer through the official Sugarcoat site to
arrange a private channel. Do not post passwords, tokens, real reports, private
URLs, exploit details or customer data in public issues.

No confirmed security review or certification is implied by a PASS result.
