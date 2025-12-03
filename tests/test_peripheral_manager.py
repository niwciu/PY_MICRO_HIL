import pytest
from unittest.mock import MagicMock
from py_micro_hil.peripheral_manager import (
    PeripheralManager,
    PeripheralInitializationError,
)


# -------------------------------------------------------------------------
# MOCK CLASSES
# -------------------------------------------------------------------------


class MockDevice:
    """Mock device used to simulate peripherals or protocols."""

    def __init__(self, name, pins=None, ports=None, optional=False, fail=False, unexpected=False):
        self.name = name
        self._pins = pins or []
        self._ports = ports or []
        self.initialized = False
        self.released = False
        self.logger = None
        self.logging_enabled = False
        self.optional = optional
        self._fail = fail
        self._unexpected = unexpected

    def get_required_resources(self):
        """Return simulated required resources."""
        return {"pins": self._pins, "ports": self._ports}

    def get_initialized_params(self):
        """Return simulated initialized params."""
        if self._ports:
            return {"port": self._ports[0]}
        return {}

    def initialize(self):
        """Simulate initialization with optional failure."""
        if self._unexpected:
            raise Exception("Unexpected error")
        if self._fail:
            raise RuntimeError("Init failed")
        self.initialized = True

    def release(self):
        """Simulate device release."""
        self.released = True

    def enable_logging(self):
        self.logging_enabled = True

    def disable_logging(self):
        self.logging_enabled = False


@pytest.fixture
def mock_logger():
    """Provides a MagicMock logger compatible with PeripheralManager."""
    logger = MagicMock()
    logger.log = MagicMock()
    return logger


# -------------------------------------------------------------------------
# INITIALIZATION AND RELEASE
# -------------------------------------------------------------------------


def test_successful_initialization_and_release(mock_logger):
    d1 = MockDevice("P1", pins=[1], ports=["/dev/tty1"])
    d2 = MockDevice("X1", pins=[2], ports=["/dev/tty2"])
    devices = {"protocols": [d1], "peripherals": [d2]}
    manager = PeripheralManager(devices, logger=mock_logger)

    manager.initialize_all()

    assert d1.initialized
    assert d2.initialized
    assert len(manager.initialized_devices) == 2

    # check initialization log
    mock_logger.log.assert_any_call("[INFO] MockDevice initialized successfully.", to_console=True)

    manager.release_all()

    assert d1.released
    assert d2.released
    assert not manager.gpio_registry
    assert not manager.port_registry


# -------------------------------------------------------------------------
# RESOURCE CONFLICTS
# -------------------------------------------------------------------------


def test_pin_conflict_raises(mock_logger):
    d1 = MockDevice("A", pins=[5])
    d2 = MockDevice("B", pins=[5])
    devices = {"protocols": [d1, d2]}
    manager = PeripheralManager(devices, logger=mock_logger)

    with pytest.raises(PeripheralInitializationError):
        manager.initialize_all()


def test_port_conflict_raises(mock_logger):
    d1 = MockDevice("A", ports=["/dev/ttyX"])
    d2 = MockDevice("B", ports=["/dev/ttyX"])
    devices = {"protocols": [d1, d2]}
    manager = PeripheralManager(devices, logger=mock_logger)

    with pytest.raises(PeripheralInitializationError):
        manager.initialize_all()


# -------------------------------------------------------------------------
# OPTIONAL DEVICES AND FAILURES
# -------------------------------------------------------------------------


def test_optional_device_does_not_abort(mock_logger):
    d1 = MockDevice("Critical", pins=[1])
    d2 = MockDevice("OptionalFail", pins=[2], optional=True, fail=True)
    devices = {"protocols": [d1, d2]}
    manager = PeripheralManager(devices, logger=mock_logger)

    manager.initialize_all()

    assert d1.initialized
    assert not d2.initialized

    mock_logger.log.assert_any_call(
        "[WARNING] Nie zainicjalizowano MockDevice: Init failed", to_console=True
    )


def test_unexpected_error_triggers_rollback(mock_logger):
    d1 = MockDevice("Good", pins=[1])
    d2 = MockDevice("Bad", pins=[2], unexpected=True)
    devices = {"protocols": [d1, d2]}
    manager = PeripheralManager(devices, logger=mock_logger)

    with pytest.raises(PeripheralInitializationError):
        manager.initialize_all()

    mock_logger.log.assert_any_call("[INFO] All resources released.", to_console=True)


def test_runtime_error_triggers_rollback(mock_logger):
    d1 = MockDevice("Critical", pins=[1], fail=True)
    devices = {"protocols": [d1]}
    manager = PeripheralManager(devices, logger=mock_logger)

    with pytest.raises(PeripheralInitializationError):
        manager.initialize_all()

    mock_logger.log.assert_any_call("[INFO] All resources released.", to_console=True)


# -------------------------------------------------------------------------
# LOGGING CONTROL
# -------------------------------------------------------------------------


def test_disable_enable_logging_calls(mock_logger):
    d1 = MockDevice("LogDev")
    devices = {"protocols": [d1]}
    manager = PeripheralManager(devices, logger=mock_logger)

    manager.disable_logging_all()
    assert not d1.logging_enabled

    manager.enable_logging_all()
    assert d1.logging_enabled


# -------------------------------------------------------------------------
# DEVICE LOOKUP
# -------------------------------------------------------------------------


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


# -------------------------------------------------------------------------
# RELEASE AND CLEANUP
# -------------------------------------------------------------------------


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
    assert d1.released


# -------------------------------------------------------------------------
# EDGE CASES
# -------------------------------------------------------------------------


def test_device_without_get_required_resources(mock_logger):
    class MinimalDevice:
        def initialize(self):
            self.initialized = True

        def release(self):
            self.released = True

    d = MinimalDevice()
    devices = {"protocols": [d]}
    manager = PeripheralManager(devices, logger=mock_logger)

    manager.initialize_all()
    assert d.initialized

    manager.release_all()
    assert d.released


def test_assert_devices_type(mock_logger):
    with pytest.raises(AssertionError):
        PeripheralManager([], logger=mock_logger)
