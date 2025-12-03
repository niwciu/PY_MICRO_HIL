import pytest
from unittest.mock import patch, MagicMock
from py_micro_hil.peripherals.protocols import ModbusRTU


@pytest.fixture
def modbus_rtu():
    return ModbusRTU(port="/dev/ttyUSB1", baudrate=9600, stopbits=2, parity="E", timeout=2)


# === Initialization / Release ===


def test_initialization_and_release():
    with patch("py_micro_hil.peripherals.protocols.ModbusClient") as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.connect.return_value = True

        modbus = ModbusRTU(port="/dev/ttyUSB0")
        modbus.initialize()

        mock_client_class.assert_called_once_with(
            port="/dev/ttyUSB0", baudrate=115200, stopbits=1, parity="N", timeout=1
        )
        assert modbus.client is mock_client
        assert modbus.client.connect.called

        # simulate connected
        modbus.client.connected = True
        modbus.release()
        modbus.client.close.assert_called_once()


def test_initialize_connection_failure():
    with patch("py_micro_hil.peripherals.protocols.ModbusClient") as mock_client_class:
        mock_instance = mock_client_class.return_value
        mock_instance.connect.return_value = False
        modbus = ModbusRTU()
        with pytest.raises(ConnectionError):
            modbus.initialize()


def test_release_when_not_connected():
    modbus = ModbusRTU()
    modbus.client = MagicMock()
    modbus.client.connected = False
    modbus.release()
    modbus.client.close.assert_not_called()


def test_release_when_client_none():
    modbus = ModbusRTU()
    modbus.client = None
    # should not raise
    modbus.release()


# === Config and resources ===


def test_get_initialized_params():
    modbus = ModbusRTU(port="/dev/ttyUSB5", baudrate=19200, stopbits=1, parity="O", timeout=3)
    assert modbus.get_initialized_params() == {
        "port": "/dev/ttyUSB5",
        "baudrate": 19200,
        "stopbits": 1,
        "parity": "O",
        "timeout": 3,
    }


def test_get_required_resources():
    modbus = ModbusRTU(port="/dev/ttyS10")
    assert modbus.get_required_resources() == {"ports": ["/dev/ttyS10"]}


# === Helper map for methods ===

CLIENT_METHOD_MAP = {
    "read_holding_registers": "read_holding_registers",
    "write_single_register": "write_register",
    "write_multiple_registers": "write_registers",
    "read_coils": "read_coils",
    "read_discrete_inputs": "read_discrete_inputs",
    "read_input_registers": "read_input_registers",
    "write_single_coil": "write_coil",
    "write_multiple_coils": "write_coils",
}


# === Success cases ===


@pytest.mark.parametrize(
    "method_name,response_attr,response_value,args",
    [
        ("read_holding_registers", "registers", [1, 2, 3], (1, 100, 3)),
        ("write_single_register", None, None, (1, 100, 123)),
        ("write_multiple_registers", None, None, (1, 100, [1, 2])),
        ("read_coils", "bits", [True, False], (1, 100, 2)),
        ("read_discrete_inputs", "bits", [False, True], (1, 100, 2)),
        ("read_input_registers", "registers", [10, 20], (1, 100, 2)),
        ("write_single_coil", None, None, (1, 100, True)),
        ("write_multiple_coils", None, None, (1, 100, [True, False])),
    ],
)
def test_modbus_methods_success(method_name, response_attr, response_value, args, modbus_rtu):
    mock_response = MagicMock()
    mock_response.isError.return_value = False
    if response_attr:
        setattr(mock_response, response_attr, response_value)

    client_method_name = CLIENT_METHOD_MAP[method_name]
    mock_client = MagicMock()
    getattr(mock_client, client_method_name).return_value = mock_response
    modbus_rtu.client = mock_client

    result = getattr(modbus_rtu, method_name)(*args)
    if response_attr:
        assert result == response_value
    else:
        assert result == mock_response


# === Error cases ===


@pytest.mark.parametrize(
    "method_name,args",
    [
        ("read_holding_registers", (1, 100, 2)),
        ("write_single_register", (1, 100, 123)),
        ("write_multiple_registers", (1, 100, [1, 2])),
        ("read_coils", (1, 100, 2)),
        ("read_discrete_inputs", (1, 100, 2)),
        ("read_input_registers", (1, 100, 2)),
        ("write_single_coil", (1, 100, True)),
        ("write_multiple_coils", (1, 100, [True, False])),
    ],
)
def test_method_runtime_error_when_not_initialized(method_name, args, modbus_rtu):
    with pytest.raises(RuntimeError):
        getattr(modbus_rtu, method_name)(*args)


@pytest.mark.parametrize(
    "method_name,args",
    [
        ("read_holding_registers", (1, 100, 2)),
        ("write_single_register", (1, 100, 123)),
        ("write_multiple_registers", (1, 100, [1, 2])),
        ("read_coils", (1, 100, 2)),
        ("read_discrete_inputs", (1, 100, 2)),
        ("read_input_registers", (1, 100, 2)),
        ("write_single_coil", (1, 100, True)),
        ("write_multiple_coils", (1, 100, [True, False])),
    ],
)
def test_method_ioerror_on_error_response(method_name, args, modbus_rtu):
    mock_response = MagicMock()
    mock_response.isError.return_value = True

    client_method_name = CLIENT_METHOD_MAP[method_name]
    mock_client = MagicMock()
    getattr(mock_client, client_method_name).return_value = mock_response
    modbus_rtu.client = mock_client

    with pytest.raises(IOError):
        getattr(modbus_rtu, method_name)(*args)


@pytest.mark.parametrize(
    "method_name,args",
    [
        ("read_holding_registers", (1, 100, 2)),
        ("write_single_register", (1, 100, 123)),
    ],
)
def test_method_ioerror_when_response_none(method_name, args, modbus_rtu):
    client_method_name = CLIENT_METHOD_MAP[method_name]
    mock_client = MagicMock()
    getattr(mock_client, client_method_name).return_value = None
    modbus_rtu.client = mock_client

    with pytest.raises(IOError):
        getattr(modbus_rtu, method_name)(*args)
