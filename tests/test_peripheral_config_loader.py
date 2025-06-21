import yaml
import pytest
from pathlib import Path
from py_micro_hil.peripheral_config_loader import (
    load_peripheral_configuration,
    RPiGPIO, RPiPWM, RPiUART, RPiI2C, RPiSPI, ModbusRTU
)

class DummyLogger:
    def __init__(self):
        self.messages = []

    def log(self, msg, to_console=False, to_log_file=False):
        self.messages.append((msg, to_console, to_log_file))


def write_yaml(tmp_path: Path, data):
    file = tmp_path / "cfg.yaml"
    file.write_text(yaml.safe_dump(data))
    return str(file)


def test_missing_file(tmp_path):
    logger = DummyLogger()
    with pytest.raises(ValueError):
        load_peripheral_configuration(yaml_file=str(tmp_path/"nope.yaml"), logger=logger)
    assert any("[ERROR]" in msg for msg, *_ in logger.messages)


def test_invalid_yaml(tmp_path):
    f = tmp_path / "bad.yaml"
    f.write_text("{unbalanced: [1, 2")  # causes yaml.YAMLError
    logger = DummyLogger()
    with pytest.raises(ValueError):
        load_peripheral_configuration(yaml_file=str(f), logger=logger)
    assert any("Failed to parse YAML" in msg for msg, *_ in logger.messages)


def test_yaml_not_dict(tmp_path):
    f = tmp_path / "not_dict.yaml"
    f.write_text('"string not dict"')  # valid YAML scalar
    logger = DummyLogger()
    with pytest.raises(ValueError):
        load_peripheral_configuration(yaml_file=str(f), logger=logger)
    assert any("YAML content must be a dictionary" in msg for msg, *_ in logger.messages)


def test_empty_file(tmp_path):
    f = tmp_path / "empty.yaml"
    f.write_text("")  # empty
    logger = DummyLogger()
    result = load_peripheral_configuration(yaml_file=str(f), logger=logger)
    assert result == {"peripherals": [], "protocols": []}
    assert any("[WARNING]" in msg and "empty" in msg for msg, *_ in logger.messages)


def test_minimal_config(tmp_path):
    fpath = write_yaml(tmp_path, {})
    res = load_peripheral_configuration(yaml_file=fpath)
    assert res == {"peripherals": [], "protocols": []}


def test_modbus_protocol(tmp_path):
    data = {"protocols": {"modbus": {"port": "/dev/ttyUSB0", "baudrate": 115200}}}
    fpath = write_yaml(tmp_path, data)
    res = load_peripheral_configuration(yaml_file=fpath)
    assert isinstance(res["protocols"][0], ModbusRTU)


def test_uart_peripheral(tmp_path):
    data = {"peripherals": {"uart": {"port": "/ttyX", "baudrate": 4800}}}
    fpath = write_yaml(tmp_path, data)
    res = load_peripheral_configuration(yaml_file=fpath)
    assert isinstance(res["peripherals"][0], RPiUART)


def test_gpio_valid(tmp_path):
    data = {"peripherals": {"gpio": [{"pin": 17, "mode": "out", "initial": "high"}]}}
    fpath = write_yaml(tmp_path, data)
    res = load_peripheral_configuration(yaml_file=fpath)
    assert isinstance(res["peripherals"][0], RPiGPIO)


def test_gpio_invalid(tmp_path):
    data = {"peripherals": {"gpio": [{"pin": "foo", "mode": "in"}]}}
    fpath = write_yaml(tmp_path, data)
    logger = DummyLogger()
    res = load_peripheral_configuration(yaml_file=fpath, logger=logger)
    assert res == {"peripherals": [], "protocols": []}
    assert any("Invalid GPIO config" in msg for msg, *_ in logger.messages)


def test_pwm_valid(tmp_path):
    data = {"peripherals": {"pwm": [{"pin": 5, "frequency": 2000}]}}
    fpath = write_yaml(tmp_path, data)
    res = load_peripheral_configuration(yaml_file=fpath)
    assert isinstance(res["peripherals"][0], RPiPWM)


def test_pwm_invalid_format(tmp_path):
    data = {"peripherals": {"pwm": ["not a dict"]}}
    fpath = write_yaml(tmp_path, data)
    logger = DummyLogger()
    res = load_peripheral_configuration(yaml_file=fpath, logger=logger)
    assert res["peripherals"] == []
    assert any("Invalid PWM configuration format" in msg for msg, *_ in logger.messages)


def test_i2c_valid(tmp_path):
    data = {"peripherals": {"i2c": {"bus": 1, "frequency": 50000}}}
    fpath = write_yaml(tmp_path, data)
    res = load_peripheral_configuration(yaml_file=fpath)
    assert isinstance(res["peripherals"][0], RPiI2C)


def test_i2c_invalid(tmp_path):
    data = {"peripherals": {"i2c": ["bad"]}}
    fpath = write_yaml(tmp_path, data)
    logger = DummyLogger()
    res = load_peripheral_configuration(yaml_file=fpath, logger=logger)
    assert res["peripherals"] == []
    assert any("Invalid configuration for I2C" in msg for msg, *_ in logger.messages)


def test_spi_valid(tmp_path):
    data = {"peripherals": {"spi": {"bus": 0, "device": 1}}}
    fpath = write_yaml(tmp_path, data)
    res = load_peripheral_configuration(yaml_file=fpath)
    assert isinstance(res["peripherals"][0], RPiSPI)


def test_spi_invalid(tmp_path):
    data = {"peripherals": {"spi": ["bad"]}}
    fpath = write_yaml(tmp_path, data)
    logger = DummyLogger()
    res = load_peripheral_configuration(yaml_file=fpath, logger=logger)
    assert res["peripherals"] == []
    assert any("Invalid configuration for SPI" in msg for msg, *_ in logger.messages)
