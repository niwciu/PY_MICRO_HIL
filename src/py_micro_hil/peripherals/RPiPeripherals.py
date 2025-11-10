import sys
from py_micro_hil.utils.system import is_raspberry_pi

ON_RPI = is_raspberry_pi()

if not ON_RPI:
    from py_micro_hil.peripherals import dummyRPiPeripherals as mock
    sys.modules["RPi.GPIO"] = mock.GPIO
    sys.modules["spidev"] = mock.spidev
    sys.modules["smbus2"] = type("smbus2", (), {"SMBus": mock.SMBus})
    sys.modules["serial"] = mock.serial

import RPi.GPIO as GPIO
import spidev
import serial
from smbus2 import SMBus

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union


# Mixins for logging and resource management
class LoggingMixin:
    """
    Mixin providing enable/disable logging and an internal _log helper.
    """
    def __init__(self, logger: Optional[logging.Logger] = None,
                 logging_enabled: bool = True) -> None:
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
            # nasz Logger.log(msg, to_console=False, to_log_file=False)
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
    def write(self, pin: int, value: int) -> None:
        pass

    @abstractmethod
    def read(self, pin: int) -> int:
        pass

    @abstractmethod
    def toggle(self, pin: int) -> None:
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
    def __init__(self,
                 pin_config: Dict[int, Dict[str, Any]],
                 logger: Optional[logging.Logger] = None,
                 logging_enabled: bool = True) -> None:
        super().__init__(logger, logging_enabled)
        self._pin_config = pin_config

    def get_required_resources(self) -> Dict[str, List[int]]:
        return {"pins": list(self._pin_config.keys())}

    def initialize(self) -> None:
        """Configure all GPIO pins according to pin_config."""
        GPIO.setmode(GPIO.BCM)
        for pin, cfg in self._pin_config.items():
            mode = cfg.get('mode', GPIO.IN)
            initial = cfg.get('initial')
            if mode == GPIO.OUT:
                if initial is not None:
                    GPIO.setup(pin, GPIO.OUT, initial=initial)
                else:
                    GPIO.setup(pin, GPIO.OUT)
                self._log(f"Initialized OUTPUT pin {pin}")
            else:
                GPIO.setup(pin, GPIO.IN)
                self._log(f"Initialized INPUT pin {pin}")

    def write(self, pin: int, value: int) -> None:
        """Set digital output value on a pin."""
        GPIO.output(pin, value)
        self._log(f"Wrote value {value} to pin {pin}")

    def read(self, pin: int) -> int:
        """Read digital input value from a pin."""
        val = GPIO.input(pin)
        self._log(f"Read value {val} from pin {pin}")
        return val

    def toggle(self, pin: int) -> None:
        """Toggle digital output on a pin."""
        current = GPIO.input(pin)
        GPIO.output(pin, not current)
        self._log(f"Toggled pin {pin} to {not current}")

    def release(self) -> None:
        """Clean up all configured GPIO pins."""
        for pin in self._pin_config:
            GPIO.cleanup(pin)
            self._log(f"Cleaned up pin {pin}")
    def get_gpio_interface():
        """  Returns GPIO interface.    """
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
    def __init__(self,
                 pin: int,
                 frequency: float = 1000.0,
                 logger: Optional[logging.Logger] = None,
                 logging_enabled: bool = True) -> None:
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
        self._log(f"Started PWM on pin {self.pin} at {self.frequency}Hz")

    def set_duty_cycle(self, duty_cycle: float) -> None:
        """Change PWM duty cycle (0-100)."""
        if not 0 <= duty_cycle <= 100:
            raise ValueError("Duty cycle must be 0-100%")
        self._pwm.ChangeDutyCycle(duty_cycle)
        self._log(f"Duty cycle set to {duty_cycle}% on pin {self.pin}")

    def set_frequency(self, frequency: float) -> None:
        """Change PWM frequency."""
        if frequency <= 0:
            raise ValueError("Frequency must be > 0Hz")
        self._pwm.ChangeFrequency(frequency)
        self._log(f"Frequency changed to {frequency}Hz on pin {self.pin}")

    def release(self) -> None:
        """Stop PWM and clean up GPIO."""
        if self._pwm:
            self._pwm.stop()
        GPIO.cleanup(self.pin)
        self._log(f"Stopped PWM and cleaned up pin {self.pin}")


# --- UART ---
class RPiUART_API(ABC):
    """Abstract interface for UART serial communication."""
    @abstractmethod
    def initialize(self) -> None: pass

    @abstractmethod
    def send(self, data: Union[str, bytes]) -> None: pass

    @abstractmethod
    def receive(self, size: int = 1) -> bytes: pass

    @abstractmethod
    def readline(self) -> bytes: pass

    @abstractmethod
    def release(self) -> None: pass
class RPiUART(LoggingMixin, ResourceMixin, RPiUART_API):
    """
    UART interface using pyserial on Raspberry Pi.
    """
    def __init__(self,
                 port: str = '/dev/serial0',
                 baudrate: int = 9600,
                 timeout: float = 1.0,
                 parity: Any = serial.PARITY_NONE,
                 stopbits: Any = serial.STOPBITS_ONE,
                 logger: Optional[logging.Logger] = None,
                 logging_enabled: bool = True) -> None:
        super().__init__(logger, logging_enabled)
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.parity = parity
        self.stopbits = stopbits
        self._serial: Optional[serial.Serial] = None

    def get_required_resources(self) -> Dict[str, List[Union[int, str]]]:
        return {"pins": [14, 15], "ports": [self.port]}

    def initialize(self) -> None:
        """Open serial port for UART communication."""
        self._serial = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout,
            parity=self.parity,
            stopbits=self.stopbits
        )
        self._log(f"Initialized UART on {self.port} at {self.baudrate}bps")

    def get_initialized_params(self) -> Dict[str, Any]:
        """
        Return the UART configuration parameters after initialization.
        """
        return {
            "port": self.port,
            "baudrate": self.baudrate,
            "timeout": self.timeout,
            "parity": self.parity,
            "stopbits": self.stopbits
        }

    def send(self, data: Union[str, bytes]) -> None:
        """Send bytes or string over UART."""
        if isinstance(data, str):
            data = data.encode()
        self._serial.write(data)
        self._log(f"Sent {data} over UART")

    def receive(self, size: int = 1) -> bytes:
        """Read a fixed number of bytes from UART."""
        data = self._serial.read(size)
        self._log(f"Received {data} from UART")
        return data

    def readline(self) -> bytes:
        """Read until newline from UART."""
        line = self._serial.readline()
        self._log(f"Read line {line} from UART")
        return line

    def release(self) -> None:
        """Close UART serial port."""
        if self._serial:
            self._serial.close()
            self._log(f"Closed UART on {self.port}")



# --- I2C ---
class RPiI2C_API(ABC):
    """Abstract interface for I2C communication."""
    @abstractmethod
    def scan(self) -> List[int]: pass
    @abstractmethod
    def read(self, address: int, register: int, length: int) -> List[int]: pass
    @abstractmethod
    def write(self, address: int, register: int, data: List[int]) -> None: pass
    @abstractmethod
    def read_byte(self, address: int) -> int: pass
    @abstractmethod
    def write_byte(self, address: int, value: int) -> None: pass
    @abstractmethod
    def read_word(self, address: int, register: int) -> int: pass
    @abstractmethod
    def write_word(self, address: int, register: int, value: int) -> None: pass
    @abstractmethod
    def enable_logging(self) -> None: pass
    @abstractmethod
    def disable_logging(self) -> None: pass
class RPiI2C(LoggingMixin, ResourceMixin, RPiI2C_API):
    """
    I2C interface using smbus2.
    """
    def __init__(self,
                 bus_number: int = 1,
                 frequency: int = 100000,
                 logger: Optional[logging.Logger] = None,
                 logging_enabled: bool = True) -> None:
        super().__init__(logger, logging_enabled)
        if bus_number not in (0, 1):
            raise ValueError("I2C bus must be 0 or 1")
        self.bus_number = bus_number
        self.frequency = frequency
        self.bus: Optional[SMBus] = None

    def get_required_resources(self) -> Dict[str, List[Union[int,str]]]:
        return {"pins": [2,3] if self.bus_number==1 else [0,1],
                "ports": [f"/dev/i2c-{self.bus_number}"]}

    def initialize(self) -> None:
        """Open I2C bus."""
        self.bus = SMBus(self.bus_number)
        self._log(f"Initialized I2C bus {self.bus_number} at {self.frequency}Hz")
    
    def get_initialized_params(self) -> Dict[str, Any]:
        """
        Return the I2C configuration parameters after initialization.
        """
        return {
            "bus_number": self.bus_number,
            "frequency": self.frequency
        }
    
    def scan(self) -> List[int]:
        """Scan for I2C devices."""
        devices: List[int] = []
        for addr in range(0x08, 0x78):
            try:
                self.bus.write_quick(addr)
                devices.append(addr)
            except Exception:
                pass
        self._log(f"I2C scan found {devices}")
        return devices

    def read(self, address: int, register: int, length: int) -> List[int]:
        """Read block data from I2C device."""
        data = self.bus.read_i2c_block_data(address, register, length)
        self._log(f"I2C read from 0x{address:02X}, reg 0x{register:02X}: {data}")
        return data

    def write(self, address: int, register: int, data: List[int]) -> None:
        """Write block data to I2C device."""
        self.bus.write_i2c_block_data(address, register, data)
        self._log(f"I2C write to 0x{address:02X}, reg 0x{register:02X}: {data}")

    def read_byte(self, address: int) -> int:
        """Read single byte from I2C device."""
        val = self.bus.read_byte(address)
        self._log(f"I2C read_byte from 0x{address:02X}: 0x{val:02X}")
        return val

    def write_byte(self, address: int, value: int) -> None:
        """Write single byte to I2C device."""
        self.bus.write_byte(address, value)
        self._log(f"I2C write_byte to 0x{address:02X}: 0x{value:02X}")

    def read_word(self, address: int, register: int) -> int:
        """Read word (2 bytes) from I2C device."""
        val = self.bus.read_word_data(address, register)
        self._log(f"I2C read_word from 0x{address:02X}, reg 0x{register:02X}: 0x{val:04X}")
        return val

    def write_word(self, address: int, register: int, value: int) -> None:
        """Write word (2 bytes) to I2C device."""
        self.bus.write_word_data(address, register, value)
        self._log(f"I2C write_word to 0x{address:02X}, reg 0x{register:02X}: 0x{value:04X}")

    def release(self) -> None:
        """Close I2C bus."""
        self.bus.close()
        self._log(f"Closed I2C bus {self.bus_number}")


# --- SPI ---
class RPiSPI_API(ABC):
    """Abstract interface for SPI communication."""
    @abstractmethod
    def transfer(self, data: List[int]) -> List[int]: pass
    @abstractmethod
    def transfer_bytes(self, data: bytes) -> bytes: pass
    @abstractmethod
    def write_bytes(self, data: List[int]) -> None: pass
    @abstractmethod
    def read_bytes(self, length: int) -> List[int]: pass
    @abstractmethod
    def transfer2(self, data: List[int]) -> List[int]: pass
    @abstractmethod
    def enable_logging(self) -> None: pass
    @abstractmethod
    def disable_logging(self) -> None: pass
class RPiSPI(LoggingMixin, ResourceMixin, RPiSPI_API):
    """
    SPI interface using spidev.
    """
    def __init__(self,
                 bus: int = 0,
                 device: int = 0,
                 max_speed_hz: int = 500000,
                 mode: int = 0,
                 bits_per_word: int = 8,
                 cs_high: bool = False,
                 lsbfirst: bool = False,
                 logger: Optional[logging.Logger] = None,
                 logging_enabled: bool = True) -> None:
        super().__init__(logger, logging_enabled)
        self.bus = bus
        self.device = device
        self.max_speed_hz = max_speed_hz
        self.mode = mode
        self.bits_per_word = bits_per_word
        self.cs_high = cs_high
        self.lsbfirst = lsbfirst
        self.spi = spidev.SpiDev()

    def get_required_resources(self) -> Dict[str, List[Union[int,str]]]:
        return {"ports": [f"/dev/spidev{self.bus}.{self.device}"]}

    def initialize(self) -> None:
        """Open SPI bus and apply settings."""
        self.spi.open(self.bus, self.device)
        self.spi.max_speed_hz = self.max_speed_hz
        self.spi.mode = self.mode
        self.spi.bits_per_word = self.bits_per_word
        self.spi.cshigh = self.cs_high
        self.spi.lsbfirst = self.lsbfirst
        self._log(f"Initialized SPI /dev/spidev{self.bus}.{self.device} @ {self.max_speed_hz}Hz")

    def get_initialized_params(self) -> Dict[str, Any]:
        """
        Return the SPI configuration parameters after initialization.
        """
        return {
            "bus": self.bus,
            "device": self.device,
            "max_speed_hz": self.max_speed_hz,
            "mode": self.mode,
            "bits_per_word": self.bits_per_word,
            "cs_high": self.cs_high,
            "lsbfirst": self.lsbfirst
        }
    
    def transfer(self, data: List[int]) -> List[int]:
        """Full-duplex SPI transfer (list of ints)."""
        resp = self.spi.xfer(data)
        self._log(f"SPI transfer sent={data}, recv={resp}")
        return resp

    def transfer_bytes(self, data: bytes) -> bytes:
        """Full-duplex SPI transfer (bytes)."""
        resp = bytes(self.spi.xfer(list(data)))
        self._log(f"SPI transfer_bytes sent={list(data)}, recv={list(resp)}")
        return resp

    def write_bytes(self, data: List[int]) -> None:
        """Write-only SPI transaction."""
        self.spi.writebytes(data)
        self._log(f"SPI write_bytes data={data}")

    def read_bytes(self, length: int) -> List[int]:
        """Read-only SPI transaction."""
        data = self.spi.readbytes(length)
        self._log(f"SPI read_bytes length={length}, data={data}")
        return data

    def transfer2(self, data: List[int]) -> List[int]:
        """SPI transfer with CS held active between bytes."""
        resp = self.spi.xfer2(data)
        self._log(f"SPI transfer2 sent={data}, recv={resp}")
        return resp

    def release(self) -> None:
        """Close SPI device."""
        self.spi.close()
        self._log(f"Closed SPI /dev/spidev{self.bus}.{self.device}")


# --- 1-Wire ---
# class RPi1Wire_API(ABC):
#     """Abstract interface for 1-Wire bus via sysfs."""
#     @abstractmethod
#     def list_devices(self) -> List[str]: pass
#     @abstractmethod
#     def read_device(self, device_id: str, filename: str = 'w1_slave') -> str: pass
#     @abstractmethod
#     def read_temperature(self, device_id: Optional[str] = None) -> float: pass
#     @abstractmethod
#     def reset_bus(self) -> None: pass
#     @abstractmethod
#     def release(self) -> None: pass
#     @abstractmethod
#     def enable_logging(self) -> None: pass
#     @abstractmethod
#     def disable_logging(self) -> None: pass
# class RPi1Wire(LoggingMixin, ResourceMixin, RPi1Wire_API):
#     """
#     1-Wire interface via Linux sysfs (e.g., DS18B20 sensors).
#     If kernel modules are not present, initialization will raise RuntimeError,
#     but this device is optional in our framework.
#     """
#     optional = True
#     def __init__(self,
#                  pin: int,
#                  logger: Optional[logging.Logger] = None,
#                  logging_enabled: bool = True) -> None:
#         super().__init__(logger, logging_enabled)
#         self.pin = pin
#         self.device_files: List[str] = []

#     def get_required_resources(self) -> Dict[str, List[int]]:
#         return {"pins": [self.pin]}

#     def initialize(self) -> None:
#             """Scan for 1-Wire devices under /sys/bus/w1/devices/ without calling modprobe."""
#             base = '/sys/bus/w1/devices/'

#             # Jeżeli nie ma katalogu, oznacza to, że one-wire nie jest włączony w kernelu
#             if not os.path.isdir(base):
#                 raise RuntimeError(
#                     "1-Wire sysfs interface not found. "
#                     "Upewnij się, że w kernelu włączono one-wire "
#                     "(np. dodając 'dtoverlay=w1-gpio' do /boot/config.txt)."
#                 )

#             # Skanujemy czujniki DS18B20 - katalogi zaczynające się od "28-"
#             self.device_files = glob.glob(f"{base}28*")

#             if not self.device_files:
#                 # Nie wykryto żadnych sensorów
#                 self._log(
#                     "Brak urządzeń 1-Wire w sysfs. "
#                     "Sprawdź okablowanie i konfigurację dtoverlay w /boot/config.txt.",
#                     level=logging.WARNING
#                 )
#             else:
#                 self._log(f"1-Wire devices found: {self.device_files}")

#     def get_initialized_params(self) -> Dict[str, Any]:
#         """
#         Return pin and list of discovered 1-Wire device IDs.
#         """
#         return {
#             "pin": self.pin,
#             "devices": [Path(d).name for d in self.device_files]
#         }
    
#     def list_devices(self) -> List[str]:
#         """Return list of attached 1-Wire device IDs."""
#         ids=[]
#         for d in self.device_files:
#             ids.append(d.split('/')[-1])
#         self._log(f"1-Wire list_devices={ids}")
#         return ids

#     def read_device(self, device_id: str, filename: str='w1_slave') -> str:
#         """Read raw contents of a 1-Wire device file."""
#         path=f"/sys/bus/w1/devices/{device_id}/{filename}"
#         with open(path,'r') as f: data=f.read()
#         self._log(f"1-Wire read {path}")
#         return data

#     def read_temperature(self, device_id: Optional[str]=None) -> float:
#         """Parse temperature reading from DS18B20."""
#         if device_id is None: device_id=self.list_devices()[0]
#         raw=self.read_device(device_id)
#         lines=raw.splitlines()
#         if not lines[0].endswith('YES'): raise IOError('CRC check failed')
#         temp=int(lines[1].split('t=')[-1])/1000.0
#         self._log(f"1-Wire temp={temp}C for {device_id}")
#         return temp

#     def reset_bus(self) -> None:
#         """Reload 1-Wire kernel modules."""
#         subprocess.run(['modprobe','-r','w1-gpio'],check=True)
#         subprocess.run(['modprobe','w1-gpio'],check=True)
#         self._log("1-Wire bus reset")

#     def release(self) -> None:
#         """Cleanup GPIO and unload modules."""
#         GPIO.cleanup(self.pin)
#         subprocess.run(['modprobe','-r','w1-gpio'],check=True)
#         subprocess.run(['modprobe','-r','w1-therm'],check=True)
#         self._log("1-Wire released")


# # --- ADC (MCP3008) via SPI---
# class RPiADC_API(ABC):
#     """Abstract interface for ADC reading."""
#     @abstractmethod
#     def initialize(self) -> None: pass
#     @abstractmethod
#     def read(self) -> int: pass
#     @abstractmethod
#     def read_all_channels(self) -> List[int]: pass
#     @abstractmethod
#     def release(self) -> None: pass
#     @abstractmethod
#     def enable_logging(self) -> None: pass
#     @abstractmethod
#     def disable_logging(self) -> None: pass

# class RPiADC(LoggingMixin, ResourceMixin, RPiADC_API):
#     """
#     10-bit ADC (e.g., MCP3008) over SPI.
#     """
#     def __init__(self,
#                  channel: int=0,
#                  logger: Optional[logging.Logger]=None,
#                  logging_enabled: bool=True) -> None:
#         super().__init__(logger, logging_enabled)
#         if channel not in range(8): raise ValueError("Channel 0-7")
#         self.channel=channel
#         self.spi=spidev.SpiDev()

#     def initialize(self) -> None:
#         """Open SPI for ADC."""
#         self.spi.open(0,0)
#         self.spi.max_speed_hz=1350000
#         self._log(f"ADC initialized channel={self.channel}")
#     def get_required_resources(self) -> Dict[str, Any]:
#         """
#         Return the ADC channel and SPI speed that were initialized.
#         """
#         return {
#             "channel": self.channel,
#             "max_speed_hz": self.spi.max_speed_hz,
#             "pins" : self
#         }
#     def read(self) -> int:
#         """Read single channel value (0-1023)."""
#         resp=self.spi.xfer2([1,(8+self.channel)<<4,0])
#         val=((resp[1]&3)<<8)|resp[2]
#         self._log(f"ADC read channel={self.channel}, value={val}")
#         return val

#     def read_all_channels(self) -> List[int]:
#         """Read all 8 channels."""
#         vals=[]
#         for ch in range(8):
#             resp=self.spi.xfer2([1,(8+ch)<<4,0])
#             vals.append(((resp[1]&3)<<8)|resp[2])
#         self._log(f"ADC all channels={vals}")
#         return vals

#     def release(self) -> None:
#         """Close SPI ADC."""
#         self.spi.close()
#         self._log("ADC released")


# # --- CAN via SocketCAN ---
# class RPiCAN_API(ABC):
#     """Abstract interface for CAN bus messaging."""
#     @abstractmethod
#     def send_message(self, arbitration_id: int, data: Union[bytes,List[int]], extended_id: bool=False) -> None: pass
#     @abstractmethod
#     def receive_message(self, timeout: float=1.0) -> Optional[can.Message]: pass
#     @abstractmethod
#     def enable_logging(self) -> None: pass
#     @abstractmethod
#     def disable_logging(self) -> None: pass

# class RPiCAN(LoggingMixin, ResourceMixin, RPiCAN_API):
#     """
#     SocketCAN interface on Linux.
#     """
#     def __init__(self,
#                  interface: str='can0',
#                  bitrate: int=500000,
#                  logger: Optional[logging.Logger]=None,
#                  logging_enabled: bool=True) -> None:
#         super().__init__(logger, logging_enabled)
#         self.interface=interface
#         self.bitrate=bitrate
#         self.bus: Optional[can.Bus]=None
#     def get_required_resources(self) -> Dict[str, List[Any]]:
#         """
#         Return required resources: no GPIO pins, but network interface name.
#         """
#         return {
#             "pins": [],
#             "interfaces": [self.interface]
#         }

#     def initialize(self) -> None:
#         """Set up CAN interface and open bus."""
#         subprocess.run(['sudo','ip','link','set',self.interface,'up','type','can',f'bitrate={self.bitrate}'],check=True)
#         self.bus=can.interface.Bus(channel=self.interface,bustype='socketcan')
#         self._log(f"CAN initialized {self.interface}@{self.bitrate}")

#     def get_initialized_params(self) -> Dict[str, Any]:
#         """
#         Return the CAN interface and bitrate that were initialized.
#         """
#         return {
#             "interface": self.interface,
#             "bitrate": self.bitrate
#         }

#     def send_message(self, arbitration_id: int, data: Union[bytes,List[int]], extended_id: bool=False) -> None:
#         """Send a CAN message."""
#         if isinstance(data,list): data=bytes(data)
#         msg=can.Message(arbitration_id=arbitration_id,data=data,is_extended_id=extended_id)
#         self.bus.send(msg)
#         self._log(f"CAN send id={arbitration_id}, data={data}")

#     def receive_message(self, timeout: float=1.0) -> Optional[can.Message]:
#         """Receive a CAN message with timeout."""
#         msg=self.bus.recv(timeout)
#         self._log(f"CAN received {msg}")
#         return msg

#     def release(self) -> None:
#         """Shutdown CAN bus and lower interface."""
#         if self.bus:
#             self.bus.shutdown()
#         subprocess.run(['sudo','ip','link','set',self.interface,'down'],check=True)
#         self._log(f"CAN released {self.interface}")


# --- Hardware PWM via GPIO hardware channels ---
class RPiHardwarePWM_API(ABC):
    """Abstract interface for hardware PWM outputs."""
    @abstractmethod
    def set_duty_cycle(self, duty_cycle: float) -> None: pass
    @abstractmethod
    def set_frequency(self, frequency: float) -> None: pass
    @abstractmethod
    def enable_logging(self) -> None: pass
    @abstractmethod
    def disable_logging(self) -> None: pass

class RPiHardwarePWM(LoggingMixin, ResourceMixin, RPiHardwarePWM_API):
    """
    Hardware PWM via RPi.GPIO on supported pins.
    """
    def __init__(self,
                 pin: int,
                 frequency: float = 1000.0,
                 logger: Optional[logging.Logger]=None,
                 logging_enabled: bool=True) -> None:
        super().__init__(logger, logging_enabled)
        self.pin=pin
        self.frequency=frequency
        self._pwm: Optional[GPIO.PWM]=None

    def get_required_resources(self) -> Dict[str,List[int]]:
        return {"pins":[self.pin]}

    def initialize(self) -> None:
        """Start hardware PWM on pin."""
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin,GPIO.OUT)
        self._pwm=GPIO.PWM(self.pin,self.frequency)
        self._pwm.start(0)
        self._log(f"Hardware PWM started on pin {self.pin} at {self.frequency}Hz")

    def set_duty_cycle(self,duty_cycle:float)->None:
        """Adjust hardware PWM duty cycle."""
        self._pwm.ChangeDutyCycle(duty_cycle)
        self._log(f"Hardware PWM duty_cycle set to {duty_cycle}% on pin {self.pin}")

    def set_frequency(self,frequency:float)->None:
        """Adjust hardware PWM frequency."""
        self._pwm.ChangeFrequency(frequency)
        self._log(f"Hardware PWM frequency set to {frequency}Hz on pin {self.pin}")

    def release(self)->None:
        """Stop hardware PWM and clean up."""
        if self._pwm: self._pwm.stop()
        GPIO.cleanup(self.pin)
        self._log(f"Hardware PWM stopped and cleaned up pin {self.pin}")
