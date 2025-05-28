from core.assertions import _current_framework
from core.RPiPeripherals import RPiUART_API , RPiGPIO_API, RPiPWM_API, RPiI2C_API, RPiSPI_API, RPi1Wire_API, RPiADC_API, RPiCAN_API, RPiHardwarePWM_API
from core.protocols import ModbusRTU_API
def _get_framework():
    framework = _current_framework.get()
    if not framework:
        raise RuntimeError("No framework context is set for this test")
    return framework

def get_ModBus_peripheral() -> ModbusRTU_API:
    framework = _get_framework()
    return framework.peripheral_manager.get_device("protocols", "ModbusRTU")

def get_RPiUART_peripheral() -> RPiUART_API:
    framework = _get_framework()
    return framework.peripheral_manager.get_device("peripherals", "RPiUART")

def get_RPiGPIO_peripheral() -> RPiGPIO_API:
    framework = _get_framework()
    return framework.peripheral_manager.get_device("peripherals", "RPiGPIO")

def get_RPiPWM_peripheral() -> RPiPWM_API:
    framework = _get_framework()
    return framework.peripheral_manager.get_device("peripherals", "RPiPWM")

def get_RPiI2C_peripheral() -> RPiI2C_API:
    framework = _get_framework()
    return framework.peripheral_manager.get_device("peripherals", "RPiI2C")

def get_RPiPWM_peripheral() -> RPiPWM_API:
    framework = _get_framework()
    return framework.peripheral_manager.get_device("peripherals", "RPiPWM")

def get_RPiPWM_peripheral() -> RPiSPI_API:
    framework = _get_framework()
    return framework.peripheral_manager.get_device("peripherals", "RPiSPI")

def get_RPiCAN_peripheral() -> RPiCAN_API:
    framework = _get_framework()
    return framework.peripheral_manager.get_device("peripherals", "RPiCAN")

def get_RPiADC_peripheral() -> RPiADC_API:
    framework = _get_framework()
    return framework.peripheral_manager.get_device("peripherals", "RPiADC")

def get_RPi1Wire_peripheral() -> RPi1Wire_API:
    framework = _get_framework()
    return framework.peripheral_manager.get_device("peripherals", "RPi1Wire")

def get_RPiHardwarePWM_peripheral() -> RPiHardwarePWM_API:
    framework = _get_framework()
    return framework.peripheral_manager.get_device("peripherals", "RPiHardwarePWM")