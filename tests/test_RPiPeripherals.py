import pytest
from unittest.mock import mock_open, MagicMock, patch
import logging
import os
import glob
import subprocess

import RPi.GPIO as GPIO
import spidev
import serial
import can
from smbus2 import SMBus

from py_micro_hil.RPiPeripherals import (
    RPiGPIO, RPiPWM, RPiUART, RPiI2C, RPiSPI,
    RPi1Wire, RPiADC, RPiCAN, RPiHardwarePWM
)

# ==== Fixtures for mocks ==== 
@pytest.fixture(autouse=True)
def no_hardware(monkeypatch):
    # Mock GPIO
    monkeypatch.setattr(GPIO, 'setmode', lambda *args, **kw: None)
    monkeypatch.setattr(GPIO, 'setup', lambda *args, **kw: None)
    monkeypatch.setattr(GPIO, 'output', lambda *args, **kw: None)
    monkeypatch.setattr(GPIO, 'input', lambda pin: 0)
    monkeypatch.setattr(GPIO, 'cleanup', lambda *args, **kw: None)
    # Stub out software/hardware PWM to avoid real RPi.GPIO.PWM calls
    class DummyPWM:
        def __init__(self, pin, freq): pass
        def start(self, dc): pass
        def ChangeDutyCycle(self, dc): pass
        def ChangeFrequency(self, f): pass
        def stop(self): pass
    monkeypatch.setattr(GPIO, 'PWM', lambda pin, freq: DummyPWM(pin, freq))
    
    # Mock spidev
    fake_spi = MagicMock()
    fake_spi.xfer.side_effect = lambda data: list(reversed(data))
    fake_spi.xfer2.side_effect = lambda data: data
    fake_spi.readbytes.return_value = [0, 0]
    monkeypatch.setattr(spidev, 'SpiDev', lambda: fake_spi)
    
    # Mock serial
    fake_serial = MagicMock()
    fake_serial.readline.return_value = b"ok\n"
    fake_serial.read.return_value = b"x"
    monkeypatch.setattr(serial, 'Serial', lambda *args, **kw: fake_serial)
    
    # Mock SMBus
    class FakeBus:
        def __init__(self, bus): pass
        def write_quick(self, addr):
            if addr == 0x09:
                raise IOError
        def read_i2c_block_data(self, addr, reg, length):
            return [1]*length
        def write_i2c_block_data(self, addr, reg, data): pass
        def read_byte(self, addr): return 0
        def write_byte(self, addr, val): pass
        def read_word_data(self, addr, reg): return 0xABCD
        def write_word_data(self, addr, reg, val): pass
        def close(self): pass
    monkeypatch.setattr(SMBus, '__init__', lambda self, bus: None)
    monkeypatch.setattr(SMBus, 'write_quick', FakeBus.write_quick)
    monkeypatch.setattr(SMBus, 'read_i2c_block_data', FakeBus.read_i2c_block_data)
    monkeypatch.setattr(SMBus, 'write_i2c_block_data', FakeBus.write_i2c_block_data)
    monkeypatch.setattr(SMBus, 'read_byte', FakeBus.read_byte)
    monkeypatch.setattr(SMBus, 'write_byte', FakeBus.write_byte)
    monkeypatch.setattr(SMBus, 'read_word_data', FakeBus.read_word_data)
    monkeypatch.setattr(SMBus, 'write_word_data', FakeBus.write_word_data)
    monkeypatch.setattr(SMBus, 'close', FakeBus.close)
    
    # Mock CAN
    fake_bus = MagicMock()
    monkeypatch.setattr(can.interface, 'Bus', lambda *args, **kw: fake_bus)
    fake_bus.recv.return_value = MagicMock()
    
    # Mock subprocess and glob for 1-Wire
    monkeypatch.setattr(glob, 'glob', lambda pattern: ['/sys/bus/w1/devices/28-0001'] if '28*' in pattern else [])
    monkeypatch.setattr(subprocess, 'run', lambda *args, **kw: None)

# ==== GPIO Tests ==== 

def test_gpio_write_read_toggle():
    config = {5: {'mode': GPIO.OUT, 'initial': GPIO.LOW}}
    gpio = RPiGPIO(config)
    gpio.initialize()
    gpio.write(5, GPIO.HIGH)
    assert gpio.read(5) == 0  # mocked input returns 0
    gpio.toggle(5)

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

# ==== UART Tests ====

def test_uart_send_receive_readline():
    uart = RPiUART()
    uart.initialize()
    uart.send("hello")
    assert uart.receive(1) == b"x"
    assert uart.readline() == b"ok\n"

# ==== I2C Tests ====

def test_i2c_scan_and_rw():
    i2c = RPiI2C(bus_number=1)
    i2c.initialize()
    devices = i2c.scan()
    assert isinstance(devices, list)
    data = i2c.read(0x10, 0x01, 4)
    assert data == [1,1,1,1]
    i2c.write(0x10, 0x01, [2,3])
    assert i2c.read_byte(0x10) == 0
    assert i2c.read_word(0x10,0x01) == 0xABCD

# ==== SPI Tests ====

def test_spi_transfer():
    spi = RPiSPI(bus=0, device=0)
    spi.initialize()
    assert spi.transfer([1,2,3]) == [3,2,1]
    assert spi.transfer2([4,5]) == [4,5]
    assert spi.transfer_bytes(b"ab") == b"ba"
    spi.write_bytes([9,8])
    assert isinstance(spi.read_bytes(2), list)

# ==== 1-Wire Tests ====

def test_1wire_temperature_and_list():
    one = RPi1Wire(pin=4)
    one.initialize()
    ids = one.list_devices()
    assert '28-0001' in ids
    # simulate file content
    m = mock_open(read_data="YES\n... t=23000")
    with patch('builtins.open', m):
        temp = one.read_temperature('28-0001')
        assert temp == 23.0

# ==== ADC Tests ====

def test_adc_invalid_channel():
    with pytest.raises(ValueError):
        RPiADC(channel=9)

def test_adc_read_all_and_single():
    adc = RPiADC(channel=0)
    adc.initialize()
    val = adc.read()
    assert isinstance(val, int)
    all_vals = adc.read_all_channels()
    assert len(all_vals) == 8

# ==== CAN Tests ====

def test_can_send_receive():
    canif = RPiCAN(interface='can0')
    canif.initialize()
    canif.send_message(0x123, [1,2,3])
    msg = canif.receive_message()
    assert msg is not None

# ==== Hardware PWM Tests ====

def test_hardware_pwm():
    hw = RPiHardwarePWM(pin=18)
    hw.initialize()
    hw.set_duty_cycle(50)
    hw.set_frequency(2000)
    hw.release()

# ==== Edge Cases ====

def test_i2c_invalid_write_quick_address():
    i2c = RPiI2C(1)
    i2c.initialize()
    devices = i2c.scan()
    assert 0x09 not in devices

@pytest.mark.parametrize("duty", [-10, 150])
def test_pwm_edge_duty_cycle(duty):
    pwm = RPiPWM(6)
    pwm.initialize()
    with pytest.raises(ValueError):
        pwm.set_duty_cycle(duty)

@pytest.mark.parametrize("freq", [0, -100])
def test_pwm_edge_frequency(freq):
    pwm = RPiPWM(6)
    pwm.initialize()
    with pytest.raises(ValueError):
        pwm.set_frequency(freq)

@pytest.mark.parametrize("bus", [2, -1])
def test_i2c_invalid_bus(bus):
    with pytest.raises(ValueError):
        RPiI2C(bus_number=bus)
