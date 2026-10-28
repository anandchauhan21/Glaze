# Contributing to Glaze

Use a branch and a pull request. Describe the user-visible problem, the smallest
change that fixes it, the checks performed, and any limits. Never run tests
against a production system without permission. Use synthetic fixtures only.

Run:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q glaze
bash -n scripts/install.sh
```

UI work must preserve responsive layouts, textual chart alternatives and clear
no-data/stale states. Security work must preserve local-only binding, token
checks, verified TLS, bounded requests, and non-mutating dashboard routes.
No automatic fixes, production writes or secret-bearing screenshots in PRs.

Glaze uses Python 3.10+ standard library, curl and optional Chromium. Keep new
dependencies justified and pinned. Contributions are licensed under MIT.
The Sugarcoat and Glaze names do not grant permission to imply endorsement.
