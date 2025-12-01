# Getting Started

This chapter walks through installation, the expected project layout, and a
first end-to-end run that produces both console output and artifacts.

## Prerequisites
- Python 3.9+ on Linux (tested on Raspberry Pi OS and standard distributions).
- Access to the target hardware **or** a PC/CI agent for simulation mode.
- Optional: `pipx` or virtual environments to isolate dependencies.

## Installation options

### From PyPI (recommended)
```bash
pip install py-micro-hil
```

### From source (for contributors)
```bash
git clone https://github.com/niwciu/PY_MICRO_HIL.git
cd PY_MICRO_HIL
pip install -e .[dev]
```

> 💡 In CI/CD or containerized hosts you can add `--break-system-packages` to
> bypass distro packaging checks when necessary:
> ```bash
> pip install py-micro-hil --break-system-packages
> ```

## Minimal project layout

```text
my-project/
├─ peripherals_config.yaml   # hardware definition (YAML)
├─ hil_tests/                # default test root (override with --test-dir)
│  └─ test_gpio_led.py
└─ reports/                  # optional folder for logs/HTML outputs
```

1. Create `peripherals_config.yaml` with your buses and devices (see
   **Hardware Configuration** for a detailed schema).
2. Add a `hil_tests/` folder with Python files prefixed by `test_`.
3. Run the suite:
   ```bash
   hiltests
   ```

## Quickstart example

1. Define a minimal configuration:
   ```yaml
   peripherals:
     gpio:
       - pin: 17
         mode: out
       - pin: 18
         mode: in
   ```
2. Generate a starter test group from the template, then edit it to match the
   example below:
   ```bash
   mkdir -p hil_tests
   hiltests --create-test-group gpio_led --test-dir ./hil_tests
   ```
   Update `hil_tests/test_gpio_led.py` with:
   ```python
   from py_micro_hil.assertions import *
   from py_micro_hil.framework_API import *


   def test_led_loopback():
       gpio = get_RPiGPIO_peripheral()
       gpio.write(17, 1)
       TEST_ASSERT_TRUE(gpio.read(18))
   ```
3. Run with defaults (YAML + tests in the current directory):
   ```bash
   hiltests
   ```
4. Generate artifacts in custom locations:
   ```bash
   hiltests --log ./reports/run.log --html ./public_html/hil_report.html
   ```
5. Check which runner version is installed (useful for CI traceability and when comparing logs with teammates):
   ```bash
   hiltests --version
   ```
6. Turn on debug-level visibility when you need to trace low-level peripheral calls:
   ```bash
   hiltests --debug --log ./reports/run-debug.log
   ```
   Messages tagged with `[DEBUG]` stay hidden unless the flag is set, keeping everyday runs concise.

## Default locations and how to override them
- Hardware config: `./peripherals_config.yaml` → `--config /path/to/custom.yaml`.
- Tests: `./hil_tests/` → `--test-dir ./integration/hil/`.
- HTML report: `./html_report/report.html` → `--html ./public_html` or
  `--html ./public_html/hil_report.html`.
- Text log: disabled by default → `--log ./reports/run.log`.
- Debug output: suppressed by default → `--debug` to include `[DEBUG]` entries in console output, text logs, and HTML reports.

Relative paths are resolved to absolute ones before execution so you can invoke
`hiltests` from any working directory.
