from abc import ABC, abstractmethod
from typing import Any, Dict, List


# =============================================================================
# ABSTRACT BASE CLASSES
# =============================================================================


class Peripheral(ABC):
    """
    Abstract base class for a peripheral device.
    Each peripheral must implement initialize() and release().
    """

    @abstractmethod
    def initialize(self) -> None:
        pass

    @abstractmethod
    def release(self) -> None:
        pass


class Protocol(ABC):
    """
    Abstract base class for a communication protocol device.
    Each protocol must implement initialize() and release().
    """

    @abstractmethod
    def initialize(self) -> None:
        pass

    @abstractmethod
    def release(self) -> None:
        pass


# =============================================================================
# CUSTOM EXCEPTIONS
# =============================================================================


class FrameworkError(RuntimeError):
    """Base class for all framework-related errors."""

    pass


class PeripheralInitializationError(FrameworkError):
    """Raised when a critical error occurs during peripheral initialization."""

    pass


# =============================================================================
# PERIPHERAL MANAGER
# =============================================================================


class PeripheralManager:
    """
    Manages devices and reservations of GPIOs and ports.
    Handles initialization, resource conflicts, and cleanup of peripherals.
    """

    def __init__(
        self, devices: Dict[str, List[Any]], logger: Any, logging_enabled: bool = True
    ) -> None:
        """
        :param devices: Dictionary containing devices grouped under 'protocols' and 'peripherals'.
        :param logger: Instance of the Logger class for logging.
        :param logging_enabled: Whether to enable logging by default for all devices.
        :raises AssertionError: If devices is not a dictionary.
        """
        assert isinstance(devices, dict), "devices must be a dictionary"

        self.devices = devices
        self.logger = logger
        self.logging_enabled = logging_enabled

        # Resource registries
        self.gpio_registry: Dict[Any, str] = {}  # {pin: "DeviceName"}
        self.port_registry: Dict[Any, str] = {}  # {port: "DeviceName"}
        self.initialized_devices: List[Any] = []  # Devices initialized before potential failure

        # Pass logger and logging config to all devices
        for group in ["protocols", "peripherals"]:
            for device in self.devices.get(group, []):
                if hasattr(device, "logger"):
                    device.logger = self.logger
                if hasattr(device, "logging_enabled"):
                    device.logging_enabled = self.logging_enabled

    # -------------------------------------------------------------------------
    # Logging enable/disable
    # -------------------------------------------------------------------------

    def enable_logging_all(self) -> None:
        """
        Enables logging for all devices in both groups.
        """
        self.logging_enabled = True
        for group in ["protocols", "peripherals"]:
            for device in self.devices.get(group, []):
                if hasattr(device, "enable_logging"):
                    device.enable_logging()

    def disable_logging_all(self) -> None:
        """
        Disables logging for all devices in both groups.
        """
        self.logging_enabled = False
        for group in ["protocols", "peripherals"]:
            for device in self.devices.get(group, []):
                if hasattr(device, "disable_logging"):
                    device.disable_logging()

    # -------------------------------------------------------------------------
    # Initialization / Cleanup Phases
    # -------------------------------------------------------------------------

    def initialize_all(self) -> None:
        """
        Initializes all devices (protocols and peripherals).
        Handles resource reservation and rollback in case of critical failures.

        :raises PeripheralInitializationError: If a critical device fails to initialize.
        """
        for group, devices in self.devices.items():
            self.logger.log(f"\n[INFO] Initializing {group}...", to_console=True)

            for device in devices:
                device_name = type(device).__name__

                try:
                    # --- Resource reservation ---
                    # Use safe getter in case device doesn't define get_required_resources()
                    resources = getattr(device, "get_required_resources", lambda: {})()
                    self._reserve_pins(resources.get("pins", []), device_name)
                    self._reserve_ports(resources.get("ports", []), device_name)

                    # --- Device initialization ---
                    device.initialize()
                    self._log_resources_initialized(resources, device, device_name)
                    self.initialized_devices.append(device)

                    self.logger.log(
                        f"[INFO] {device_name} initialized successfully.", to_console=True
                    )

                except RuntimeError as e:
                    # Optional device → log warning and continue
                    if getattr(device, "optional", False):
                        self.logger.log(
                            f"[WARNING] Nie zainicjalizowano {device_name}: {e}", to_console=True
                        )
                        continue

                    # Critical error → rollback and abort
                    self.logger.log(
                        f"[ERROR] Krytyczny błąd przy inicjalizacji {device_name}: {e}",
                        to_console=True,
                    )
                    self.release_all()
                    raise PeripheralInitializationError(str(e))

                except Exception as e:
                    # Unexpected exception → rollback and abort
                    self.logger.log(f"[ERROR] Nieoczekiwany błąd: {e}", to_console=True)
                    self.release_all()
                    raise PeripheralInitializationError(str(e))

            # After all devices in this group
            self.logger.log(f"[INFO] All {group} initialized.", to_console=True)

    def release_all(self) -> None:
        """
        Releases all devices in both 'protocols' and 'peripherals'.
        Clears resource registries afterward.
        """
        for device in self.initialized_devices:
            try:
                name = type(device).__name__
                self.logger.log(f"[INFO] Releasing {name}...", to_console=True)
                device.release()
                self.logger.log(f"[INFO] Released {name}.", to_console=True)
            except Exception as e:
                self.logger.log(
                    f"[ERROR] Error during releasing {type(device).__name__}: {str(e)}",
                    to_console=True,
                )

        # --- Cleanup registries ---
        self.initialized_devices.clear()
        self.gpio_registry.clear()
        self.port_registry.clear()

        self.logger.log("[INFO] All resources released.", to_console=True)

    # -------------------------------------------------------------------------
    # Resource Reservation (GPIOs, Ports)
    # -------------------------------------------------------------------------

    def _reserve_pins(self, pins: List[Any], device_name: str) -> None:
        """
        Reserves GPIO pins for a device.
        :param pins: List of GPIO pins to reserve.
        :param device_name: Name of the device reserving the pins.
        :raises RuntimeError: If any pin is already occupied.
        """
        for pin in pins:
            if pin in self.gpio_registry:
                conflicting_device = self.gpio_registry[pin]
                self._log_conflict(pin, device_name, conflicting_device, resource_type="Pin")

            # Mark the pin as reserved
            self.gpio_registry[pin] = device_name
            self.logger.log(f"[INFO] Pin {pin} reserved for {device_name}.", to_console=True)

    def _reserve_ports(self, ports: List[Any], device_name: str) -> None:
        """
        Reserves ports for the device.
        :param ports: List of ports to reserve.
        :param device_name: Name of the device reserving the ports.
        :raises RuntimeError: If any port is already occupied.
        """
        for port in ports:
            if port in self.port_registry:
                conflicting_device = self.port_registry[port]
                self._log_conflict(port, device_name, conflicting_device, resource_type="Port")

            # Mark port as reserved
            self.port_registry[port] = device_name

            # Log port reservation
            if isinstance(port, str):  # e.g., /dev/ttyUSB0
                self.logger.log(f"[INFO] Port {port} reserved for {device_name}.", to_console=True)

    def _log_conflict(
        self, resource: Any, current_device: str, conflicting_device: str, resource_type: str
    ) -> None:
        """
        Logs a resource conflict and raises a RuntimeError.
        :param resource: Name of the resource (pin or port).
        :param current_device: Device trying to reserve the resource.
        :param conflicting_device: Device that already reserved it.
        :param resource_type: 'Pin' or 'Port'.
        """
        message = (
            f"[ERROR] {resource_type} {resource} conflict: "
            f"{current_device} cannot be initialized because it is already reserved by {conflicting_device}."
        )
        self.logger.log(message, to_console=True)
        raise RuntimeError(message)

    def _log_resources_initialized(
        self, resources: Dict[str, Any], device: Any, device_name: str
    ) -> None:
        """
        Logs successful initialization of all resources.
        :param resources: Dict of resources from device.
        :param device: Device instance.
        :param device_name: Device class name.
        """
        for pin in resources.get("pins", []):
            self.logger.log(
                f"[INFO] Pin {pin} successfully initialized by {device_name}.", to_console=True
            )

        for port in resources.get("ports", []):
            device_param = getattr(device, "get_initialized_params", lambda: {})()
            params_str = ", ".join([f"{key}: {value}" for key, value in device_param.items()])
            self.logger.log(
                f"[INFO] {device_name} successfully opened {params_str}", to_console=True
            )

        # Final confirmation log for device readiness
        if resources.get("ports") or resources.get("pins"):
            self.logger.log(f"[INFO] {device_name} ready for operation.", to_console=True)

    # -------------------------------------------------------------------------
    # Device Lookup
    # -------------------------------------------------------------------------

    def get_device(self, group: str, name: str) -> Any:
        """
        Finds a device by group ('protocols' or 'peripherals') and class name.
        :param group: Group name.
        :param name: Class name of the device.
        :return: Matching device instance.
        :raises ValueError: If the device is not found.
        """
        for device in self.devices.get(group, []):
            if type(device).__name__ == name:
                return device
        raise ValueError(f"Device '{name}' not found in group '{group}'.")
