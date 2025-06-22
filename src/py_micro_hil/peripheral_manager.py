from abc import ABC, abstractmethod
import sys
from typing import Any, Dict, List, Optional, Union


class Peripheral(ABC):
    @abstractmethod
    def initialize(self):
        pass

    @abstractmethod
    def release(self):
        pass


class Protocol(ABC):
    @abstractmethod
    def initialize(self):
        pass

    @abstractmethod
    def release(self):
        pass


class PeripheralManager:
    def __init__(self, devices: Dict[str, List[Any]], logger: Any, logging_enabled: bool = True):
        """
        Manages devices and reservations of GPIOs and ports.
        :param devices: Dictionary with devices grouped as "protocols" and "peripherals".
        :param logger: Instance of the Logger class for logging.
        :param logging_enabled: Whether to enable logging by default for devices.
        """
        self.devices = devices
        self.logger = logger
        self.logging_enabled = logging_enabled
        self.gpio_registry: Dict[Any, str] = {}  # Registry of occupied pins in the format {pin: "DeviceName"}
        self.port_registry: Dict[Any, str] = {}  # Registry of occupied ports in the format {port: "DeviceName"}
        self.initialized_devices: List[Any] = []  # List of devices initialized up to the point of failure

        # Pass logger and set logging in devices
        for group in ['protocols', 'peripherals']:
            for device in self.devices.get(group, []):
                if hasattr(device, 'logger'):
                    device.logger = self.logger
                if hasattr(device, 'logging_enabled'):
                    device.logging_enabled = self.logging_enabled

    def enable_logging_all(self):
        """
        Enables logging in all devices.
        """
        self.logging_enabled = True
        for group in ['protocols', 'peripherals']:
            for device in self.devices.get(group, []):
                if hasattr(device, 'enable_logging'):
                    device.enable_logging()

    def disable_logging_all(self):
        """
        Disables logging in all devices.
        """
        self.logging_enabled = False
        for group in ['protocols', 'peripherals']:
            for device in self.devices.get(group, []):
                if hasattr(device, 'disable_logging'):
                    device.disable_logging()

    def initialize_all(self):
        """
        Initializes all devices in the 'protocols' and 'peripherals' groups.
        """
        for group, devices in self.devices.items():
            self.logger.log(f"\nInitializing {group}...", to_console=True)
            for device in devices:
                try:
                    device_name = type(device).__name__
                    resources = device.get_required_resources()
                    pins = resources.get("pins", [])
                    ports = resources.get("ports", [])

                    self._reserve_pins(pins, device_name)
                    self._reserve_ports(ports, device_name)

                    device.initialize()
                    self._log_resources_initialized(resources, device, device_name)
                    self.initialized_devices.append(device)

                    self.logger.log(f"[INFO] {device_name} initialized successfully.", to_console=True)
                except RuntimeError as e:
                    self.release_all()
                    self.logger.log(str(e), to_console=True)
                    sys.exit(1)
                except Exception as e:
                    self.logger.log(f"[ERROR] Unexpected error: {str(e)}", to_console=True)
                    self.release_all()
                    sys.exit(1)
            self.logger.log(f"All {group} initialized.", to_console=True)

    def release_all(self):
        """
        Releases all devices in the 'protocols' and 'peripherals' groups.
        """
        for device in self.initialized_devices:
            try:
                self.logger.log(f"[INFO] Releasing {type(device).__name__}...", to_console=True)
                device.release()
                self.logger.log(f"[INFO] Released {type(device).__name__}.", to_console=True)
            except Exception as e:
                self.logger.log(f"[ERROR] Error during releasing {type(device).__name__}: {str(e)}", to_console=True)
        self.initialized_devices.clear()  # Clear the list of initialized devices
        self.gpio_registry.clear()  # Clear the GPIO registry
        self.port_registry.clear()  # Clear the port registry
        self.logger.log("[INFO] All resources released.", to_console=True)

    def _reserve_pins(self, pins: List[Any], device_name: str):
        """
        Reserves GPIO pins for the device.
        :param pins: List of GPIO pins to reserve.
        :param device_name: Name of the device reserving the pins.
        :raises RuntimeError: If any pin is already occupied.
        """
        for pin in pins:
            if pin in self.gpio_registry:
                conflicting_device = self.gpio_registry[pin]
                self._log_conflict(pin, device_name, conflicting_device, resource_type="Pin")
            self.gpio_registry[pin] = device_name
            self.logger.log(f"[INFO] Pin {pin} reserved for {device_name}.", to_console=True)

    def _reserve_ports(self, ports: List[Any], device_name: str):
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
            self.port_registry[port] = device_name

            # Log port parameters upon reservation
            if isinstance(port, str):  # If it's a port, e.g., /dev/ttyUSB0
                self.logger.log(f"[INFO] Port {port} reserved for {device_name}.", to_console=True)

    def _log_conflict(self, resource: Any, current_device: str, conflicting_device: str, resource_type: str):
        """
        Logs a resource conflict and terminates the program.
        :param resource: Name of the resource (pin or port).
        :param current_device: Device trying to reserve the resource.
        :param conflicting_device: Device that already reserved the resource.
        :param resource_type: Type of resource ('Pin' or 'Port').
        """
        message = (f"[ERROR] {resource_type} {resource} conflict: {current_device} cannot be initialized "
                   f"because it is already reserved by {conflicting_device}.")
        self.logger.log(message, to_console=True)
        raise RuntimeError(message)

    def _log_resources_initialized(self, resources: Dict[str, Any], device: Any, device_name: str):
        """
        Logs successful initialization of resources.
        :param resources: Dictionary of resources.
        :param device_name: Name of the device initializing the resources.
        """
        for pin in resources.get("pins", []):
            self.logger.log(f"[INFO] Pin {pin} successfully initialized by {device_name}.", to_console=True)
        for port in resources.get("ports", []):
            device_param = device.get_initialized_params()
            # Create dynamic log entry for the port
            params_str = ', '.join([f"{key}: {value}" for key, value in device_param.items()])

            self.logger.log(f"[INFO] {device_name} successfully open {params_str} ", to_console=True)

    def get_device(self, group: str, name: str) -> Any:
        """
        Finds a device based on group ('protocols' or 'peripherals') and name.
        :param group: Group name ('protocols' or 'peripherals').
        :param name: Class name of the device (e.g., 'RPiGPIO').
        :return: Device instance or raises ValueError if not found.
        """
        for device in self.devices.get(group, []):
            if type(device).__name__ == name:
                return device
        raise ValueError(f"Device '{name}' not found in group '{group}'.")
