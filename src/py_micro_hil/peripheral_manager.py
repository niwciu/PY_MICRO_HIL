from abc import ABC, abstractmethod
import sys


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
    def __init__(self, devices, logger, logging_enabled=True):
        """
        Zarządza urządzeniami i rezerwacjami GPIO oraz portów.
        :param devices: Słownik z urządzeniami grupowanymi jako "protocols" i "peripherals".
        :param logger: Instancja klasy Logger do logowania.
        :param logging_enabled: Czy domyślnie włączyć logowanie w urządzeniach.
        """
        self.devices = devices
        self.logger = logger
        self.logging_enabled = logging_enabled
        self.gpio_registry = {}  # Rejestracja zajętych pinów w formacie {pin: "DeviceName"}
        self.port_registry = {}  # Rejestracja zajętych portów w formacie {port: "DeviceName"}
        self.initialized_devices = []  # Lista urządzeń zainicjalizowanych do momentu błędu

        # Przekazujemy logger i ustawiamy logowanie w urządzeniach
        for group in ['protocols', 'peripherals']:
            if group in self.devices:
                for device in self.devices[group]:
                    if hasattr(device, 'logger'):
                        device.logger = self.logger
                    if hasattr(device, 'logging_enabled'):
                        device.logging_enabled = self.logging_enabled

    def enable_logging_all(self):
        """
        Włącza logowanie we wszystkich urządzeniach.
        """
        self.logging_enabled = True
        for group in ['protocols', 'peripherals']:
            if group in self.devices:
                for device in self.devices[group]:
                    if hasattr(device, 'enable_logging'):
                        device.enable_logging()

    def disable_logging_all(self):
        """
        Wyłącza logowanie we wszystkich urządzeniach.
        """
        self.logging_enabled = False
        for group in ['protocols', 'peripherals']:
            if group in self.devices:
                for device in self.devices[group]:
                    if hasattr(device, 'disable_logging'):
                        device.disable_logging()

    def initialize_all(self):
        """
        Inicjalizuje wszystkie urządzenia w grupach 'protocols' i 'peripherals'.
        """
        for group, devices in self.devices.items():
            self.logger.log(f"\nInitializing {group}...", to_console=True)
            for device in devices:
                try:
                    resources = device.get_required_resources()
                    pins = resources.get("pins", [])
                    ports = resources.get("ports", [])

                    self._reserve_pins(pins, device.__class__.__name__)
                    self._reserve_ports(ports, device.__class__.__name__)

                    device.initialize()
                    self._log_resources_initialized(resources, device)
                    self.initialized_devices.append(device)

                    self.logger.log(f"[INFO] {device.__class__.__name__} initialized successfully.", to_console=True)
                except RuntimeError as e:
                    self.release_all()
                    self.logger.log(f"{str(e)}", to_console=True)
                    sys.exit(1)
                except Exception as e:
                    self.logger.log(f"[ERROR] Unexpected error: {str(e)}", to_console=True)
                    self.release_all()
                    sys.exit(1)
            self.logger.log(f"All {group} initialized.", to_console=True)

    def release_all(self):
        """
        Zwalnia wszystkie urządzenia w grupach 'protocols' i 'peripherals'.
        """
        for device in self.initialized_devices:
            try:
                device.release()
                self.logger.log(f"[INFO] Released {device.__class__.__name__}.", to_console=True)
            except Exception as e:
                self.logger.log(f"[ERROR] Error during releasing {device.__class__.__name__}: {str(e)}", to_console=True)
        self.initialized_devices.clear()  # Czyszczenie listy zainicjalizowanych urządzeń
        self.gpio_registry.clear()  # Czyszczenie rejestru pinów
        self.port_registry.clear()  # Czyszczenie rejestru portów
        self.logger.log("[INFO] All resources released.", to_console=True)

    def _reserve_pins(self, pins, device_name):
        """
        Rezerwuje piny GPIO dla urządzenia.
        :param pins: Lista pinów GPIO do zarezerwowania.
        :param device_name: Nazwa urządzenia rezerwującego piny.
        :raises RuntimeError: Jeśli którykolwiek pin jest już zajęty.
        """
        for pin in pins:
            if pin in self.gpio_registry:
                conflicting_device = self.gpio_registry[pin]
                self._log_conflict(pin, device_name, conflicting_device, resource_type="Pin")
            self.gpio_registry[pin] = device_name
            self.logger.log(f"[INFO] Pin {pin} reserved for {device_name}.", to_console=True)

    def _reserve_ports(self, ports, device_name):
        """
        Rezerwuje porty dla urządzenia.
        :param ports: Lista portów do zarezerwowania.
        :param device_name: Nazwa urządzenia rezerwującego porty.
        :raises RuntimeError: Jeśli którykolwiek port jest już zajęty.
        """
        for port in ports:
            if port in self.port_registry:
                conflicting_device = self.port_registry[port]
                self._log_conflict(port, device_name, conflicting_device, resource_type="Port")
            self.port_registry[port] = device_name

            # Logowanie parametrów portu przy rezerwacji
            if isinstance(port, str):  # Jeżeli jest to port, np. /dev/ttyUSB0
                self.logger.log(f"[INFO] Port {port} reserved for {device_name}.", to_console=True)

    def _log_conflict(self, resource, current_device, conflicting_device, resource_type):
        """
        Loguje konflikt zasobu i kończy działanie programu.
        :param resource: Nazwa zasobu (pin lub port).
        :param current_device: Urządzenie próbujące zarezerwować zasób.
        :param conflicting_device: Urządzenie, które już zarezerwowało zasób.
        :param resource_type: Typ zasobu ('Pin' lub 'Port').
        """
        message = (f"[ERROR] {resource_type} {resource} conflict: {current_device} cannot be initialized "
                   f"because it is already reserved by {conflicting_device}.")
        self.logger.log(message, to_console=True)
        raise RuntimeError(message)

    def _log_resources_initialized(self, resources, device):
        """
        Loguje pomyślne zainicjalizowanie zasobów.
        :param resources: Słownik z zasobami.
        :param device_name: Nazwa urządzenia inicjalizującego zasoby.
        """
        for pin in resources.get("pins", []):
            self.logger.log(f"[INFO] Pin {pin} successfully initialized by {device.__class__.__name__}.", to_console=True)
        for port in resources.get("ports", []):
            device_param = device.get_initialized_params()
            # Tworzymy dynamiczny log dla portu
            params_str = ', '.join([f"{key}: {value}" for key, value in device_param.items()])
            
            self.logger.log(f"[INFO] {device.__class__.__name__} successfully open {params_str} ", to_console=True)

    def get_device(self, group, name):
        """
        Znajduje urządzenie na podstawie grupy (protocols/peripherals) i nazwy.
        :param group: Nazwa grupy ('protocols' lub 'peripherals').
        :param name: Nazwa klasy urządzenia (np. 'RPiGPIO').
        :return: Instancja urządzenia lub None, jeśli nie znaleziono.
        """
        if group in self.devices:
            for device in self.devices[group]:
                if type(device).__name__ == name:
                    return device
        raise ValueError(f"Device '{name}' not found in group '{group}'.")
