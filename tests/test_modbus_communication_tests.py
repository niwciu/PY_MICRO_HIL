from core.assertions import *
from core.framework_API import *

def test_modbus_read_test():
    try:
        # Pobranie zasobu ModbusTRU z menedżera
        ModBUS = get_ModBus_peripheral()
        UART = get_RPiUART_peripheral()

        # Korzystanie z zasobu
        registers = ModBUS.read_holding_registers(slave_address=0x01, address=0x00, count=1)
        # Sprawdzenie wartości
        TEST_ASSERT_EQUAL(0x5A5A, registers[0])
    except Exception as e:
        TEST_FAIL_MESSAGE(str(e))