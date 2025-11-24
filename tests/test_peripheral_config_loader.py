import yaml
import serial
import pytest
from pathlib import Path
from unittest.mock import patch

from py_micro_hil.peripheral_config_loader import load_peripheral_configuration
from py_micro_hil.peripherals.RPiPeripherals import (
    RPiGPIO, RPiPWM, RPiUART, RPiI2C, RPiSPI, RPiHardwarePWM,
)
from py_micro_hil.peripherals.modbus import ModbusRTU


class DummyLogger:
    def __init__(self):
        self.messages = []

    def log(self, msg, to_console=False, to_log_file=False):
        self.messages.append((msg, to_console, to_log_file))


def write_yaml(tmp_path: Path, payload) -> str:
    p = tmp_path / "cfg.yaml"
    p.write_text(yaml.safe_dump(payload))
    return str(p)


# === Base behaviour ===

@patch("py_micro_hil.peripheral_config_loader.is_raspberry_pi", return_value=False)
def test_missing_file(mock_rpi, tmp_path):
    logger = DummyLogger()
    missing = tmp_path / "nofile.yaml"
    result = load_peripheral_configuration(yaml_file=str(missing), logger=logger)
    assert result is None
    assert any("[ERROR]" in msg for msg, *_ in logger.messages)
    assert any("config file not found" in msg.lower() for msg, *_ in logger.messages)


@patch("py_micro_hil.peripheral_config_loader.is_raspberry_pi", return_value=False)
def test_invalid_yaml(mock_rpi, tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text("{unbalanced: [1,2")  # niepoprawny YAML
    logger = DummyLogger()
    result = load_peripheral_configuration(yaml_file=str(p), logger=logger)
    assert result is None
    assert any("Failed to parse YAML" in msg for msg, *_ in logger.messages)


@patch("py_micro_hil.peripheral_config_loader.is_raspberry_pi", return_value=False)
def test_empty_file_returns_none(mock_rpi, tmp_path):
    p = tmp_path / "empty.yaml"
    p.write_text("")
    logger = DummyLogger()
    result = load_peripheral_configuration(yaml_file=str(p), logger=logger)
    assert result is None
    assert any("empty" in msg.lower() for msg, *_ in logger.messages)


@patch("py_micro_hil.peripheral_config_loader.is_raspberry_pi", return_value=False)
def test_top_level_not_dict(mock_rpi, tmp_path):
    p = tmp_path / "scalar.yaml"
    p.write_text('"just a string"')
    logger = DummyLogger()
    result = load_peripheral_configuration(yaml_file=str(p), logger=logger)
    assert result is None
    assert any("must be a dictionary" in msg for msg, *_ in logger.messages)


# === Minimal / valid ===

@patch("py_micro_hil.peripheral_config_loader.is_raspberry_pi", return_value=True)
def test_minimal_empty_config(mock_rpi, tmp_path):
    path = write_yaml(tmp_path, {})
    result = load_peripheral_configuration(yaml_file=path)
    assert result == {"peripherals": [], "protocols": []}


# === Modbus ===

def test_modbus_valid_and_invalid(tmp_path):
    data_valid = {"protocols": {"modbus": {"port": "/dev/ttyX", "baudrate": 12345}}}
    path = write_yaml(tmp_path, data_valid)
    res = load_peripheral_configuration(yaml_file=path)
    assert len(res["protocols"]) == 1
    assert isinstance(res["protocols"][0], ModbusRTU)

    # nie-dict -> warning
    data_bad = {"protocols": {"modbus": ["oops"]}}
    path = write_yaml(tmp_path, data_bad)
    logger = DummyLogger()
    res2 = load_peripheral_configuration(yaml_file=path, logger=logger)
    assert res2["protocols"] == []
    assert any("Invalid configuration for Modbus" in msg for msg, *_ in logger.messages)


# === UART ===

def test_uart_valid_and_invalid(tmp_path):
    cfg = {"peripherals": {"uart": {"port": "/dev/ttyY", "baudrate": 4800, "parity": "E", "stopbits": 2}}}
    path = write_yaml(tmp_path, cfg)
    res = load_peripheral_configuration(yaml_file=path)
    assert isinstance(res["peripherals"][0], RPiUART)
    uart = res["peripherals"][0]
    assert uart.baudrate == 4800
    assert uart.parity == serial.PARITY_EVEN
    assert uart.stopbits == serial.STOPBITS_TWO

    bad = {"peripherals": {"uart": ["bad"]}}
    path = write_yaml(tmp_path, bad)
    logger = DummyLogger()
    res2 = load_peripheral_configuration(yaml_file=path, logger=logger)
    assert res2["peripherals"] == []
    assert any("Invalid configuration for UART" in msg for msg, *_ in logger.messages)


# === GPIO ===

def test_gpio_various_errors_and_success(tmp_path):
    cfg = {"peripherals": {"gpio": [{"pin": 17, "mode": "out", "initial": "high"}]}}
    path = write_yaml(tmp_path, cfg)
    res = load_peripheral_configuration(yaml_file=path)
    assert isinstance(res["peripherals"][0], RPiGPIO)

    badformat = {"peripherals": {"gpio": ["nope"]}}
    path = write_yaml(tmp_path, badformat)
    logger = DummyLogger()
    res2 = load_peripheral_configuration(yaml_file=path, logger=logger)
    assert res2["peripherals"] == []
    assert any("Invalid GPIO configuration format" in msg for msg, *_ in logger.messages)

    badpin = {"peripherals": {"gpio": [{"pin": "foo", "mode": "in"}]}}
    path = write_yaml(tmp_path, badpin)
    logger = DummyLogger()
    res3 = load_peripheral_configuration(yaml_file=path, logger=logger)
    assert res3["peripherals"] == []
    assert any("Invalid GPIO config" in msg for msg, *_ in logger.messages)

    badmode = {"peripherals": {"gpio": [{"pin": 1, "mode": "XXX", "initial": "low"}]}}
    path = write_yaml(tmp_path, badmode)
    logger = DummyLogger()
    res4 = load_peripheral_configuration(yaml_file=path, logger=logger)
    assert res4["peripherals"] == []
    assert any("Invalid GPIO mode" in msg for msg, *_ in logger.messages)

    badinit = {"peripherals": {"gpio": [{"pin": 1, "mode": "in", "initial": "???"}]}}
    path = write_yaml(tmp_path, badinit)
    logger = DummyLogger()
    res5 = load_peripheral_configuration(yaml_file=path, logger=logger)
    assert res5["peripherals"] == []
    assert any("Invalid GPIO initial value" in msg for msg, *_ in logger.messages)


# === PWM ===

def test_pwm_sections(tmp_path):
    cfg = {"peripherals": {"pwm": [{"pin": 5, "frequency": 2000}]}}
    path = write_yaml(tmp_path, cfg)
    res = load_peripheral_configuration(yaml_file=path)
    assert isinstance(res["peripherals"][0], RPiPWM)

    badfmt = {"peripherals": {"pwm": ["nope"]}}
    path = write_yaml(tmp_path, badfmt)
    logger = DummyLogger()
    res2 = load_peripheral_configuration(yaml_file=path, logger=logger)
    assert res2["peripherals"] == []
    assert any("Invalid PWM configuration format" in msg for msg, *_ in logger.messages)

    badcfg = {"peripherals": {"pwm": [{"frequency": 1000}]}}
    path = write_yaml(tmp_path, badcfg)
    logger = DummyLogger()
    res3 = load_peripheral_configuration(yaml_file=path, logger=logger)
    assert res3["peripherals"] == []
    assert any("Invalid PWM configuration" in msg for msg, *_ in logger.messages)


# === I2C ===

def test_i2c_sections(tmp_path):
    cfg = {"peripherals": {"i2c": {"bus": 1, "frequency": 50000}}}
    path = write_yaml(tmp_path, cfg)
    res = load_peripheral_configuration(yaml_file=path)
    assert isinstance(res["peripherals"][0], RPiI2C)

    bad = {"peripherals": {"i2c": ["nope"]}}
    path = write_yaml(tmp_path, bad)
    logger = DummyLogger()
    res2 = load_peripheral_configuration(yaml_file=path, logger=logger)
    assert res2["peripherals"] == []
    assert any("Invalid configuration for I2C" in msg for msg, *_ in logger.messages)


# === SPI ===

def test_spi_sections(tmp_path):
    cfg = {"peripherals": {"spi": {"bus": 0, "device": 1}}}
    path = write_yaml(tmp_path, cfg)
    res = load_peripheral_configuration(yaml_file=path)
    assert isinstance(res["peripherals"][0], RPiSPI)

    bad = {"peripherals": {"spi": ["nope"]}}
    path = write_yaml(tmp_path, bad)
    logger = DummyLogger()
    res2 = load_peripheral_configuration(yaml_file=path, logger=logger)
    assert res2["peripherals"] == []
    assert any("Invalid configuration for SPI" in msg for msg, *_ in logger.messages)


# === Hardware PWM ===

def test_hardware_pwm_sections(tmp_path):
    cfg = {"peripherals": {"hardware_pwm": [{"pin": 12, "frequency": 500}]}}
    path = write_yaml(tmp_path, cfg)
    res = load_peripheral_configuration(yaml_file=path)
    assert isinstance(res["peripherals"][0], RPiHardwarePWM)

    bad = {"peripherals": {"hardware_pwm": ["bad"]}}
    path = write_yaml(tmp_path, bad)
    logger = DummyLogger()
    res2 = load_peripheral_configuration(yaml_file=path, logger=logger)
    assert res2["peripherals"] == []
    assert any("Invalid Hardware PWM format" in msg for msg, *_ in logger.messages)
