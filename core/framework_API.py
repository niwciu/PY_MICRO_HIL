from core.assertions import _current_framework
from core.RPiPeripherals import RPiUART_API
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
