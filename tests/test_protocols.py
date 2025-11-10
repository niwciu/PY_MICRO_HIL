import pytest
from unittest.mock import patch, MagicMock
from py_micro_hil.peripherals.modbus import ModbusRTU

@pytest.fixture
def modbus_rtu():
    return ModbusRTU(port="/dev/ttyUSB1", baudrate=9600, stopbits=2, parity='E', timeout=2)

def test_initialization_and_release():
    modbus = ModbusRTU()
    with patch("py_micro_hil.protocols.ModbusClient") as mock_client:
        instance = mock_client.return_value
        instance.connect.return_value = True
        modbus.initialize()
        assert modbus.client is not None
        assert modbus.client.connect.called
        instance.connected = True
        modbus.release()
        assert modbus.client.close.called

def test_initialize_connection_failure():
    modbus = ModbusRTU()
    with patch("py_micro_hil.protocols.ModbusClient") as mock_client:
        instance = mock_client.return_value
        instance.connect.return_value = False
        with pytest.raises(ConnectionError):
            modbus.initialize()

def test_release_when_not_connected():
    modbus = ModbusRTU()
    mock_client = MagicMock()
    mock_client.connected = False
    modbus.client = mock_client
    modbus.release()
    mock_client.close.assert_not_called()

def test_get_initialized_params():
    modbus = ModbusRTU(port="/dev/ttyUSB1", baudrate=19200, stopbits=1, parity='O', timeout=5)
    expected = {
        "port": "/dev/ttyUSB1",
        "baudrate": 19200,
        "stopbits": 1,
        "parity": 'O',
        "timeout": 5
    }
    assert modbus.get_initialized_params() == expected

def test_get_required_resources():
    modbus = ModbusRTU(port="/dev/ttyUSB3")
    assert modbus.get_required_resources() == {"ports": ["/dev/ttyUSB3"]}

@pytest.mark.parametrize("method_name,response_attr,response_value,args", [
    ("read_holding_registers", "registers", [1, 2, 3], (1, 100, 3)),
    ("write_single_register", None, None, (1, 100, 123)),
    ("write_multiple_registers", None, None, (1, 100, [1, 2])),
    ("read_coils", "bits", [True, False], (1, 100, 2)),
    ("read_discrete_inputs", "bits", [False, True], (1, 100, 2)),
    ("read_input_registers", "registers", [10, 20], (1, 100, 2)),
    ("write_single_coil", None, None, (1, 100, True)),
    ("write_multiple_coils", None, None, (1, 100, [True, False])),
])
@patch("py_micro_hil.protocols.ModbusClient")
def test_modbus_methods_success(mock_client_class, method_name, response_attr, response_value, args, modbus_rtu):
    mock_response = MagicMock()
    mock_response.isError.return_value = False
    if response_attr:
        setattr(mock_response, response_attr, response_value)

    client_method_map = {
        "read_holding_registers": "read_holding_registers",
        "write_single_register": "write_register",
        "write_multiple_registers": "write_registers",
        "read_coils": "read_coils",
        "read_discrete_inputs": "read_discrete_inputs",
        "read_input_registers": "read_input_registers",
        "write_single_coil": "write_coil",
        "write_multiple_coils": "write_coils"
    }

    client_method_name = client_method_map[method_name]
    mock_client = MagicMock()
    setattr(mock_client, client_method_name, MagicMock(return_value=mock_response))
    modbus_rtu.client = mock_client

    method = getattr(modbus_rtu, method_name)
    result = method(*args)

    if response_attr:
        assert result == response_value
    else:
        assert result == mock_response

@pytest.mark.parametrize("method_name,args", [
    ("read_holding_registers", (1, 100, 2)),
    ("write_single_register", (1, 100, 123)),
    ("write_multiple_registers", (1, 100, [1, 2])),
    ("read_coils", (1, 100, 2)),
    ("read_discrete_inputs", (1, 100, 2)),
    ("read_input_registers", (1, 100, 2)),
    ("write_single_coil", (1, 100, True)),
    ("write_multiple_coils", (1, 100, [True, False])),
])
def test_method_runtime_error_when_not_initialized(method_name, args, modbus_rtu):
    method = getattr(modbus_rtu, method_name)
    with pytest.raises(RuntimeError):
        method(*args)

@pytest.mark.parametrize("method_name,args", [
    ("read_holding_registers", (1, 100, 2)),
    ("write_single_register", (1, 100, 123)),
    ("write_multiple_registers", (1, 100, [1, 2])),
    ("read_coils", (1, 100, 2)),
    ("read_discrete_inputs", (1, 100, 2)),
    ("read_input_registers", (1, 100, 2)),
    ("write_single_coil", (1, 100, True)),
    ("write_multiple_coils", (1, 100, [True, False])),
])
def test_method_ioerror_on_error_response(method_name, args, modbus_rtu):
    mock_response = MagicMock()
    mock_response.isError.return_value = True

    client_method_map = {
        "read_holding_registers": "read_holding_registers",
        "write_single_register": "write_register",
        "write_multiple_registers": "write_registers",
        "read_coils": "read_coils",
        "read_discrete_inputs": "read_discrete_inputs",
        "read_input_registers": "read_input_registers",
        "write_single_coil": "write_coil",
        "write_multiple_coils": "write_coils"
    }

    client_method_name = client_method_map[method_name]
    mock_client = MagicMock()
    setattr(mock_client, client_method_name, MagicMock(return_value=mock_response))
    modbus_rtu.client = mock_client

    method = getattr(modbus_rtu, method_name)
    with pytest.raises(IOError):
        method(*args)
