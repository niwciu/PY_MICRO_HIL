import sys
import re
from py_micro_hil.utils.system import is_raspberry_pi
import RPi.GPIO as GPIO
import spidev
import serial
from smbus2 import SMBus
import glob

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

ON_RPI = is_raspberry_pi()

if not ON_RPI:
    from py_micro_hil.peripherals import dummyRPiPeripherals as mock

    sys.modules["RPi.GPIO"] = mock.GPIO
    sys.modules["spidev"] = mock.spidev
    sys.modules["smbus2"] = type("smbus2", (), {"SMBus": mock.SMBus})
    sys.modules["serial"] = mock.serial


# Mixins for logging and resource management
class LoggingMixin:
    """
    Mixin providing enable/disable logging and an internal _log helper.
    """

    def __init__(
        self, logger: Optional[logging.Logger] = None, logging_enabled: bool = True
    ) -> None:
        self._logger = logger
        self._logging_enabled = logging_enabled

    def enable_logging(self) -> None:
        """Enable debug logging."""
        self._logging_enabled = True

    def disable_logging(self) -> None:
        """Disable debug logging."""
        self._logging_enabled = False

    def _log(self, message: str, level: int = logging.INFO) -> None:
        """
        Internal helper to log a message if logging is enabled.
        Accepts an optional `level` for compatibility, but always logs at INFO.
        """
        if self._logging_enabled and self._logger:
            # our Logger.log(msg, to_console=False, to_log_file=False)
            self._logger.log(message)


class ResourceMixin:
    """
    Mixin enabling use as a context manager: calls initialize on enter,
    and release on exit.
    """

    def __enter__(self) -> Any:
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()


# --- GPIO ---
class RPiGPIO_API(ABC):
    """Abstract interface for GPIO digital I/O."""

    @abstractmethod
    def write(self, pin: Union[int, str], value: Union[int, str, bool]) -> None:
        pass

    @abstractmethod
    def read(self, pin: Union[int, str]) -> int:
        pass

    @abstractmethod
    def toggle(self, pin: Union[int, str]) -> None:
        pass

    @abstractmethod
    def enable_logging(self) -> None:
        pass

    @abstractmethod
    def disable_logging(self) -> None:
        pass


class RPiGPIO(LoggingMixin, ResourceMixin, RPiGPIO_API):
    """
    Implementation of GPIO digital I/O using RPi.GPIO.
    """

    def __init__(
        self,
        pin_config: Dict[int, Dict[str, Any]],
        logger: Optional[logging.Logger] = None,
        logging_enabled: bool = True,
    ) -> None:
        super().__init__(logger, logging_enabled)
        self._pin_config = pin_config
        self._name_to_pin = {
            str(cfg.get("name")).strip().lower(): pin
            for pin, cfg in self._pin_config.items()
            if isinstance(cfg.get("name"), str) and cfg.get("name").strip()
        }
        register_gpio_label_constants(self._pin_config)

    def get_required_resources(self) -> Dict[str, List[int]]:
        return {"pins": list(self._pin_config.keys())}

    @staticmethod
    def register_label_constants(pin_config: Dict[int, Dict[str, Any]]) -> None:
        register_gpio_label_constants(pin_config)

    def initialize(self) -> None:
        """Configure all GPIO pins according to pin_config."""
        GPIO.setmode(GPIO.BCM)
        for pin, cfg in self._pin_config.items():
            mode = cfg.get("mode", GPIO.IN)
            initial = cfg.get("initial")
            name = cfg.get("name")
            label = f" ({name})" if isinstance(name, str) and name.strip() else ""
            if mode == GPIO.OUT:
                if initial is not None:
                    GPIO.setup(pin, GPIO.OUT, initial=initial)
                else:
                    GPIO.setup(pin, GPIO.OUT)
                self._log(f"[INFO] Initialized OUTPUT pin {pin}{label}")
            else:
                GPIO.setup(pin, GPIO.IN)
                self._log(f"[INFO] Initialized INPUT pin {pin}{label}")

    def _resolve_pin(self, pin: Union[int, str]) -> int:
        if isinstance(pin, int):
            return pin

        if isinstance(pin, str):
            stripped = pin.strip()
            normalized = stripped.lower()
            if normalized in self._name_to_pin:
                return self._name_to_pin[normalized]
            if stripped.isdigit():
                return int(stripped)
            raise ValueError(f"Unknown GPIO label: {pin}")

        raise TypeError("pin must be an int or string label")

    def _pin_label(self, pin: Union[int, str]) -> str:
        """Return a label string for a pin if a name is configured, else empty string.

        Example: ' (LED)'
        """
        resolved = None
        try:
            resolved = self._resolve_pin(pin)
        except Exception:
            return ""

        cfg = self._pin_config.get(resolved, {})
        name = cfg.get("name") if isinstance(cfg, dict) else None
        if isinstance(name, str) and name.strip():
            return f" ({name})"
        return ""

    def _normalize_value(self, value: Union[int, str, bool]) -> int:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized == "high":
                return GPIO.HIGH
            if normalized == "low":
                return GPIO.LOW
            raise ValueError("GPIO value must be 'high'/'HIGH', 'low'/'LOW', 1, 0, True, or False")

        if value in (GPIO.HIGH, GPIO.LOW):
            return value

        if isinstance(value, bool):
            return GPIO.HIGH if value else GPIO.LOW

        if isinstance(value, int) and value in (0, 1):
            return GPIO.HIGH if value else GPIO.LOW

        raise ValueError("GPIO value must be 'high'/'HIGH', 'low'/'LOW', 1, 0, True, or False")

    def write(self, pin: Union[int, str], value: Union[int, str, bool]) -> None:
        """Set digital output value on a pin."""
        resolved_pin = self._resolve_pin(pin)
        normalized_value = self._normalize_value(value)
        GPIO.output(resolved_pin, normalized_value)
        label = self._pin_label(resolved_pin)
        self._log(f"[DEBUG] Wrote value {normalized_value} to pin {resolved_pin}{label}")

    def read(self, pin: Union[int, str]) -> int:
        """Read digital input value from a pin."""
        resolved_pin = self._resolve_pin(pin)
        val = GPIO.input(resolved_pin)
        label = self._pin_label(resolved_pin)
        self._log(f"[DEBUG] Read value {val} from pin {resolved_pin}{label}")
        return val

    def toggle(self, pin: Union[int, str]) -> None:
        """Toggle digital output on a pin."""
        resolved_pin = self._resolve_pin(pin)
        current = GPIO.input(resolved_pin)
        GPIO.output(resolved_pin, not current)
        label = self._pin_label(resolved_pin)
        self._log(f"[DEBUG] Toggled pin {resolved_pin}{label} to {not current}")

    def release(self) -> None:
        """Clean up all configured GPIO pins."""
        for pin, cfg in self._pin_config.items():
            name = cfg.get("name")
            label = f" ({name})" if isinstance(name, str) and name.strip() else ""
            GPIO.cleanup(pin)
            self._log(f"[INFO] Cleaned up pin {pin}{label}")

    @staticmethod
    def get_gpio_interface():
        """Return the configured GPIO interface module."""
        return GPIO


# --- Software PWM ---
class RPiPWM_API(ABC):
    """Abstract interface for software PWM using RPi.GPIO."""

    @abstractmethod
    def set_duty_cycle(self, duty_cycle: float) -> None:
        pass

    @abstractmethod
    def set_frequency(self, frequency: float) -> None:
        pass

    @abstractmethod
    def enable_logging(self) -> None:
        pass

    @abstractmethod
    def disable_logging(self) -> None:
        pass


class RPiPWM(LoggingMixin, ResourceMixin, RPiPWM_API):
    """
    Software PWM on a GPIO pin via RPi.GPIO.PWM.
    """

    def __init__(
        self,
        pin: int,
        frequency: float = 1000.0,
        logger: Optional[logging.Logger] = None,
        logging_enabled: bool = True,
    ) -> None:
        super().__init__(logger, logging_enabled)
        self.pin = pin
        self.frequency = frequency
        self._pwm: Optional[GPIO.PWM] = None

    def get_required_resources(self) -> Dict[str, List[int]]:
        return {"pins": [self.pin]}

    def initialize(self) -> None:
        """Initialize PWM with given frequency on pin."""
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT)
        self._pwm = GPIO.PWM(self.pin, self.frequency)
        self._pwm.start(0)
        self._log(f"[INFO] Started PWM on pin {self.pin} at {self.frequency}Hz")

    def set_duty_cycle(self, duty_cycle: float) -> None:
        """Change PWM duty cycle (0-100)."""
        if not 0 <= duty_cycle <= 100:
            raise ValueError("Duty cycle must be 0-100%")
        self._pwm.ChangeDutyCycle(duty_cycle)
        self._log(f"[DEBUG] Duty cycle set to {duty_cycle}% on pin {self.pin}")

    def set_frequency(self, frequency: float) -> None:
        """Change PWM frequency."""
        if frequency <= 0:
            raise ValueError("Frequency must be > 0Hz")
        self._pwm.ChangeFrequency(frequency)
        self._log(f"[DEBUG] Frequency changed to {frequency}Hz on pin {self.pin}")

    def release(self) -> None:
        """Stop PWM and clean up GPIO."""
        if self._pwm:
            self._pwm.stop()
        GPIO.cleanup(self.pin)
        self._log(f"[INFO] Stopped PWM and cleaned up pin {self.pin}")


# --- UART API ---
class RPiUART_API(ABC):
    """Abstract interface for UART serial communication."""

    @abstractmethod
    def initialize(self) -> None:
        pass

    @abstractmethod
    def send(self, data: Union[str, bytes]) -> None:
        pass

    @abstractmethod
    def receive(self, size: int = 1) -> bytes:
        pass

    @abstractmethod
    def readline(self) -> bytes:
        pass

    @abstractmethod
    def release(self) -> None:
        pass

    @abstractmethod
    def enable_logging(self) -> None:
        pass

    @abstractmethod
    def disable_logging(self) -> None:
        pass


# Mapping hardware UART ports to their corresponding GPIO pins
UART_PIN_MAP = {
    "/dev/ttyAMA0": [14, 15],  # uart0 (PL011)
    "/dev/ttyS0": [14, 15],  # uart1 (mini UART)
    "/dev/ttyAMA1": [0, 1],  # uart2 (PL011)
    "/dev/ttyAMA2": [4, 5],  # uart3 (PL011)
    "/dev/ttyAMA3": [8, 9],  # uart4 (PL011)
    "/dev/ttyAMA4": [12, 13],  # uart5 (PL011)
    "/dev/serial0": [14, 15],  # system alias (mapped dynamically)
}


class RPiUART(LoggingMixin, ResourceMixin, RPiUART_API):
    """
    UART interface using pyserial on Raspberry Pi.
    """

    def __init__(
        self,
        port: str = "/dev/serial0",
        baudrate: int = 9600,
        timeout: float = 1.0,
        parity: Any = serial.PARITY_NONE,
        stopbits: Any = serial.STOPBITS_ONE,
        logger: Optional[logging.Logger] = None,
        logging_enabled: bool = True,
    ) -> None:
        super().__init__(logger, logging_enabled)
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.parity = parity
        self.stopbits = stopbits
        self._serial: Optional[serial.Serial] = None

    def get_required_resources(self) -> Dict[str, List[Union[int, str]]]:
        """
        Return required resources based on port type.

        - Hardware UART (ttyAMA*, ttyS0, serial0):
          → return GPIO pins assigned to that UART.
        - USB UART (ttyUSB*, ttyACM*):
          → return only the port, no GPIO pins.
        """

        # USB serial adapters do not use Raspberry Pi GPIO pins
        if self.port.startswith("/dev/ttyUSB") or self.port.startswith("/dev/ttyACM"):
            return {"ports": [self.port]}

        # Hardware UART: lookup GPIO pins
        pins = UART_PIN_MAP.get(self.port, [])

        return {
            "pins": pins,
            "ports": [self.port],
        }

    def initialize(self) -> None:
        """Open the serial port for UART communication."""
        self._serial = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout,
            parity=self.parity,
            stopbits=self.stopbits,
        )
        self._log(f"[INFO] Initialized UART on {self.port} at {self.baudrate}bps")

    def get_initialized_params(self) -> Dict[str, Any]:
        """
        Return the UART configuration parameters after initialization.
        """
        return {
            "port": self.port,
            "baudrate": self.baudrate,
            "timeout": self.timeout,
            "parity": self.parity,
            "stopbits": self.stopbits,
        }

    def send(self, data: Union[str, bytes]) -> None:
        """Send bytes or a string over UART."""
        if isinstance(data, str):
            data = data.encode()
        self._serial.write(data)
        self._log(f"[DEBUG] Sent {data} over UART")

    def receive(self, size: int = 1) -> bytes:
        """Read a fixed number of bytes from UART."""
        data = self._serial.read(size)
        self._log(f"[DEBUG] Received {data} from UART")
        return data

    def readline(self) -> bytes:
        """Read a line (until newline) from UART."""
        line = self._serial.readline()
        self._log(f"[DEBUG] Read line {line} from UART")
        return line

    def release(self) -> None:
        """Close the UART serial port."""
        if self._serial:
            self._serial.close()
            self._log(f"[INFO] Closed UART on {self.port}")


# --- I2C ---
class RPiI2C_API(ABC):
    """Abstract interface for I2C communication."""

    @abstractmethod
    def scan(self) -> List[int]:
        pass

    @abstractmethod
    def read(self, address: int, register: int, length: int) -> List[int]:
        pass

    @abstractmethod
    def write(self, address: int, register: int, data: List[int]) -> None:
        pass

    @abstractmethod
    def read_byte(self, address: int) -> int:
        pass

    @abstractmethod
    def write_byte(self, address: int, value: int) -> None:
        pass

    @abstractmethod
    def read_word(self, address: int, register: int) -> int:
        pass

    @abstractmethod
    def write_word(self, address: int, register: int, value: int) -> None:
        pass

    @abstractmethod
    def enable_logging(self) -> None:
        pass

    @abstractmethod
    def disable_logging(self) -> None:
        pass


# Mapping I2C buses to their corresponding GPIO pins (BCM numbering)
I2C_PIN_MAP = {
    0: [0, 1],  # SDA0, SCL0 (BSC0) - requires overlay: i2c0
    1: [2, 3],  # SDA1, SCL1 (BSC1) - enabled by raspi-config
    3: [4, 5],  # BSC3 - requires overlay: i2c3
    4: [6, 7],  # BSC4 - requires overlay: i2c4
    5: [12, 13],  # BSC5 - requires overlay: i2c5
    6: [22, 23],  # BSC6 - requires overlay: i2c6
}


class RPiI2C(LoggingMixin, ResourceMixin, RPiI2C_API):
    """
    I2C interface using smbus2 on Raspberry Pi.
    Supports multiple I2C buses (0,1,3,4,5,6) depending on overlays.
    """

    def __init__(
        self,
        bus_number: int = 1,
        frequency: int = 100000,
        logger: Optional[logging.Logger] = None,
        logging_enabled: bool = True,
    ) -> None:
        super().__init__(logger, logging_enabled)
        self.bus_number = bus_number
        self.frequency = frequency
        self.bus: Optional[SMBus] = None

    def get_required_resources(self) -> Dict[str, List[Union[int, str]]]:
        """
        Return required resources for this I2C bus.

        - Hardware I2C (buses 0,1,3,4,5,6):
          → returns GPIO pins based on I2C_PIN_MAP.

        - USB I2C adapters (e.g. /dev/i2c-20):
          → returns only the I2C device path, no GPIO pins.
        """
        dev_path = f"/dev/i2c-{self.bus_number}"

        # USB / non-header I2C dongles or unsupported bus number
        if self.bus_number not in I2C_PIN_MAP:
            return {"ports": [dev_path]}

        # Hardware I2C bus → return GPIO pins
        pins = I2C_PIN_MAP[self.bus_number]

        return {
            "pins": pins,
            "ports": [dev_path],
        }

    def initialize(self) -> None:
        """Open the I2C bus."""
        self.bus = SMBus(self.bus_number)
        self._log(f"[INFO] Initialized I2C bus {self.bus_number} at {self.frequency}Hz")

    def get_initialized_params(self) -> Dict[str, Any]:
        """Return I2C configuration parameters after initialization."""
        return {
            "bus_number": self.bus_number,
            "frequency": self.frequency,
        }

    def scan(self) -> List[int]:
        """Scan the I2C bus for active device addresses."""
        devices: List[int] = []
        for addr in range(0x08, 0x78):
            try:
                self.bus.write_quick(addr)
                devices.append(addr)
            except Exception:
                pass
        self._log(f"[DEBUG] I2C scan found {devices}")
        return devices

    def read(self, address: int, register: int, length: int) -> List[int]:
        """Read a block of bytes from a device."""
        data = self.bus.read_i2c_block_data(address, register, length)
        self._log(f"[DEBUG] I2C read from 0x{address:02X}, reg 0x{register:02X}: {data}")
        return data

    def write(self, address: int, register: int, data: List[int]) -> None:
        """Write a block of bytes to a device."""
        self.bus.write_i2c_block_data(address, register, data)
        self._log(f"[DEBUG] I2C write to 0x{address:02X}, reg 0x{register:02X}: {data}")

    def read_byte(self, address: int) -> int:
        """Read a single byte."""
        val = self.bus.read_byte(address)
        self._log(f"[DEBUG] I2C read_byte from 0x{address:02X}: 0x{val:02X}")
        return val

    def write_byte(self, address: int, value: int) -> None:
        """Write a single byte."""
        self.bus.write_byte(address, value)
        self._log(f"[DEBUG] I2C write_byte to 0x{address:02X}: 0x{value:02X}")

    def read_word(self, address: int, register: int) -> int:
        """Read a 16-bit word."""
        val = self.bus.read_word_data(address, register)
        self._log(f"[DEBUG] I2C read_word from 0x{address:02X}, reg 0x{register:02X}: 0x{val:04X}")
        return val

    def write_word(self, address: int, register: int, value: int) -> None:
        """Write a 16-bit word."""
        self.bus.write_word_data(address, register, value)
        self._log(f"[DEBUG] I2C write_word to 0x{address:02X}, reg 0x{register:02X}: 0x{value:04X}")

    def release(self) -> None:
        """Close the I2C bus."""
        if self.bus:
            self.bus.close()
            self._log(f"[INFO] Closed I2C bus {self.bus_number}")


# --- SPI ---
class RPiSPI_API(ABC):
    """Abstract interface for SPI communication."""

    @abstractmethod
    def transfer(self, data: List[int]) -> List[int]:
        pass

    @abstractmethod
    def transfer_bytes(self, data: bytes) -> bytes:
        pass

    @abstractmethod
    def write_bytes(self, data: List[int]) -> None:
        pass

    @abstractmethod
    def read_bytes(self, length: int) -> List[int]:
        pass

    @abstractmethod
    def transfer2(self, data: List[int]) -> List[int]:
        pass

    @abstractmethod
    def enable_logging(self) -> None:
        pass

    @abstractmethod
    def disable_logging(self) -> None:
        pass


# Mapping SPI buses to their GPIO pins (BCM numbering)
SPI_PIN_MAP = {
    0: {
        "mosi": 10,
        "miso": 9,
        "sclk": 11,
        "ce": {0: 8, 1: 7},  # CE0, CE1 on header
    },
    1: {
        "mosi": 20,
        "miso": 19,
        "sclk": 21,
        "ce": {0: 18, 1: 17, 2: 16},  # CE0, CE1, CE2 (overlay, not on all boards)
    },
    2: {
        # SPI2 pins: only on SoC / CM, not on 40-pin header of standard boards
        "mosi": 40,
        "miso": 41,
        "sclk": 42,
        "ce": {0: 43, 1: 44, 2: 45},
    },
}


class RPiSPI(LoggingMixin, ResourceMixin, RPiSPI_API):
    """
    SPI interface using spidev.
    This version automatically determines GPIO pins based on the
    hardware SPI bus number.
    """

    def __init__(
        self,
        bus: int = 0,
        device: int = 0,
        max_speed_hz: int = 500000,
        mode: int = 0,
        bits_per_word: int = 8,
        cs_high: bool = False,
        lsbfirst: bool = False,
        logger: Optional[logging.Logger] = None,
        logging_enabled: bool = True,
    ) -> None:
        super().__init__(logger, logging_enabled)
        self.bus = bus  # SPI bus number (0,1,2)
        self.device = device  # CE line (chip select)
        self.max_speed_hz = max_speed_hz
        self.mode = mode
        self.bits_per_word = bits_per_word
        self.cs_high = cs_high
        self.lsbfirst = lsbfirst
        self.spi = spidev.SpiDev()

    def get_required_resources(self) -> Dict[str, List[Union[int, str]]]:
        """
        Return required GPIO pins and the SPI device path.

        - If the SPI bus is hardware-based (0,1,2), use SPI_PIN_MAP.
        - If the bus number is unrecognized, assume virtual/USB SPI → no pins.

        Example device name: /dev/spidev0.1  →  bus=0, device=1
        """
        dev_path = f"/dev/spidev{self.bus}.{self.device}"

        # Unknown bus number → possibly virtual/USB SPI
        if self.bus not in SPI_PIN_MAP:
            return {"ports": [dev_path]}

        spi_info = SPI_PIN_MAP[self.bus]

        # Shared lines (MOSI, MISO, SCLK)
        pins = [
            spi_info["mosi"],
            spi_info["miso"],
            spi_info["sclk"],
        ]

        # Add the chip-select pin (CE)
        ce_map = spi_info["ce"]
        if self.device in ce_map:
            pins.append(ce_map[self.device])
        else:
            # Unsupported CE line (e.g., CE2 without overlay)
            pass

        return {
            "pins": pins,
            "ports": [dev_path],
        }

    def initialize(self) -> None:
        """Open SPI device and configure parameters."""
        self.spi.open(self.bus, self.device)
        self.spi.max_speed_hz = self.max_speed_hz
        self.spi.mode = self.mode
        self.spi.bits_per_word = self.bits_per_word
        self.spi.cshigh = self.cs_high
        self.spi.lsbfirst = self.lsbfirst
        self._log(
            f"[INFO] Initialized SPI /dev/spidev{self.bus}.{self.device} "
            f"@ {self.max_speed_hz}Hz"
        )

    def get_initialized_params(self) -> Dict[str, Any]:
        """Return SPI configuration parameters after initialization."""
        return {
            "bus": self.bus,
            "device": self.device,
            "max_speed_hz": self.max_speed_hz,
            "mode": self.mode,
            "bits_per_word": self.bits_per_word,
            "cs_high": self.cs_high,
            "lsbfirst": self.lsbfirst,
        }

    def transfer(self, data: List[int]) -> List[int]:
        """Full-duplex SPI transfer (list of ints)."""
        resp = self.spi.xfer(data)
        self._log(f"[DEBUG] SPI transfer sent={data}, recv={resp}")
        return resp

    def transfer_bytes(self, data: bytes) -> bytes:
        """Full-duplex SPI transfer (bytes)."""
        resp = bytes(self.spi.xfer(list(data)))
        self._log(f"[DEBUG] SPI transfer_bytes sent={list(data)}, recv={list(resp)}")
        return resp

    def write_bytes(self, data: List[int]) -> None:
        """Write-only SPI transaction."""
        self.spi.writebytes(data)
        self._log(f"[DEBUG] SPI write_bytes data={data}")

    def read_bytes(self, length: int) -> List[int]:
        """Read-only SPI transaction."""
        data = self.spi.readbytes(length)
        self._log(f"[DEBUG] SPI read_bytes length={length}, data={data}")
        return data

    def transfer2(self, data: List[int]) -> List[int]:
        """SPI transfer with CS held active between bytes."""
        resp = self.spi.xfer2(data)
        self._log(f"[DEBUG] SPI transfer2 sent={data}, recv={resp}")
        return resp

    def release(self) -> None:
        """Close the SPI device."""
        self.spi.close()
        self._log(f"[INFO] Closed SPI /dev/spidev{self.bus}.{self.device}")


# --- Hardware PWM via GPIO hardware channels ---
class RPiHardwarePWM_API(ABC):
    """Abstract interface for hardware PWM outputs."""

    @abstractmethod
    def set_duty_cycle(self, duty_cycle: float) -> None:
        pass

    @abstractmethod
    def set_frequency(self, frequency: float) -> None:
        pass

    @abstractmethod
    def enable_logging(self) -> None:
        pass

    @abstractmethod
    def disable_logging(self) -> None:
        pass


class RPiHardwarePWM(LoggingMixin, ResourceMixin, RPiHardwarePWM_API):
    """
    Hardware PWM via RPi.GPIO on supported pins.
    """

    def __init__(
        self,
        pin: int,
        frequency: float = 1000.0,
        logger: Optional[logging.Logger] = None,
        logging_enabled: bool = True,
    ) -> None:
        super().__init__(logger, logging_enabled)
        self.pin = pin
        self.frequency = frequency
        self._pwm: Optional[GPIO.PWM] = None

    def get_required_resources(self) -> Dict[str, List[int]]:
        return {"pins": [self.pin]}

    def initialize(self) -> None:
        """Start hardware PWM on pin."""
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT)
        self._pwm = GPIO.PWM(self.pin, self.frequency)
        self._pwm.start(0)
        self._log(f"[INFO] Hardware PWM started on pin {self.pin} at {self.frequency}Hz")

    def set_duty_cycle(self, duty_cycle: float) -> None:
        """Adjust hardware PWM duty cycle."""
        self._pwm.ChangeDutyCycle(duty_cycle)
        self._log(f"[DEBUG] Hardware PWM duty_cycle set to {duty_cycle}% on pin {self.pin}")

    def set_frequency(self, frequency: float) -> None:
        """Adjust hardware PWM frequency."""
        self._pwm.ChangeFrequency(frequency)
        self._log(f"[DEBUG] Hardware PWM frequency set to {frequency}Hz on pin {self.pin}")

    def release(self) -> None:
        """Stop hardware PWM and clean up."""
        if self._pwm:
            self._pwm.stop()
        GPIO.cleanup(self.pin)
        self._log(f"[DEBUG] [INFO] Hardware PWM stopped and cleaned up pin {self.pin}")


class RPiOneWire_API(ABC):
    @abstractmethod
    def scan_devices(self) -> List[str]:
        pass

    @abstractmethod
    def read_temperature(self, device_id: str) -> float:
        pass

    @abstractmethod
    def get_required_resources(self) -> Dict[str, List[int]]:
        pass

    @abstractmethod
    def initialize(self) -> None:
        pass

    @abstractmethod
    def release(self) -> None:
        pass

    @abstractmethod
    def enable_logging(self) -> None:
        pass

    @abstractmethod
    def disable_logging(self) -> None:
        pass


class RPiOneWire(LoggingMixin, ResourceMixin, RPiOneWire_API):
    """
    Full user-space 1-Wire support used for DS18B20 tests.
    """

    BASE_PATH = "/sys/bus/w1/devices"
    DEFAULT_PIN = 4  # default w1-gpio pin

    def __init__(
        self,
        pin: int = DEFAULT_PIN,
        logger: Optional[logging.Logger] = None,
        logging_enabled: bool = True,
    ) -> None:
        super().__init__(logger, logging_enabled)
        self.pin = pin

    def get_required_resources(self) -> Dict[str, List[int]]:
        return {"pins": [self.pin]}

    def initialize(self) -> None:
        # Kernel driver handles actual init.
        self._log(f"[INFO] 1-Wire initialized on GPIO{self.pin}")

    # ==============================
    #     DEVICE SCANNING
    # ==============================
    def scan_devices(self) -> List[str]:
        """
        Return list of device IDs (e.g. "28-0001...").
        """
        paths = glob.glob(f"{self.BASE_PATH}/28-*")
        devices = [p.split("/")[-1] for p in paths]
        self._log(f"[DEBUG] 1-Wire found devices: {devices}")
        return devices

    # ==============================
    #   TEMPERATURE READING (DS18B20)
    # ==============================
    def read_temperature(self, device_id: str) -> float:
        """
        Read temperature from DS18B20 via w1_slave format.
        """
        slave_path = f"{self.BASE_PATH}/{device_id}/w1_slave"

        try:
            with open(slave_path, "r") as f:
                lines = f.readlines()
        except FileNotFoundError:
            raise FileNotFoundError(f"Device {device_id} not found")

        # Look for t=<value> in second line
        for line in lines:
            if "t=" in line:
                temp_milli = int(line.split("t=")[1].strip())
                temp_c = temp_milli / 1000.0
                self._log(f"1-Wire {device_id} temperature: {temp_c:.3f} °C")
                return temp_c

        raise ValueError("Invalid w1_slave format: temperature not found")

    def release(self) -> None:
        # No cleanup required
        self._log("[INFO] 1-Wire released")


GPIO_LABEL_CONSTANTS: Dict[str, str] = {}
HIGH = "HIGH"
LOW = "LOW"
high = HIGH
low = LOW


def _sanitize_label_constant(name: str) -> Optional[str]:
    cleaned = re.sub(r"[^0-9a-zA-Z_]+", "_", name.strip())
    cleaned = re.sub(r"__+", "_", cleaned).strip("_")
    if not cleaned:
        return None
    if cleaned[0].isdigit():
        cleaned = f"PIN_{cleaned}"
    return cleaned.upper()


def register_gpio_label_constants(pin_config: Dict[int, Dict[str, Any]]) -> None:
    """Expose GPIO labels as module-level constants for test ergonomics."""

    global GPIO_LABEL_CONSTANTS
    GPIO_LABEL_CONSTANTS = {}

    for cfg in pin_config.values():
        name = cfg.get("name")
        if not isinstance(name, str) or not name.strip():
            continue

        ident = _sanitize_label_constant(name)
        if not ident or ident in GPIO_LABEL_CONSTANTS:
            continue

        GPIO_LABEL_CONSTANTS[ident] = name
        globals()[ident] = name
