# Writing Tests

Tests live in Python modules discovered by the `hiltests` runner. This guide
covers layout, lifecycle hooks, assertion helpers, signature expectations, and
peripheral-specific examples so authors can build reliable suites for both
hardware rigs and simulation hosts. For a function-by-function breakdown of the
helpers available to test authors, see the [Test API Reference](test-api-reference.md).

## Folder layout and naming
- Default directory: `./hil_tests/`.
- Files must start with `test_` and use the `.py` extension.
- Each file represents a **test group** and may define:
  - Test functions named `test_*`.
  - Optional `setup_group()` and `teardown_group()` functions called once per
    file.
- Use a different directory with `hiltests --test-dir ./custom_tests`. Paths are
  resolved absolutely so you can run from any working directory.

A multi-suite structure might look like:
```text
hil_tests/
├─ test_gpio_inputs.py
├─ test_pwm_outputs.py
└─ test_spi_flash.py
hil_tests_ext/
└─ test_field_rig.py
```
Run against the second suite by passing `--test-dir ./hil_tests_ext`.

### Scaffolding a new group from the template
Use the CLI flag to create a starter file without running any tests:

```bash
hiltests --create-test-group <group_name> [target_dir]
```

- If `target_dir` is omitted, the generator uses the path from `--test-dir`
  (default: `./hil_tests`).
- The file is named `test_<group_name>.py` and is populated from
  `example/test_group_template.py`.
- The `{test_group_name}` placeholder inside the template is rendered with the
  provided name so setup/teardown messages already include your group.

When the target folder does not exist or the destination file already exists,
the command exits with an error and a log entry instead of overwriting
anything.

## Function signatures and context
The runner wraps each test and inspects its signature:
- **No parameters** → the function is called directly.
- **Any parameters** → the framework instance is passed as the first argument
  (useful if you want to call `framework.logger` or inspect counts).

Group-level hooks take no arguments. Context is automatically injected so
assertions and `TEST_INFO_MESSAGE` know which test is running.

If `setup_group()` raises, the entire group is skipped and the failure is stored
as a synthetic test result for reporting. `teardown_group()` errors are also
captured as failures after the last test so cleanup issues stay visible in
reports.

### Lifecycle hook example
```python
shared_uart = None


def setup_group():
    global shared_uart
    shared_uart = get_RPiUART_peripheral()
    TEST_INFO_MESSAGE("UART ready for echo tests")


def teardown_group():
    TEST_INFO_MESSAGE("Tearing down UART group")


def test_uart_echo():
    shared_uart.send(b"ping")
    TEST_ASSERT_EQUAL(b"ping", shared_uart.receive(4))
```

## Minimal template
```python
from py_micro_hil.assertions import *
from py_micro_hil.framework_API import *


def setup_group():
    TEST_INFO_MESSAGE("Preparing test group")


def teardown_group():
    TEST_INFO_MESSAGE("Cleaning up test group")


def test_led_toggle():
    gpio = get_RPiGPIO_peripheral()
    gpio.write("LED_RED", "HIGH")
    TEST_ASSERT_EQUAL(1, gpio.read("PUSHBUTTON"))
```

## Assertion helpers
- `TEST_ASSERT_EQUAL(expected, actual)` — equality with descriptive errors.
- `TEST_ASSERT_TRUE(condition)` — truthiness check.
- `TEST_ASSERT_IN(item, collection)` — membership check.
- `TEST_INFO_MESSAGE(message)` — informational log that flows to console, log,
  and HTML report.
- `TEST_FAIL_MESSAGE(message)` — explicit failure with context.

These helpers automatically report to the active framework; when run outside the
runner (e.g., REPL), they return symbolic tuples to aid debugging.

### Assertion usage examples
```python
def test_assert_equal_and_true():
    gpio = get_RPiGPIO_peripheral()
    gpio.write("LED_RED", "high")  # string values map to 1/0
    TEST_ASSERT_EQUAL(1, gpio.read("LED_RED"))
    TEST_ASSERT_TRUE(gpio.read("LED_RED"))


def test_assert_in():
    peripherals = ["gpio", "spi", "uart"]
    TEST_ASSERT_IN("spi", peripherals)


def test_info_and_fail_message():
    TEST_INFO_MESSAGE("About to force a failure for demonstration")
    TEST_FAIL_MESSAGE("Deliberate failure to showcase reporting")
```

## Accessing configured peripherals
The framework registers peripherals from the active YAML file (see **Hardware
Configuration**). Use getters from `py_micro_hil.framework_API`:
- `get_RPiGPIO_peripheral()` — software-accessible GPIO pins.
- `get_RPiPWM_peripheral()` / `get_RPiHardwarePWM_peripheral()` — PWM outputs.
- `get_RPiUART_peripheral()` — UART channel from the `uart` block.
- `get_RPiI2C_peripheral()` — I²C controller declared under `i2c`.
- `get_RPiSPI_peripheral()` — SPI controller declared under `spi`.
- `get_RPiOneWire_peripheral()` — 1-Wire bus for DS18B20 sensors.
- `get_ModBus_peripheral()` — Modbus RTU client configured under
  `protocols.modbus`.

Dummy implementations are returned on non-Raspberry Pi hosts so you can execute
and debug tests without hardware (assertions still run).

## End-to-end examples by peripheral
### GPIO
You can address configured pins either by their numeric BCM index or by the
`name` token declared in `peripherals.gpio` of `peripherals_config.yaml`. GPIO
writes also accept string literals `"high"`/`"HIGH"` and `"low"`/`"LOW"` in
addition to `1`/`0`.

After the YAML is loaded, every `name` token is also exposed as a Python
constant alongside `HIGH`/`LOW` helpers so you can skip quotes entirely when
you `from py_micro_hil.peripherals.RPiPeripherals import *`:

```python
gpio.write(PUSHBUTTON, LOW)
gpio.write(RST, HIGH)
```
```python
def test_button_triggers_led():
    gpio = get_RPiGPIO_peripheral()
    TEST_INFO_MESSAGE("Driving LED high on pin 17")
    gpio.write("LED_RED", 1)
    TEST_ASSERT_TRUE(gpio.read("PUSHBUTTON"))  # button input sensed on pin 18
```

Need lower-level access to the underlying GPIO module (for example, to register
edge-detection callbacks that are not wrapped by the helper methods)? Use the
static accessor on `RPiGPIO`—it also works when called on an instance:

```python
from py_micro_hil.peripherals.RPiPeripherals import RPiGPIO


def test_gpio_edge_events():
    gpio = get_RPiGPIO_peripheral()

    # Both forms below return the same module imported by the framework
    gpio_module = RPiGPIO.get_gpio_interface()
    same_module = gpio.get_gpio_interface()

    gpio_module.add_event_detect(18, gpio_module.RISING)
    gpio.write(17, 1)
    TEST_ASSERT_TRUE(gpio_module.event_detected(18))
```

### Software PWM
```python
def test_pwm_frequency_and_duty():
    pwm = get_RPiPWM_peripheral()
    pwm.set_frequency(1000)
    pwm.set_duty_cycle(25)
    TEST_ASSERT_TRUE(True)  # configuration calls completed without error
```

### Hardware PWM
```python
def test_hardware_pwm_ramp():
    hpwm = get_RPiHardwarePWM_peripheral()
    for duty in (10, 50, 90):
        hpwm.set_duty_cycle(duty)
    TEST_ASSERT_TRUE(True)
```

### UART
```python
def test_uart_roundtrip():
    uart = get_RPiUART_peripheral()
    payload = b"ping\n"
    uart.send(payload)
    reply = uart.receive(len(payload))
    TEST_ASSERT_EQUAL(payload, reply)
```

### I²C
```python
def test_i2c_probe_and_read():
    i2c = get_RPiI2C_peripheral()
    devices = i2c.scan()
    TEST_ASSERT_TRUE(len(devices) > 0)

    address = devices[0]
    register = 0x00
    data = i2c.read(address, register, 1)
    TEST_ASSERT_TRUE(len(data) == 1)
```

### SPI
```python
def test_spi_transfer():
    spi = get_RPiSPI_peripheral()
    rx = spi.transfer([0x9F, 0x00, 0x00, 0x00])  # JEDEC ID read frame
    TEST_ASSERT_TRUE(len(rx) == 4)
```

### Modbus RTU
```python
def test_modbus_register_flow():
    modbus = get_ModBus_peripheral()
    slave = 1
    register = 0x000A
    modbus.write_single_register(slave, register, 123)
    values = modbus.read_holding_registers(slave, register, 1)
    TEST_ASSERT_EQUAL(123, values[0])
```

### 1-Wire (DS18B20)
```python
def test_onewire_temperature_read():
    ow = get_RPiOneWire_peripheral()
    devices = ow.scan_devices()
    TEST_ASSERT_TRUE(len(devices) > 0)

    temp_c = ow.read_temperature(devices[0])
    TEST_ASSERT_TRUE(temp_c > -50)  # sanity bound for DS18B20
```

## Advanced authoring patterns
- **Data-driven checks**: wrap repeated patterns in helper functions within the
  same file to keep groups focused.
- **Parallel suites**: keep separate folders (e.g., `hil_tests_lab/`,
  `hil_tests_prod/`) and pair each with the appropriate YAML via `--config`.
- **Selective execution**: create a temporary folder containing only the tests
  you want, then pass it via `--test-dir` instead of adding complex selection
  logic in code.
- **Logging steps**: add `TEST_INFO_MESSAGE` inside loops or protocol exchanges
  to make HTML reports easier to debug after failures.
- **Deterministic checks**: when timing-sensitive (PWM, SPI), assert on API
  outcomes rather than analog characteristics to keep runs stable across
  hardware and simulation modes.

## Troubleshooting tips
- If a test fails before executing assertions, check YAML parsing and peripheral
  initialization logs at the top of the run output.
- Missing peripherals in YAML result in `None` returns from getters—double-check
  spelling and structure.
- When running on a PC, remember that dummy peripherals do not interact with real
  hardware; adjust expectations accordingly or gate hardware-only cases via
  environment variables.
