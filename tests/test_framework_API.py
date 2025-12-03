import pytest
from py_micro_hil import framework_API
from py_micro_hil.assertions import _current_framework


# ---------------------------------------------------------------------
# Dummy classes
# ---------------------------------------------------------------------


class DummyPeripheralManager:
    def get_device(self, device_type, class_name):
        return f"{device_type}:{class_name}"


class DummyFramework:
    def __init__(self):
        self.peripheral_manager = DummyPeripheralManager()


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------


@pytest.fixture
def set_framework_context():
    _current_framework.set(DummyFramework())
    yield
    _current_framework.set(None)


# ---------------------------------------------------------------------
# Context management
# ---------------------------------------------------------------------


def test_get_framework_raises_if_not_set():
    _current_framework.set(None)
    with pytest.raises(RuntimeError, match="No framework context is set"):
        framework_API._get_framework()


def test_get_framework_returns_instance(set_framework_context):
    fw = framework_API._get_framework()
    assert hasattr(fw, "peripheral_manager")


# ---------------------------------------------------------------------
# Peripheral getters
# ---------------------------------------------------------------------


def test_get_ModBus_peripheral(set_framework_context):
    assert framework_API.get_ModBus_peripheral() == "protocols:ModbusRTU"


def test_get_RPiUART_peripheral(set_framework_context):
    assert framework_API.get_RPiUART_peripheral() == "peripherals:RPiUART"


def test_get_RPiGPIO_peripheral(set_framework_context):
    assert framework_API.get_RPiGPIO_peripheral() == "peripherals:RPiGPIO"


def test_get_RPiPWM_peripheral(set_framework_context):
    assert framework_API.get_RPiPWM_peripheral() == "peripherals:RPiPWM"


def test_get_RPiI2C_peripheral(set_framework_context):
    assert framework_API.get_RPiI2C_peripheral() == "peripherals:RPiI2C"


def test_get_RPiSPI_peripheral(set_framework_context):
    assert framework_API.get_RPiSPI_peripheral() == "peripherals:RPiSPI"


def test_get_RPiHardwarePWM_peripheral(set_framework_context):
    assert framework_API.get_RPiHardwarePWM_peripheral() == "peripherals:RPiHardwarePWM"


def test_get_RPi1Wire_peripheral(set_framework_context):
    assert framework_API.get_RPiOneWire_peripheral() == "peripherals:RPiOneWire"
