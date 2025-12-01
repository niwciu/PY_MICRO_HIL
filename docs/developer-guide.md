# Developer Guide

This guide explains how the framework is organized, how to extend it with new
peripherals or CLI options, and what to keep in mind when contributing.

## Code structure (high level)
- `src/py_micro_hil/cli.py` — argument parsing and the `hiltests` entrypoint.
- `src/py_micro_hil/peripheral_config_loader.py` — YAML parsing and device
  instantiation (real or dummy depending on platform).
- `src/py_micro_hil/framework_API.py` — getters that expose configured
  peripherals to tests.
- `src/py_micro_hil/tests_group_factory.py` — wraps modules into test groups,
  injects context, and handles setup/teardown.
- `src/py_micro_hil/tests_framework.py` — executes groups, aggregates results,
  and triggers report generation.
- `src/py_micro_hil/logger.py` and `report_generator.py` — console/file logging
  plus HTML report output.

## Architecture and lifecycle
- The execution lifecycle and component responsibilities are detailed in the
  [System Architecture & Extensibility Guide](architecture.md). Start there for
  a holistic view of how the CLI, loader, API, orchestrator, and reporter work
  together.
- Keep layers loosely coupled: tests interact only with the public API getters,
  not with concrete driver classes; the loader owns schema validation and
  instantiation logic; the CLI only prepares runtime context and dispatches.

## Environment and setup for contributors
- Python 3.10+ with `pip` and `venv`. Install dev dependencies with
  `pip install -e .[dev]`.
- Hardware runners (Raspberry Pi) need device permissions for GPIO, UART, SPI,
  and serial ports; host-only development can use dummy drivers.
- Recommended pre-commit checks: `ruff`/`flake8` for style, `pytest` for unit
  tests, and `mypy` or `pyright` if you add typing-heavy code.

## Adding new peripherals
1. **Implement a driver** in `src/py_micro_hil/peripherals/` that satisfies the
   pattern used by `RPiGPIO`, `RPiPWM`, `RPiUART`, etc. Provide `initialize()`
   and `release()` plus any protocol-specific methods you need in tests.
2. **Extend the YAML loader** (`peripheral_config_loader.py`) to parse a new
   block, validate defaults, and construct your driver. Emit clear warnings when
   user input is malformed.
3. **Expose a getter** in `framework_API.py` so test authors can retrieve the
   configured instance without importing your class directly.
4. **Document the schema** in `docs/hardware-configuration.md` and add a small
   usage example under `docs/writing-tests.md`.
5. **Add example tests** under `example/hil_tests/` (or a new folder) so users
   see end-to-end usage.
6. **Verify dummy mode** where possible so CI can exercise the feature without
   hardware access.

## Extending the CLI
- The parser lives in `cli.py` (`parse_args()`), and HTML path handling is in
  `resolve_html_path()`.
- When adding options, update log messages and docs so users can discover the
  feature via `--help`.
- Debug visibility is opt-in: `[DEBUG]` messages are only emitted when the
  `--debug` flag is set and the `Logger` is initialized with `debug_enabled=True`.
- Keep defaults ergonomic (e.g., sensible report locations, automatic folder
  creation) and log any inferred behavior so users understand what happened.
- Add regression tests for new flags to ensure interactions with defaults and
  report generation remain stable.

## Reporting and logging internals
- `Logger` collects console, text log, and HTML entries. HTML output copies a
  `styles.css` next to the report file.
- The test framework appends log entries as tests run; if generation fails, the
  CLI reports the error but does not block exit.
- Preserve report schemas (text + HTML) for backwards compatibility; introduce
  versioned fields if layouts change.

## Testing expectations
- Add or update unit tests for loader changes, CLI flags, and report generation.
- For integration scenarios, prefer dummy drivers so tests remain portable.
- When touching timing-sensitive drivers, document and test expected tolerances
  to avoid regressions on slower CI hardware.

## Contribution checklist
- Follow PEP 8; include or update unit tests where applicable.
- Run `pytest` locally when changing code paths.
- Update documentation and examples when modifying the YAML schema, CLI flags, or
  report layout.
- Prefer incremental, well-scoped commits with descriptive messages.
- Include notes for release/version bumps when introducing breaking changes; add
  ADR entries for significant design decisions to keep architectural rationale
  discoverable.
