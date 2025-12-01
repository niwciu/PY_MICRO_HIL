# Running Tests & CLI

The `hiltests` runner executes discovered tests, initializes peripherals, and
handles logging/reporting. It normalizes all provided paths so you can launch it
from any working directory or CI job.

## Command overview
```bash
hiltests [--config <YAML>] [--test-dir <DIR>] [--log <FILE>] [--html [PATH]] [--list-tests] [--strict-imports] [--debug] [--version] [--create-test-group <GROUP> [DIR]]
```

### Flag reference
| Flag | Description |
|------|-------------|
| `--config, -c <YAML>` | Path to the hardware configuration file. Defaults to `./peripherals_config.yaml`. Accepts absolute or relative paths. |
| `--test-dir <DIR>` | Directory containing `test_*.py` files (default `./hil_tests`). Can point to alternate suites or a temporary filtered folder. |
| `--log <FILE>` | Write plain-text logs to the given file. Parent folders are created automatically. |
| `--debug, -d` | Emit messages tagged with `[DEBUG]` to the console, text log, and HTML report. Without this flag, debug lines are intentionally suppressed. |
| `--html [PATH]` | Generate an HTML report. Without a value → `./html_report/report.html`. With a folder → `<folder>/html_report/report.html`. With a `.html` file → saved exactly there. |
| `--list-tests` | Discover and print test groups, then exit without execution. |
| `--strict-imports` | Fail fast when any discovered test module cannot be imported (useful for CI to catch missing dependencies or bad imports). |
| `--version, -v` | Print the installed/checked-out runner version and exit. Useful in CI logs to verify which release executed your tests. |
| `--create-test-group <GROUP> [DIR]` | Scaffold a new `test_<GROUP>.py` from the editable template in `example/`, writing to `DIR` or the current `--test-dir`, then exit without running tests. |

## Usage patterns
- **Default run (everything local):**
  ```bash
  hiltests
  ```
  Looks for `./peripherals_config.yaml` and `./hil_tests/`.

- **Custom folder and config:**
  ```bash
  hiltests --config ./configs/lab.yaml --test-dir ./tests/integration/hil --log ./logs/lab.log
  ```

- **Publish HTML to a web root (e.g., lighttpd/nginx `public_html`):**
  ```bash
  hiltests --html ./public_html/hil_report.html
  # or place it inside a folder
  hiltests --html ./public_html
  # saves ./public_html/html_report/report.html + styles.css
  ```

- **List without executing:**
  ```bash
  hiltests --list-tests
  ```

- **Enable verbose device diagnostics:**
  ```bash
  hiltests --debug --log ./logs/debug.log
  ```
  Debug lines (prefixed with `[DEBUG]`) remain silent unless `--debug` is set, so you can keep day-to-day runs concise and only surface protocol-level traces when troubleshooting.

- **Inspect initialized peripherals:**
  ```bash
  hiltests --debug
  ```
  When debug logging is enabled, the runner prints each discovered category (e.g., GPIO, UART) and the attributes of every instantiated device. Ensure your YAML resolves to lists of peripheral objects—empty categories are reported as `(none)`.

- **Enforce clean imports in CI:**
  ```bash
  hiltests --strict-imports
  ```
  This surfaces missing optional dependencies or bad imports as a hard failure instead of a warning.
- **Create a new test group file without executing anything:**
  ```bash
  hiltests --create-test-group my_group ./hil_tests
  # or rely on the active --test-dir (defaults to ./hil_tests)
  hiltests --create-test-group my_group
  ```

## Execution lifecycle
1. **Argument parsing** — resolves paths, prepares HTML/log locations.
2. **Peripheral initialization** — loads YAML, creates real or dummy devices, and
   emits warnings if running off-Raspberry Pi.
3. **Test discovery** — walks `--test-dir`, imports modules, and wraps
   `test_*` functions into groups.
4. **Run & report** — executes group setup, tests, teardown; reports to console
   and optional log/HTML outputs.
5. **Cleanup & summary** — releases peripherals, prints pass/fail counts, and
   generates the HTML report when requested.

## CI/CD recommendations
- **Isolate suites**: keep a dedicated `hil_tests_ci/` with fast checks and run it
  with `--test-dir hil_tests_ci`.
- **Use absolute paths**: precompute config/log/report paths to avoid surprises
  when CI changes working directories.
- **Persist artifacts**: combine `--log` and `--html` so pipelines can publish
  both machine-readable logs and human-friendly reports.
- **Simulation-first**: hardware not available? YAML still loads and dummy
  peripherals are created; assertions continue to execute for basic coverage.

## Troubleshooting
- YAML parsing errors or missing files stop the run before tests execute—fix the
  config path or syntax first.
- Import warnings usually indicate optional dependencies are missing; rerun with
  `--strict-imports` in CI to fail fast and fix the dependency or stub.
- If no tests are discovered, confirm filenames start with `test_` and the folder
  passed to `--test-dir` exists.
- Serial/I/O errors (UART, SPI, Modbus) usually indicate mismatched port names or
  permissions; verify device nodes and user access.
