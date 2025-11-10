import yaml
import serial
import pytest
from pathlib import Path
from py_micro_hil.peripheral_config_loader import (
    load_peripheral_configuration,
)
from py_micro_hil.peripherals.RPiPeripherals import (
    RPiGPIO, RPiPWM, RPiUART, RPiI2C, RPiSPI,
    RPiHardwarePWM,# RPi1Wire, RPiADC, RPiCAN,
)
from py_micro_hil.peripherals.modbus import ModbusRTU


class DummyLogger:
    def __init__(self):
        # przechowuje tuple (msg, to_console, to_log_file)
        self.messages = []

    def log(self, msg, to_console=False, to_log_file=False):
        self.messages.append((msg, to_console, to_log_file))


def write_yaml(tmp_path: Path, payload) -> str:
    p = tmp_path / "cfg.yaml"
    p.write_text(yaml.safe_dump(payload))
    return str(p)


def test_missing_file(tmp_path):
    logger = DummyLogger()
    missing = tmp_path / "nofile.yaml"
    with pytest.raises(ValueError) as exc:
        load_peripheral_configuration(yaml_file=str(missing), logger=logger)
    # powinien być komunikat ERROR
    assert any("[ERROR]" in msg for msg, *_ in logger.messages)
    assert "config file not found" in logger.messages[0][0].lower()


def test_invalid_yaml(tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text("{unbalanced: [1,2")  # niepoprawny YAML
    logger = DummyLogger()
    with pytest.raises(ValueError):
        load_peripheral_configuration(yaml_file=str(p), logger=logger)
    assert any("Failed to parse YAML" in msg for msg, *_ in logger.messages)


def test_empty_file_returns_empty_and_warns(tmp_path):
    p = tmp_path / "empty.yaml"
    p.write_text("")  # pusty
    logger = DummyLogger()
    result = load_peripheral_configuration(yaml_file=str(p), logger=logger)
    assert result == {"peripherals": [], "protocols": []}
    assert any("[WARNING]" in msg and "empty" in msg.lower() for msg, *_ in logger.messages)


def test_top_level_not_dict(tmp_path):
    p = tmp_path / "scalar.yaml"
    p.write_text('"just a string"')
    logger = DummyLogger()
    with pytest.raises(ValueError):
        load_peripheral_configuration(yaml_file=str(p), logger=logger)
    assert any("must be a dictionary" in msg for msg, *_ in logger.messages)


def test_minimal_empty_config(tmp_path):
    path = write_yaml(tmp_path, {})
    result = load_peripheral_configuration(yaml_file=path)
    assert result == {"peripherals": [], "protocols": []}


def test_modbus_valid_and_invalid(tmp_path):
    data_valid = {"protocols": {"modbus": {"port": "/dev/ttyX", "baudrate": 12345}}}
    path = write_yaml(tmp_path, data_valid)
    res = load_peripheral_configuration(yaml_file=path)
    assert len(res["protocols"]) == 1
    assert isinstance(res["protocols"][0], ModbusRTU)

    # nie-dict -> warning, ale nie błąd
    data_bad = {"protocols": {"modbus": ["oops"]}}
    path = write_yaml(tmp_path, data_bad)
    logger = DummyLogger()
    res2 = load_peripheral_configuration(yaml_file=path, logger=logger)
    assert res2["protocols"] == []
    assert any("Invalid configuration for Modbus" in msg for msg, *_ in logger.messages)


def test_uart_valid_and_invalid(tmp_path):
    cfg = {"peripherals": {"uart": {"port": "/dev/ttyY", "baudrate": 4800, "parity": "E", "stopbits": 2}}}
    path = write_yaml(tmp_path, cfg)
    res = load_peripheral_configuration(yaml_file=path)
    assert isinstance(res["peripherals"][0], RPiUART)
    # sprawdzamy mapowanie parzystości i zatrzymania
    uart = res["peripherals"][0]
    assert uart.baudrate == 4800
    assert uart.parity == serial.PARITY_EVEN
    assert uart.stopbits == serial.STOPBITS_TWO

    # nie-dict
    bad = {"peripherals": {"uart": ["bad"]}}
    path = write_yaml(tmp_path, bad)
    logger = DummyLogger()
    res2 = load_peripheral_configuration(yaml_file=path, logger=logger)
    assert res2["peripherals"] == []
    assert any("Invalid configuration for UART" in msg for msg, *_ in logger.messages)


def test_gpio_various_errors_and_success(tmp_path):
    # poprawna
    cfg = {"peripherals": {"gpio": [{"pin": 17, "mode": "out", "initial": "high"}]}}
    path = write_yaml(tmp_path, cfg)
    res = load_peripheral_configuration(yaml_file=path)
    assert isinstance(res["peripherals"][0], RPiGPIO)

    # format nie jest listą dict
    badformat = {"peripherals": {"gpio": ["nope"]}}
    path = write_yaml(tmp_path, badformat)
    logger = DummyLogger()
    res2 = load_peripheral_configuration(yaml_file=path, logger=logger)
    assert res2["peripherals"] == []
    assert any("Invalid GPIO configuration format" in msg for msg, *_ in logger.messages)

    # pin nie int
    badpin = {"peripherals": {"gpio": [{"pin": "foo", "mode": "in"}]}}
    path = write_yaml(tmp_path, badpin)
    logger = DummyLogger()
    res3 = load_peripheral_configuration(yaml_file=path, logger=logger)
    assert res3["peripherals"] == []
    assert any("Invalid GPIO config" in msg for msg, *_ in logger.messages)

    # nieprawidłowy mode
    badmode = {"peripherals": {"gpio": [{"pin": 1, "mode": "XXX", "initial": "low"}]}}
    path = write_yaml(tmp_path, badmode)
    logger = DummyLogger()
    res4 = load_peripheral_configuration(yaml_file=path, logger=logger)
    assert res4["peripherals"] == []
    assert any("Invalid GPIO mode" in msg for msg, *_ in logger.messages)

    # nieprawidłowy initial
    badinit = {"peripherals": {"gpio": [{"pin": 1, "mode": "in", "initial": "???"}]}}
    path = write_yaml(tmp_path, badinit)
    logger = DummyLogger()
    res5 = load_peripheral_configuration(yaml_file=path, logger=logger)
    assert res5["peripherals"] == []
    assert any("Invalid GPIO initial value" in msg for msg, *_ in logger.messages)


def test_pwm_sections(tmp_path):
    # poprawny
    cfg = {"peripherals": {"pwm": [{"pin": 5, "frequency": 2000}]}}
    path = write_yaml(tmp_path, cfg)
    res = load_peripheral_configuration(yaml_file=path)
    assert isinstance(res["peripherals"][0], RPiPWM)

    # format nie jest dict
    badfmt = {"peripherals": {"pwm": ["nope"]}}
    path = write_yaml(tmp_path, badfmt)
    logger = DummyLogger()
    res2 = load_peripheral_configuration(yaml_file=path, logger=logger)
    assert res2["peripherals"] == []
    assert any("Invalid PWM configuration format" in msg for msg, *_ in logger.messages)

    # brak klucza pin
    badcfg = {"peripherals": {"pwm": [{"frequency": 1000}]}}
    path = write_yaml(tmp_path, badcfg)
    logger = DummyLogger()
    res3 = load_peripheral_configuration(yaml_file=path, logger=logger)
    assert res3["peripherals"] == []
    assert any("Invalid PWM configuration" in msg for msg, *_ in logger.messages)


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


# def test_can_adc_hwpwm_sections(tmp_path):
#     cfg = {
#         "peripherals": {
#             "can": {"interface": "can0", "bitrate": 250000},
#             "adc": {"channel": 3},
#             "hardware_pwm": [{"pin": 12, "frequency": 500}],
#         }
#     }
#     path = write_yaml(tmp_path, cfg)
#     res = load_peripheral_configuration(yaml_file=path)
#     # CAN
#     assert any(isinstance(p, RPiCAN) for p in res["peripherals"])
#     # ADC
#     assert any(isinstance(p, RPiADC) for p in res["peripherals"])
#     # hardware PWM
#     assert any(isinstance(p, RPiHardwarePWM) for p in res["peripherals"])

#     # invalid formats
#     bad = {
#         "peripherals": {
#             "can": ["nope"],
#             "adc": ["x"],
#             "hardware_pwm": ["nope"]
#         }
#     }
#     path = write_yaml(tmp_path, bad)
#     logger = DummyLogger()
#     res2 = load_peripheral_configuration(yaml_file=path, logger=logger)
#     assert all(not isinstance(p, (RPiCAN, RPiADC, RPiHardwarePWM)) for p in res2["peripherals"])
#     # trzy ostrzeżenia
#     assert sum(1 for msg, *_ in logger.messages if "expected dictionary" in msg.lower()) == 3
