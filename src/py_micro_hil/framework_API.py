from typing import TYPE_CHECKING
from py_micro_hil.assertions import _current_framework

if TYPE_CHECKING:
    from py_micro_hil.peripherals.RPiPeripherals import (
        RPiUART_API,
        RPiGPIO_API,
        RPiPWM_API,
        RPiI2C_API,
        RPiSPI_API,
        RPiHardwarePWM_API,
        RPiOneWire_API,  # ← DODANE
    )
    from py_micro_hil.peripherals.modbus import ModbusRTU_API


def _get_framework():
    """Retrieve the current framework context.

    :raises RuntimeError: If no framework context has been set.
    """
    framework = _current_framework.get()
    if not framework:
        raise RuntimeError(
            "No framework context is set (did you forget to call set_test_context()?)"
        )
    return framework


def get_ModBus_peripheral() -> "ModbusRTU_API":
    """Return an instance of the ModbusRTU peripheral."""
    return _get_framework().peripheral_manager.get_device("protocols", "ModbusRTU")


def get_RPiUART_peripheral() -> "RPiUART_API":
    """Return an instance of the UART peripheral configured for Raspberry Pi."""
    return _get_framework().peripheral_manager.get_device("peripherals", "RPiUART")


def get_RPiGPIO_peripheral() -> "RPiGPIO_API":
    """Return an instance of the GPIO peripheral configured for Raspberry Pi."""
    return _get_framework().peripheral_manager.get_device("peripherals", "RPiGPIO")


def get_RPiPWM_peripheral() -> "RPiPWM_API":
    """Return an instance of the software PWM peripheral configured for Raspberry Pi."""
    return _get_framework().peripheral_manager.get_device("peripherals", "RPiPWM")


def get_RPiI2C_peripheral() -> "RPiI2C_API":
    """Return an instance of the I2C peripheral configured for Raspberry Pi."""
    return _get_framework().peripheral_manager.get_device("peripherals", "RPiI2C")


def get_RPiSPI_peripheral() -> "RPiSPI_API":
    """Return an instance of the SPI peripheral configured for Raspberry Pi."""
    return _get_framework().peripheral_manager.get_device("peripherals", "RPiSPI")


def get_RPiHardwarePWM_peripheral() -> "RPiHardwarePWM_API":
    """Return an instance of the hardware PWM peripheral configured for Raspberry Pi."""
    return _get_framework().peripheral_manager.get_device("peripherals", "RPiHardwarePWM")


def get_RPiOneWire_peripheral() -> "RPiOneWire_API":
    """Return an instance of the 1-Wire peripheral configured for Raspberry Pi."""
    return _get_framework().peripheral_manager.get_device("peripherals", "RPiOneWire")
