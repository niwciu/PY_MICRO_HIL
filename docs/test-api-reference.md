# Test API Reference

This guide lists the public helpers exposed to test authors. Import them at the
top of each group:

```python
from py_micro_hil.assertions import *
from py_micro_hil.framework_API import *
```

## Assertion and logging helpers
| Helper | Purpose |
|--------|---------|
| `TEST_ASSERT_EQUAL(expected, actual)` | Record a pass/fail when `expected == actual`; reports comparison details on failure. |
| `TEST_ASSERT_TRUE(condition)` | Succeeds when `condition` is truthy; otherwise logs a failure. |
| `TEST_ASSERT_IN(item, collection)` | Checks membership (`item in collection`). |
| `TEST_INFO_MESSAGE(message)` | Adds an informational log line tied to the current test. |
| `TEST_FAIL_MESSAGE(message)` | Forces a failure with the supplied message. |

When executed by the runner, these functions emit results through the active
framework context. When called interactively (no context), they return symbolic
tuples to help with debugging in a REPL or notebook.

Example that mixes assertions and log messages:

```python
def test_spi_smoke():
    TEST_INFO_MESSAGE("Opening SPI peripheral")
    spi = get_RPiSPI_peripheral()
    TEST_ASSERT_EQUAL([0x9F, 0xAA, 0xBB], spi.transfer([0x9F, 0x00, 0x00]))
```

## Group lifecycle hooks
Define these optional functions alongside your tests to set up and tear down
shared state:

- `setup_group()` — called once before any `test_*` in the file.
- `teardown_group()` — called once after the last test in the file.

Hooks take no arguments. Failures raised by either hook are captured and
reported in the run summary.

## Framework API getters
Use the getters below to retrieve initialized peripherals from the active
framework. Dummy implementations are returned automatically on non-Raspberry Pi
hosts so you can exercise logic without hardware.

| Getter | Returns | Common methods |
|--------|---------|----------------|
| `get_RPiGPIO_peripheral()` | GPIO driver configured from YAML. | `write(pin_or_name, value)` (accepts `"high"/"low"`), `read(pin_or_name)`, `toggle(pin_or_name)`, `get_gpio_interface()` |
| `get_RPiPWM_peripheral()` | Software PWM channel. | `set_duty_cycle(percent)`, `set_frequency(hz)` |
| `get_RPiHardwarePWM_peripheral()` | Hardware PWM channel. | `set_duty_cycle(percent)`, `set_frequency(hz)` |
| `get_RPiUART_peripheral()` | UART serial interface. | `send(data)`, `receive(size)`, `readline()` |
| `get_RPiI2C_peripheral()` | I²C bus controller. | `scan()`, `read(addr, reg, length)`, `write(addr, reg, data)`, `read_byte(addr)`, `write_word(addr, reg, value)` |
| `get_RPiSPI_peripheral()` | SPI controller. | `transfer(bytes_or_ints)`, `write_bytes(data)`, `read_bytes(length)` |
| `get_RPiOneWire_peripheral()` | 1-Wire helper for DS18B20 sensors. | `scan_devices()`, `read_temperature(device_id)` |
| `get_ModBus_peripheral()` | Modbus RTU client. | `write_single_register(slave, register, value)`, `read_holding_registers(slave, register, count)` |

Example using a peripheral getter with assertions and logging:

```python
def test_modbus_roundtrip():
    client = get_ModBus_peripheral()
    slave = 1
    register = 0x0010
    TEST_INFO_MESSAGE("Writing setpoint")
    client.write_single_register(slave, register, 42)
    TEST_ASSERT_EQUAL([42], client.read_holding_registers(slave, register, 1))
```

## Generating a template-driven group
To bootstrap a new group file, run:

```bash
hiltests --create-test-group <group_name> [target_dir]
```

The command renders `example/test_group_template.py`, replacing the
`{test_group_name}` placeholder with your supplied name before writing
`test_<group_name>.py` to the chosen directory.
