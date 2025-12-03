import pytest
from unittest.mock import mock_open, MagicMock
import subprocess
import glob

# import RPi.GPIO as GPIO
import spidev
import serial
import can
from smbus2 import SMBus
import py_micro_hil.peripherals.RPiPeripherals as rpi_peripherals

from py_micro_hil.peripherals.RPiPeripherals import (
    RPiGPIO,
    RPiPWM,
    RPiUART,
    RPiI2C,
    RPiSPI,
    RPiHardwarePWM,
    RPiOneWire,
)

# --- Fix for python-can compatibility ---
import types

GPIO = RPiGPIO.get_gpio_interface()

# Niektóre wersje python-can nie mają podmodułu 'can.interface'
if not hasattr(can, "interface"):
    can.interface = types.SimpleNamespace()

# Upewniamy się, że można podmieniać Bus (testy to robią przez monkeypatch)
if not hasattr(can.interface, "Bus"):
    can.interface.Bus = lambda *args, **kwargs: None
# --- end of compatibility fix ---


# ==== Fixtures for mocks ====
@pytest.fixture(autouse=True)
def no_hardware(monkeypatch):
    # Mock GPIO
    monkeypatch.setattr(GPIO, "setmode", lambda *args, **kw: None)
    monkeypatch.setattr(GPIO, "setup", lambda *args, **kw: None)
    monkeypatch.setattr(GPIO, "output", lambda *args, **kw: None)
    monkeypatch.setattr(GPIO, "input", lambda pin: 0)
    monkeypatch.setattr(GPIO, "cleanup", lambda *args, **kw: None)

    # Stub out PWM to avoid real RPi.GPIO.PWM calls
    class DummyPWM:
        def __init__(self, pin, freq):
            pass

        def start(self, dc):
            pass

        def ChangeDutyCycle(self, dc):
            pass

        def ChangeFrequency(self, f):
            pass

        def stop(self):
            pass

    monkeypatch.setattr(GPIO, "PWM", lambda pin, freq: DummyPWM(pin, freq))

    # Mock spidev
    fake_spi = MagicMock()
    fake_spi.xfer.side_effect = lambda data: list(reversed(data))
    fake_spi.xfer2.side_effect = lambda data: data
    fake_spi.readbytes.return_value = [0, 0]
    monkeypatch.setattr(spidev, "SpiDev", lambda: fake_spi)

    # Mock serial
    fake_serial = MagicMock()
    fake_serial.readline.return_value = b"ok\n"
    fake_serial.read.return_value = b"x"
    monkeypatch.setattr(serial, "Serial", lambda *args, **kw: fake_serial)

    # Mock SMBus
    class FakeBus:
        def write_quick(self, addr):
            if addr == 0x09:
                raise IOError

        def read_i2c_block_data(self, addr, reg, length):
            return [1] * length

        def write_i2c_block_data(self, addr, reg, data):
            pass

        def read_byte(self, addr):
            return 0

        def write_byte(self, addr, val):
            pass

        def read_word_data(self, addr, reg):
            return 0xABCD

        def write_word_data(self, addr, reg, val):
            pass

        def close(self):
            pass

    monkeypatch.setattr(SMBus, "__init__", lambda self, bus: None)
    monkeypatch.setattr(SMBus, "write_quick", FakeBus.write_quick)
    monkeypatch.setattr(SMBus, "read_i2c_block_data", FakeBus.read_i2c_block_data)
    monkeypatch.setattr(SMBus, "write_i2c_block_data", FakeBus.write_i2c_block_data)
    monkeypatch.setattr(SMBus, "read_byte", FakeBus.read_byte)
    monkeypatch.setattr(SMBus, "write_byte", FakeBus.write_byte)
    monkeypatch.setattr(SMBus, "read_word_data", FakeBus.read_word_data)
    monkeypatch.setattr(SMBus, "write_word_data", FakeBus.write_word_data)
    monkeypatch.setattr(SMBus, "close", FakeBus.close)

    # Mock CAN
    fake_bus = MagicMock()
    monkeypatch.setattr(can.interface, "Bus", lambda *args, **kw: fake_bus)
    fake_bus.recv.return_value = MagicMock()

    # Mock subprocess and glob for 1-Wire
    monkeypatch.setattr(
        glob, "glob", lambda pattern: ["/sys/bus/w1/devices/28-0001"] if "28*" in pattern else []
    )
    monkeypatch.setattr(subprocess, "run", lambda *args, **kw: None)


# ==== GPIO Tests ====


def test_gpio_interface_accessible_from_instance():
    gpio = RPiGPIO({})

    assert gpio.get_gpio_interface() is GPIO


def test_gpio_write_read_toggle():
    config = {5: {"mode": GPIO.OUT, "initial": GPIO.LOW, "name": "PUSHBUTTON"}}
    gpio = RPiGPIO(config)
    gpio.initialize()
    gpio.write("PUSHBUTTON", "HIGH")
    assert gpio.read("pushbutton") == 0  # mocked input returns 0
    gpio.toggle("PUSHBUTTON")


def test_gpio_value_normalization_and_name_errors():
    gpio = RPiGPIO({7: {"mode": GPIO.OUT, "initial": GPIO.LOW, "name": "LED"}})
    gpio.initialize()

    gpio.write("led", "low")
    gpio.write(7, 1)

    with pytest.raises(ValueError):
        gpio.write("UNKNOWN", 1)

    with pytest.raises(ValueError):
        gpio.write(7, "INVALID")


def test_gpio_required_resources():
    gpio = RPiGPIO({4: {"mode": GPIO.OUT, "initial": GPIO.LOW}})
    assert gpio.get_required_resources() == {"pins": [4]}


def test_gpio_label_constants_and_combined_config():
    config = {
        23: {"mode": GPIO.OUT, "initial": GPIO.HIGH, "name": "PUSHBUTTON"},
        22: {"mode": GPIO.OUT, "initial": GPIO.LOW, "name": "RST"},
        24: {"mode": GPIO.IN, "initial": GPIO.LOW, "name": "LED"},
    }

    gpio = RPiGPIO(config)
    gpio.initialize()

    assert getattr(rpi_peripherals, "PUSHBUTTON") == "PUSHBUTTON"
    assert getattr(rpi_peripherals, "RST") == "RST"
    assert getattr(rpi_peripherals, "high") == "HIGH"
    assert getattr(rpi_peripherals, "low") == "LOW"

    gpio.write(rpi_peripherals.RST, rpi_peripherals.low)
    gpio.write("LED", rpi_peripherals.HIGH)
    gpio.write(rpi_peripherals.PUSHBUTTON, "high")


# ==== PWM Tests ====


def test_pwm_invalid_duty_cycle():
    pwm = RPiPWM(6)
    pwm.initialize()
    with pytest.raises(ValueError):
        pwm.set_duty_cycle(200)


def test_pwm_invalid_frequency():
    pwm = RPiPWM(6)
    pwm.initialize()
    with pytest.raises(ValueError):
        pwm.set_frequency(0)


def test_pwm_edge_duty_cycle():
    pwm = RPiPWM(6)
    pwm.initialize()
    for duty in (-10, 150):
        with pytest.raises(ValueError):
            pwm.set_duty_cycle(duty)


def test_pwm_edge_frequency():
    pwm = RPiPWM(6)
    pwm.initialize()
    for freq in (0, -100):
        with pytest.raises(ValueError):
            pwm.set_frequency(freq)


def test_pwm_required_resources():
    pwm = RPiPWM(12)
    assert pwm.get_required_resources() == {"pins": [12]}


# ==== UART Tests ====


def test_uart_send_receive_readline():
    uart = RPiUART()
    uart.initialize()
    uart.send("hello")
    assert uart.receive(1) == b"x"
    assert uart.readline() == b"ok\n"


def test_uart_required_resources():
    uart = RPiUART(port="/dev/ttyS0")
    assert uart.get_required_resources() == {"pins": [14, 15], "ports": ["/dev/ttyS0"]}


# ==== I2C Tests ====


def test_i2c_scan_and_rw():
    i2c = RPiI2C(bus_number=1)
    i2c.initialize()
    devices = i2c.scan()
    assert isinstance(devices, list)
    assert 0x09 not in devices  # edge case
    assert i2c.read(0x10, 0x01, 4) == [1, 1, 1, 1]
    i2c.write(0x10, 0x01, [2, 3])
    assert i2c.read_byte(0x10) == 0
    assert i2c.read_word(0x10, 0x01) == 0xABCD


def test_i2c_required_resources():
    i2c0 = RPiI2C(bus_number=0)
    assert i2c0.get_required_resources() == {"pins": [0, 1], "ports": ["/dev/i2c-0"]}
    i2c1 = RPiI2C(bus_number=1)
    assert i2c1.get_required_resources() == {"pins": [2, 3], "ports": ["/dev/i2c-1"]}


def test_i2c_invalid_bus():
    # invalid/unsupported bus is treated as USB/virtual adapter
    i2c = RPiI2C(bus_number=2)
    assert i2c.get_required_resources() == {"ports": ["/dev/i2c-2"]}


# ==== SPI Tests ====


def test_spi_transfer():
    spi = RPiSPI(bus=0, device=0)
    spi.initialize()
    assert spi.transfer([1, 2, 3]) == [3, 2, 1]
    assert spi.transfer2([4, 5]) == [4, 5]
    assert spi.transfer_bytes(b"ab") == b"ba"
    spi.write_bytes([9, 8])
    assert isinstance(spi.read_bytes(2), list)


def test_spi_required_resources():
    spi = RPiSPI(bus=1, device=2)

    expected = {
        "pins": [
            20,  # MOSI1
            19,  # MISO1
            21,  # SCLK1
            16,  # CE2
        ],
        "ports": ["/dev/spidev1.2"],
    }

    assert spi.get_required_resources() == expected


# ==== Hardware PWM Tests ====


def test_hardware_pwm():
    hw = RPiHardwarePWM(pin=18)
    hw.initialize()
    hw.set_duty_cycle(50)
    hw.set_frequency(2000)
    hw.release()


def test_hardware_pwm_required_resources():
    hw = RPiHardwarePWM(pin=18)
    assert hw.get_required_resources() == {"pins": [18]}


# ============================================================
# 1-WIRE TESTS (NEW)
# ============================================================


def test_onewire_init_and_scan(monkeypatch):
    # Mock glob.glob to return 2 fake sensors
    monkeypatch.setattr(
        glob,
        "glob",
        lambda pattern: (
            [
                "/sys/bus/w1/devices/28-000111111111",
                "/sys/bus/w1/devices/28-000222222222",
            ]
            if "28-" in pattern
            else []
        ),
    )

    onewire = RPiOneWire(pin=4)
    onewire.initialize()

    devs = onewire.scan_devices()
    assert devs == ["28-000111111111", "28-000222222222"]


def test_onewire_no_devices(monkeypatch):
    monkeypatch.setattr(glob, "glob", lambda pattern: [])

    onewire = RPiOneWire(pin=4)
    onewire.initialize()

    devs = onewire.scan_devices()
    assert devs == []


def test_onewire_read_temperature(monkeypatch):
    # 1-wire device directory exists
    monkeypatch.setattr(
        glob, "glob", lambda pattern: ["/sys/bus/w1/devices/28-0001"] if "28-" in pattern else []
    )

    # Mock file read of w1_slave
    file_content = (
        "aa bb cc dd ee ff gg hh ii\n"
        "t=21562\n"  # 21.562°C
    )

    m = mock_open(read_data=file_content)
    monkeypatch.setattr("builtins.open", m)

    onewire = RPiOneWire(pin=4)
    onewire.initialize()

    temp = onewire.read_temperature("28-0001")
    assert temp == 21.562


def test_onewire_required_resources():
    ow = RPiOneWire(pin=4)
    assert ow.get_required_resources() == {"pins": [4]}
