import yaml
import pytest
from pathlib import Path
from unittest.mock import patch

from py_micro_hil.peripheral_config_loader import load_peripheral_configuration
from py_micro_hil.peripherals.RPiPeripherals import (
    RPiGPIO,
    RPiPWM,
    RPiUART,
    RPiI2C,
    RPiSPI,
    RPiHardwarePWM,
    RPiOneWire,
)
from py_micro_hil.peripherals.protocols import ModbusRTU


# ============================================================
# FIXTURE: DISABLE KERNEL ONEWIRE FOR ALL NON-ONEWIRE TESTS
# ============================================================


@pytest.fixture(autouse=True)
def disable_kernel_onewire(monkeypatch):
    monkeypatch.setattr(
        "py_micro_hil.peripheral_config_loader._detect_kernel_onewire_pin", lambda: None
    )


# ============================================================
# HELPERS
# ============================================================


class DummyLogger:
    def __init__(self):
        self.messages = []

    def log(self, msg, to_console=False, to_log_file=False):
        self.messages.append(msg)


def write_yaml(tmp_path: Path, payload) -> str:
    path = tmp_path / "cfg.yaml"
    path.write_text(yaml.safe_dump(payload))
    return str(path)


# MOCKS
def mock_dev_exists_true(path):
    return True


def mock_dev_exists_false(path):
    return False


def mock_gpio_consumers_empty():
    return {}


def mock_gpio_consumers_pin4_w1():
    return {4: "w1-gpio"}


# ============================================================
# BASIC FILE / YAML TESTS
# ============================================================


@patch("py_micro_hil.peripheral_config_loader._dev_exists", mock_dev_exists_true)
@patch("py_micro_hil.peripheral_config_loader._gpio_consumers", mock_gpio_consumers_empty)
def test_missing_file(tmp_path):
    logger = DummyLogger()
    missing = tmp_path / "nofile.yaml"

    res = load_peripheral_configuration(str(missing), logger=logger)

    assert res is None
    assert any("not found" in m.lower() for m in logger.messages)


@patch("py_micro_hil.peripheral_config_loader._dev_exists", mock_dev_exists_true)
@patch("py_micro_hil.peripheral_config_loader._gpio_consumers", mock_gpio_consumers_empty)
def test_invalid_yaml(tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text("{bad:")

    logger = DummyLogger()
    res = load_peripheral_configuration(str(p), logger=logger)

    assert res is None
    assert any("failed to parse yaml" in m.lower() for m in logger.messages)


@patch("py_micro_hil.peripheral_config_loader._dev_exists", mock_dev_exists_true)
@patch("py_micro_hil.peripheral_config_loader._gpio_consumers", mock_gpio_consumers_empty)
def test_empty_yaml(tmp_path):
    p = tmp_path / "empty.yaml"
    p.write_text("")

    logger = DummyLogger()
    res = load_peripheral_configuration(str(p), logger=logger)

    assert res is None
    assert any("empty" in m.lower() for m in logger.messages)


# ============================================================
# MODBUS
# ============================================================


@patch("py_micro_hil.peripheral_config_loader._dev_exists", mock_dev_exists_true)
@patch("py_micro_hil.peripheral_config_loader._gpio_consumers", mock_gpio_consumers_empty)
def test_modbus_valid_and_invalid(tmp_path):

    # VALID
    valid = {
        "protocols": {
            "modbus": {
                "port": "/dev/ttyUSB0",
                "baudrate": 115200,
                "parity": "E",
                "stopbits": 2,
                "timeout": 2,
            }
        }
    }

    p = write_yaml(tmp_path, valid)
    res = load_peripheral_configuration(p)

    assert len(res["protocols"]) == 1
    assert isinstance(res["protocols"][0], ModbusRTU)

    # INVALID
    invalid = {"protocols": {"modbus": ["bad"]}}
    p2 = write_yaml(tmp_path, invalid)
    logger = DummyLogger()

    res2 = load_peripheral_configuration(p2, logger=logger)

    # loader returns None due to errors
    assert res2 is None
    assert any("invalid configuration for modbus" in m.lower() for m in logger.messages)


# ============================================================
# UART
# ============================================================


@patch("py_micro_hil.peripheral_config_loader._dev_exists", mock_dev_exists_true)
@patch("py_micro_hil.peripheral_config_loader._gpio_consumers", mock_gpio_consumers_empty)
def test_uart_valid(tmp_path):
    cfg = {
        "peripherals": {
            "uart": {"port": "/dev/ttyUSB0", "baudrate": 4800, "parity": "E", "stopbits": 2}
        }
    }

    p = write_yaml(tmp_path, cfg)
    res = load_peripheral_configuration(p)

    uart = res["peripherals"][0]
    assert isinstance(uart, RPiUART)


@patch("py_micro_hil.peripheral_config_loader._dev_exists", mock_dev_exists_true)
@patch("py_micro_hil.peripheral_config_loader._gpio_consumers", mock_gpio_consumers_empty)
def test_uart_invalid_port(tmp_path):
    cfg = {"peripherals": {"uart": {"port": "/dev/ttyINVALID"}}}
    logger = DummyLogger()

    p = write_yaml(tmp_path, cfg)
    res = load_peripheral_configuration(p, logger=logger)

    assert res is None
    assert any("invalid uart port" in m.lower() for m in logger.messages)


# ============================================================
# GPIO
# ============================================================


@patch("py_micro_hil.peripheral_config_loader._dev_exists", mock_dev_exists_true)
@patch("py_micro_hil.peripheral_config_loader._gpio_consumers", mock_gpio_consumers_empty)
def test_gpio_valid(tmp_path):
    cfg = {"peripherals": {"gpio": [{"pin": 17, "mode": "out"}]}}
    p = write_yaml(tmp_path, cfg)

    res = load_peripheral_configuration(p)
    assert isinstance(res["peripherals"][0], RPiGPIO)


@patch("py_micro_hil.peripheral_config_loader._dev_exists", mock_dev_exists_true)
@patch("py_micro_hil.peripheral_config_loader._gpio_consumers", mock_gpio_consumers_empty)
def test_gpio_invalid_pin(tmp_path):
    cfg = {"peripherals": {"gpio": [{"pin": 99, "mode": "in"}]}}
    logger = DummyLogger()

    p = write_yaml(tmp_path, cfg)
    res = load_peripheral_configuration(p, logger=logger)

    assert res is None
    assert any("invalid gpio pin" in m.lower() for m in logger.messages)


# ============================================================
# PWM / I2C / SPI / HW PWM – identical rule: kernel W1 disabled
# ============================================================


@patch("py_micro_hil.peripheral_config_loader._dev_exists", mock_dev_exists_true)
@patch("py_micro_hil.peripheral_config_loader._gpio_consumers", mock_gpio_consumers_empty)
def test_pwm_valid(tmp_path):
    cfg = {"peripherals": {"pwm": [{"pin": 5, "frequency": 1000}]}}
    p = write_yaml(tmp_path, cfg)
    res = load_peripheral_configuration(p)
    assert isinstance(res["peripherals"][0], RPiPWM)


@patch("py_micro_hil.peripheral_config_loader._dev_exists", mock_dev_exists_true)
@patch("py_micro_hil.peripheral_config_loader._gpio_consumers", mock_gpio_consumers_empty)
def test_i2c_valid(tmp_path):
    cfg = {"peripherals": {"i2c": {"bus": 1}}}
    p = write_yaml(tmp_path, cfg)

    res = load_peripheral_configuration(p)
    assert isinstance(res["peripherals"][0], RPiI2C)


@patch("py_micro_hil.peripheral_config_loader._dev_exists", mock_dev_exists_true)
@patch("py_micro_hil.peripheral_config_loader._gpio_consumers", mock_gpio_consumers_empty)
def test_spi_valid(tmp_path):
    cfg = {"peripherals": {"spi": {"bus": 0, "device": 1}}}
    p = write_yaml(tmp_path, cfg)

    res = load_peripheral_configuration(p)
    assert isinstance(res["peripherals"][0], RPiSPI)


@patch("py_micro_hil.peripheral_config_loader._dev_exists", mock_dev_exists_true)
@patch("py_micro_hil.peripheral_config_loader._gpio_consumers", mock_gpio_consumers_empty)
def test_hardware_pwm_valid(tmp_path):
    cfg = {"peripherals": {"hardware_pwm": [{"pin": 12}]}}
    p = write_yaml(tmp_path, cfg)

    res = load_peripheral_configuration(p)
    assert isinstance(res["peripherals"][0], RPiHardwarePWM)


# ============================================================
# 1-WIRE – EXPLICIT KERNEL ENABLE
# ============================================================


@patch("py_micro_hil.peripheral_config_loader._dev_exists", mock_dev_exists_true)
@patch("py_micro_hil.peripheral_config_loader._gpio_consumers", mock_gpio_consumers_empty)
@patch("py_micro_hil.peripheral_config_loader._detect_kernel_onewire_pin", lambda: 4)
def test_onewire_yaml_valid(tmp_path):
    cfg = {"peripherals": {"onewire": {}}}
    p = write_yaml(tmp_path, cfg)

    res = load_peripheral_configuration(p)

    # kernel one-wire + yaml one-wire -> 2 objects
    assert len(res["peripherals"]) == 2
    assert all(isinstance(x, RPiOneWire) for x in res["peripherals"])


@patch("py_micro_hil.peripheral_config_loader._dev_exists", mock_dev_exists_true)
@patch("py_micro_hil.peripheral_config_loader._gpio_consumers", mock_gpio_consumers_empty)
def test_onewire_yaml_invalid_pin(tmp_path):
    cfg = {"peripherals": {"onewire": {"pin": 7}}}
    logger = DummyLogger()
    p = write_yaml(tmp_path, cfg)

    res = load_peripheral_configuration(p, logger=logger)

    assert res is None
    assert any("expected 'onewire: true'" in m.lower() for m in logger.messages)


@patch("py_micro_hil.peripheral_config_loader._dev_exists", mock_dev_exists_true)
@patch("py_micro_hil.peripheral_config_loader._detect_kernel_onewire_pin", lambda: 4)
@patch("py_micro_hil.peripheral_config_loader._gpio_consumers", mock_gpio_consumers_pin4_w1)
def test_onewire_yaml_conflict(tmp_path):
    cfg = {"peripherals": {"onewire": {}}}
    logger = DummyLogger()

    p = write_yaml(tmp_path, cfg)
    res = load_peripheral_configuration(p, logger=logger)

    assert res is None
    assert any("cannot be reused" in m.lower() for m in logger.messages)


# ============================================================
# YAML RESOURCE CONFLICTS
# ============================================================


def test_yaml_conflict_gpio_gpio(tmp_path, monkeypatch):
    cfg = {
        "peripherals": {
            "gpio": [
                {"pin": 4, "mode": "out"},
                {"pin": 4, "mode": "in"},
            ]
        }
    }

    logger = DummyLogger()
    p = write_yaml(tmp_path, cfg)

    res = load_peripheral_configuration(p, logger=logger)

    assert res is None
    assert any("pin 4 conflict between gpio" in m.lower() for m in logger.messages)


def test_yaml_conflict_uart_modbus(tmp_path, monkeypatch):
    cfg = {
        "peripherals": {"uart": {"port": "/dev/ttyUSB0"}},
        "protocols": {"modbus": {"port": "/dev/ttyUSB0"}},
    }

    logger = DummyLogger()
    p = write_yaml(tmp_path, cfg)

    res = load_peripheral_configuration(p, logger=logger)

    assert res is None
    assert any("port /dev/ttyusb0 conflict" in m.lower() for m in logger.messages)


# ============================================================
# SYSTEM-LEVEL DEVICE VALIDATION
# ============================================================


@patch("py_micro_hil.peripheral_config_loader._dev_exists", mock_dev_exists_false)
def test_system_missing_i2c(tmp_path):
    cfg = {"peripherals": {"i2c": {"bus": 1}}}
    logger = DummyLogger()
    p = write_yaml(tmp_path, cfg)

    res = load_peripheral_configuration(p, logger=logger)

    assert res is None
    assert any("i2c bus 1 is not enabled" in m.lower() for m in logger.messages)


@patch("py_micro_hil.peripheral_config_loader._dev_exists", mock_dev_exists_false)
def test_system_missing_spi(tmp_path):
    cfg = {"peripherals": {"spi": {"bus": 0, "device": 1}}}
    logger = DummyLogger()
    p = write_yaml(tmp_path, cfg)

    res = load_peripheral_configuration(p, logger=logger)

    assert res is None
    assert any("spi 0.1 is not enabled" in m.lower() for m in logger.messages)


# ============================================================
# UART – FULL NEGATIVE TESTS
# ============================================================


@patch("py_micro_hil.peripheral_config_loader._gpio_consumers", mock_gpio_consumers_empty)
@patch("py_micro_hil.peripheral_config_loader._dev_exists", mock_dev_exists_true)
def test_uart_invalid_baudrate(tmp_path):
    cfg = {"peripherals": {"uart": {"port": "/dev/ttyUSB0", "baudrate": -1}}}
    logger = DummyLogger()
    p = write_yaml(tmp_path, cfg)

    res = load_peripheral_configuration(p, logger=logger)
    assert res is None
    assert any("invalid uart baudrate" in m.lower() for m in logger.messages)


@patch("py_micro_hil.peripheral_config_loader._gpio_consumers", mock_gpio_consumers_empty)
@patch("py_micro_hil.peripheral_config_loader._dev_exists", mock_dev_exists_true)
def test_uart_invalid_parity(tmp_path):
    cfg = {"peripherals": {"uart": {"port": "/dev/ttyUSB0", "parity": "X"}}}
    logger = DummyLogger()
    p = write_yaml(tmp_path, cfg)

    res = load_peripheral_configuration(p, logger=logger)
    assert res is None
    assert any("invalid uart parity" in m.lower() for m in logger.messages)


@patch("py_micro_hil.peripheral_config_loader._gpio_consumers", mock_gpio_consumers_empty)
@patch("py_micro_hil.peripheral_config_loader._dev_exists", mock_dev_exists_true)
def test_uart_invalid_stopbits(tmp_path):
    cfg = {"peripherals": {"uart": {"port": "/dev/ttyUSB0", "stopbits": 3}}}
    logger = DummyLogger()
    p = write_yaml(tmp_path, cfg)

    res = load_peripheral_configuration(p, logger=logger)
    assert res is None
    assert any("invalid uart stopbits" in m.lower() for m in logger.messages)


# ============================================================
# SOFTWARE PWM – negative tests
# ============================================================


def test_pwm_invalid_pin(tmp_path):
    cfg = {"peripherals": {"pwm": [{"pin": 999, "frequency": 1000}]}}
    logger = DummyLogger()

    p = write_yaml(tmp_path, cfg)
    res = load_peripheral_configuration(p, logger=logger)

    assert res is None
    assert any("invalid pwm pin" in m.lower() for m in logger.messages)


def test_pwm_invalid_frequency(tmp_path):
    cfg = {"peripherals": {"pwm": [{"pin": 5, "frequency": -1}]}}
    logger = DummyLogger()

    p = write_yaml(tmp_path, cfg)
    res = load_peripheral_configuration(p, logger=logger)

    assert res is None
    assert any("invalid pwm frequency" in m.lower() for m in logger.messages)


# ============================================================
# HARDWARE PWM – negative tests
# ============================================================


def test_hw_pwm_invalid_pin(tmp_path):
    cfg = {"peripherals": {"hardware_pwm": [{"pin": 7}]}}
    logger = DummyLogger()
    p = write_yaml(tmp_path, cfg)

    res = load_peripheral_configuration(p, logger=logger)

    assert res is None
    assert any("does not support hardware pwm" in m.lower() for m in logger.messages)


def test_hw_pwm_invalid_frequency(tmp_path):
    cfg = {"peripherals": {"hardware_pwm": [{"pin": 12, "frequency": -1}]}}
    logger = DummyLogger()
    p = write_yaml(tmp_path, cfg)

    res = load_peripheral_configuration(p, logger=logger)

    assert res is None
    assert any("invalid hardware pwm frequency" in m.lower() for m in logger.messages)


# ============================================================
# I2C – negative tests
# ============================================================


def test_i2c_invalid_bus(tmp_path):
    cfg = {"peripherals": {"i2c": {"bus": 8}}}
    logger = DummyLogger()

    p = write_yaml(tmp_path, cfg)
    res = load_peripheral_configuration(p, logger=logger)

    assert res is None
    assert any("invalid i2c bus" in m.lower() for m in logger.messages)


def test_i2c_invalid_frequency(tmp_path):
    cfg = {"peripherals": {"i2c": {"bus": 1, "frequency": -10}}}
    logger = DummyLogger()

    p = write_yaml(tmp_path, cfg)
    res = load_peripheral_configuration(p, logger=logger)

    assert res is None
    assert any("invalid i2c frequency" in m.lower() for m in logger.messages)


# ============================================================
# SPI – full negative coverage
# ============================================================


def test_spi_invalid_bus(tmp_path):
    cfg = {"peripherals": {"spi": {"bus": -1, "device": 0}}}
    logger = DummyLogger()

    p = write_yaml(tmp_path, cfg)
    res = load_peripheral_configuration(p, logger=logger)

    assert res is None
    assert any("invalid spi bus" in m.lower() for m in logger.messages)


def test_spi_invalid_device(tmp_path):
    cfg = {"peripherals": {"spi": {"bus": 0, "device": 5}}}
    logger = DummyLogger()

    p = write_yaml(tmp_path, cfg)
    res = load_peripheral_configuration(p, logger=logger)

    assert res is None
    assert any("invalid spi device" in m.lower() for m in logger.messages)


def test_spi_invalid_mode(tmp_path):
    cfg = {"peripherals": {"spi": {"bus": 0, "device": 0, "mode": 5}}}
    logger = DummyLogger()

    p = write_yaml(tmp_path, cfg)
    res = load_peripheral_configuration(p, logger=logger)

    assert res is None
    assert any("invalid spi mode" in m.lower() for m in logger.messages)


# ============================================================
# GPIO – additional negative tests
# ============================================================


@patch("py_micro_hil.peripheral_config_loader._dev_exists", mock_dev_exists_true)
def test_gpio_invalid_initial(tmp_path):
    cfg = {"peripherals": {"gpio": [{"pin": 4, "mode": "out", "initial": "XYZ"}]}}
    logger = DummyLogger()

    p = write_yaml(tmp_path, cfg)
    res = load_peripheral_configuration(p, logger=logger)

    # invalid initial is WARNING, not ERROR → loader continues
    assert res == {"peripherals": [], "protocols": []}
    assert any("invalid gpio initial" in m.lower() for m in logger.messages)
