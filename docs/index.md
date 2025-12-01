# Py-Micro-HIL Documentation

Py-Micro-HIL is a modular, lightweight **Hardware-in-the-Loop (HIL)** framework
for Python. It focuses on embedded peripherals (GPIO, PWM, UART, I²C, SPI, and
Modbus RTU) and can run on Raspberry Pi hardware or in a simulated mode on any
PC so that teams can write, review, and debug tests without being blocked by
physical rigs.

This site targets **two audiences**:

- **Test authors and operators** who need clear instructions to configure
  hardware, organize test suites, and run them locally or in CI/CD.
- **Framework contributors** who want to extend the YAML schema, add new
  peripherals, or improve the CLI and reporting pipeline.

Use the navigation bar for dedicated guides, or start with:

- [Getting Started](getting-started.md) — install, set up folders, and run your
  first suite.
- [Hardware Configuration](hardware-configuration.md) — full YAML schema,
  per-peripheral options, validation rules, and ready-to-run snippets.
- [Writing Tests](writing-tests.md) — structure, fixtures, assertion helpers,
  and examples for every supported peripheral.
- [Running Tests & CLI](running-tests.md) — command reference, combinations of
  flags, and CI-friendly invocation patterns.
- [Reports & Artifacts](reports-and-artifacts.md) — HTML/text outputs and how to
  publish them to web roots like `public_html`.
- [System Architecture & Extensibility](architecture.md) — lifecycle, layer
  responsibilities, public API surface, and extensibility contracts for
  contributors.
- [Developer Guide](developer-guide.md) — code layout, testing expectations, and
  contribution practices.
- [FAQ](faq.md) — quick answers and troubleshooting tips.
