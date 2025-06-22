import pytest
from unittest.mock import MagicMock
from py_micro_hil.peripheral_manager import PeripheralManager, Peripheral, Protocol


class MockDevice:
    def __init__(self, name, pins=None, ports=None):
        self.name = name
        self._pins = pins or []
        self._ports = ports or []
        self.initialized = False
        self.released = False
        self.logger = None
        self.logging_enabled = False

    def get_required_resources(self):
        return {"pins": self._pins, "ports": self._ports}

    def get_initialized_params(self):
        return {"port": self._ports[0] if self._ports else "none"}

    def initialize(self):
        self.initialized = True

    def release(self):
        self.released = True

    def enable_logging(self):
        self.logging_enabled = True

    def disable_logging(self):
        self.logging_enabled = False


@pytest.fixture
def mock_logger():
    logger = MagicMock()
    logger.log = MagicMock()
    return logger


def test_successful_initialization_and_release(mock_logger):
    d1 = MockDevice("P1", pins=[1], ports=["/dev/tty1"])
    d2 = MockDevice("X1", pins=[2], ports=["/dev/tty2"])
    devices = {
        "protocols": [d1],
        "peripherals": [d2]
    }
    manager = PeripheralManager(devices, logger=mock_logger)

    manager.initialize_all()
    assert len(manager.initialized_devices) == 2

    manager.release_all()

    # Ensure devices were released before list was cleared
    assert d1.released is True
    assert d2.released is True


def test_pin_conflict_raises(mock_logger):
    d1 = MockDevice("A", pins=[5])
    d2 = MockDevice("B", pins=[5])
    devices = {"protocols": [d1, d2]}
    manager = PeripheralManager(devices, logger=mock_logger)

    with pytest.raises(SystemExit):
        manager.initialize_all()


def test_port_conflict_raises(mock_logger):
    d1 = MockDevice("A", ports=["/dev/ttyX"])
    d2 = MockDevice("B", ports=["/dev/ttyX"])
    devices = {"protocols": [d1, d2]}
    manager = PeripheralManager(devices, logger=mock_logger)

    with pytest.raises(SystemExit):
        manager.initialize_all()


def test_disable_enable_logging_calls(mock_logger):
    d1 = MockDevice("LogDev")
    devices = {"protocols": [d1]}
    manager = PeripheralManager(devices, logger=mock_logger)

    manager.disable_logging_all()
    assert not d1.logging_enabled

    manager.enable_logging_all()
    assert d1.logging_enabled


def test_get_device_found(mock_logger):
    d1 = MockDevice("GetMe")
    devices = {"protocols": [d1]}
    manager = PeripheralManager(devices, logger=mock_logger)
    result = manager.get_device("protocols", "MockDevice")
    assert result is d1


def test_get_device_not_found_raises(mock_logger):
    devices = {"protocols": []}
    manager = PeripheralManager(devices, logger=mock_logger)
    with pytest.raises(ValueError):
        manager.get_device("protocols", "NotExist")


def test_release_all_clears_registries(mock_logger):
    d1 = MockDevice("D", pins=[3], ports=["/dev/ttyD"])
    devices = {"protocols": [d1]}
    manager = PeripheralManager(devices, logger=mock_logger)
    manager.initialize_all()
    assert manager.gpio_registry
    assert manager.port_registry
    manager.release_all()
    assert not manager.gpio_registry
    assert not manager.port_registry
