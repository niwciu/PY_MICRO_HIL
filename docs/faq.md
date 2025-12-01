# FAQ

**Do I need a Raspberry Pi to run tests?**  
No. On non-RPi hosts the framework switches to dummy interfaces and logs a
warning. You can author and debug suites on a PC or in CI/CD; swap in hardware
later with the same tests.

**How do I run only specific tests?**  
Create a smaller folder with just the desired files (e.g., `hil_tests_subset/`)
and point the runner to it with `--test-dir hil_tests_subset`. Filenames still
need to start with `test_`.

**Where is the HTML report stored?**  
By default at `./html_report/report.html`. Change it with `--html`, including
paths served by lighttpd/nginx (e.g., `public_html`). A `styles.css` is written
next to the HTML file.

**Can I maintain multiple hardware setups?**  
Yes. Keep multiple YAML files (e.g., `configs/lab.yaml`, `configs/prod.yaml`) and
invoke the runner with the matching `--config`. Pair each with its own test
folder if needed using `--test-dir`.

**What if YAML parsing fails?**  
The runner aborts before executing tests and prints the parsing error. Fix the
syntax or path; this prevents partial runs on misconfigured hardware.

**How do I log extra details in reports?**  
Use `TEST_INFO_MESSAGE("step description")` inside your tests. Messages appear
in the console, optional text log, and the HTML report.

**Can I publish reports to `public_html`?**
Yes. Pass `--html ./public_html` or `--html ./public_html/hil_report.html`. The
runner creates subfolders as needed; copy both `report.html` and `styles.css`
if your web server reads from a different location.

**How do I see low-level protocol traces?**
Run with `--debug` to emit `[DEBUG]` messages to the console, text logs, and HTML
reports. Without the flag those entries are suppressed so routine runs stay
compact.

**How do I confirm which version of the runner executed my job?**
Use `hiltests --version`; the value comes from the installed package when
available or from the checked-out `pyproject.toml` when running from source.
