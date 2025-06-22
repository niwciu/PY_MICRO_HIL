from py_micro_hil.assertions import _current_framework
from py_micro_hil.RPiPeripherals import (
    RPiUART_API, RPiGPIO_API, RPiPWM_API, RPiI2C_API,
    RPiSPI_API, RPiHardwarePWM_API
)
from py_micro_hil.protocols import ModbusRTU_API


def _get_framework():
    """
    Retrieves the current framework context from _current_framework.
    :return: The current test framework context instance.
    :raises RuntimeError: If the framework context has not been set.
    """
    framework = _current_framework.get()
    if not framework:
        raise RuntimeError("No framework context is set for this test")
    return framework


def get_ModBus_peripheral() -> ModbusRTU_API:
    """
    Retrieves an instance of the ModbusRTU peripheral from the framework.
    :return: Instance implementing ModbusRTU_API.
    """
    framework = _get_framework()
    return framework.peripheral_manager.get_device("protocols", "ModbusRTU")


def get_RPiUART_peripheral() -> RPiUART_API:
    """
    Retrieves an instance of the UART peripheral configured for Raspberry Pi.
    :return: Instance implementing RPiUART_API.
    """
    framework = _get_framework()
    return framework.peripheral_manager.get_device("peripherals", "RPiUART")


def get_RPiGPIO_peripheral() -> RPiGPIO_API:
    """
    Retrieves an instance of the GPIO peripheral configured for Raspberry Pi.
    :return: Instance implementing RPiGPIO_API.
    """
    framework = _get_framework()
    return framework.peripheral_manager.get_device("peripherals", "RPiGPIO")


def get_RPiPWM_peripheral() -> RPiPWM_API:
    """
    Retrieves an instance of the software PWM peripheral configured for Raspberry Pi.
    :return: Instance implementing RPiPWM_API.
    """
    framework = _get_framework()
    return framework.peripheral_manager.get_device("peripherals", "RPiPWM")


def get_RPiI2C_peripheral() -> RPiI2C_API:
    """
    Retrieves an instance of the I2C peripheral configured for Raspberry Pi.
    :return: Instance implementing RPiI2C_API.
    """
    framework = _get_framework()
    return framework.peripheral_manager.get_device("peripherals", "RPiI2C")


def get_RPiSPI_peripheral() -> RPiSPI_API:
    """
    Retrieves an instance of the SPI peripheral configured for Raspberry Pi.
    :return: Instance implementing RPiSPI_API.
    """
    framework = _get_framework()
    return framework.peripheral_manager.get_device("peripherals", "RPiSPI")


def get_RPiHardwarePWM_peripheral() -> RPiHardwarePWM_API:
    """
    Retrieves an instance of the hardware PWM peripheral configured for Raspberry Pi.
    :return: Instance implementing RPiHardwarePWM_API.
    """
    framework = _get_framework()
    return framework.peripheral_manager.get_device("peripherals", "RPiHardwarePWM")
