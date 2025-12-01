# Reports & Artifacts

Py-Micro-HIL emits console output by default and can optionally persist text logs
and HTML reports. Both are controlled via CLI flags so you can route artifacts to
local folders, CI workspaces, or web-server roots like `public_html`.

## Text log (`--log`)
- Example: `hiltests --log ./reports/run.log`.
- Parent directories are created automatically.
- Each run recreates the file to avoid mixing sessions.
- Content mirrors console output (without ANSI colors) for easy ingestion by CI
  log collectors.
- Add `--debug` when you want `[DEBUG]` traces from peripherals to appear in the
  log; otherwise those lines stay hidden to keep the file concise.

## HTML report (`--html`)
- Add `--html` to generate a styled summary with per-group entries and details.
- Path handling rules:
  - **No value**: saves to `./html_report/report.html`.
  - **Folder value**: saves to `<folder>/html_report/report.html`.
  - **.html value**: saves exactly to that file (e.g.,
    `--html ./public_html/hil_report.html`).
- A companion `styles.css` is copied next to the HTML output for self-contained
  publishing.
- Templates and CSS are validated up front. If Jinja2 is unavailable, a
  simplified but still complete HTML report is rendered so runs never fail only
  because templating is missing.

### Examples
- Publish to a web root for lighttpd/nginx:
  ```bash
  hiltests --html /var/www/public_html/hil_report.html
  ```
- Generate both text and HTML in a CI workspace:
  ```bash
  hiltests --log ./artifacts/hil.log --html ./artifacts
  ```

## Integration tips
- Combine `--log` and `--html` so pipelines retain machine-readable logs and a
  human-friendly report simultaneously.
- If permissions prevent writing directly into a web root, generate artifacts in
  a temporary folder and copy both `report.html` and `styles.css` during deploy
  steps.
- HTML output is deterministic and safe to store under versioned `public_html`
  directories for static hosting.
- When running in constrained environments (e.g., minimal containers without
  Jinja2), expect a plain HTML layout; content and pass/fail totals remain the
  same so CI artifacts stay useful.

## What gets recorded
- **Pass/fail status** for every test with a timestamped summary.
- **[INFO] entries** emitted by `TEST_INFO_MESSAGE` inside your tests.
- **Initialization messages** about YAML path selection and discovered
  peripherals.
- **Errors** surfaced during setup/teardown and report generation.
- **[DEBUG] traces** (protocol-level I/O, bus scans, etc.) *only* when the
  runner is invoked with `--debug`, so you can choose when to capture
  high-volume detail.
