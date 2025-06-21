import RPi.GPIO as GPIO
from smbus2 import SMBus
import spidev
import serial
import os
from abc import ABC, abstractmethod
import glob
import time
import can
from typing import List, Dict

class RPiGPIO_API(ABC):
    @abstractmethod
    def write(self, pin, value):
        pass
    
    @abstractmethod
    def read(self, pin):
        pass

    @abstractmethod
    def toggle(self, pin):
        pass

    @abstractmethod
    def enable_logging(self):
        pass

    @abstractmethod
    def disable_logging(self):
        pass

class RPiGPIO(RPiGPIO_API):
    def __init__(self, pin_config, logger=None, logging_enabled=True):
        """
        :param pin_config: {pin: {'mode': GPIO.OUT/IN, 'initial': GPIO.LOW/HIGH}}
        """
        self._pin_config = pin_config
        self._logger = logger
        self._logging_enabled = logging_enabled

    def get_required_resources(self):
        return {"pins": list(self._pin_config.keys())}

    def initialize(self):
        GPIO.setmode(GPIO.BCM)
        for pin, config in self._pin_config.items():
            if config['mode'] == GPIO.OUT:
                GPIO.setup(pin, GPIO.OUT, initial=config.get('initial', GPIO.LOW))
                self._log(f"[INFO] GPIO pin {pin} set as OUTPUT.")
            else:
                GPIO.setup(pin, GPIO.IN)
                self._log(f"[INFO] GPIO pin {pin} set as INPUT.")

    def write(self, pin, value):
        GPIO.output(pin, value)
        self._log(f"[INFO] Written {value} to GPIO pin {pin}.")

    def read(self, pin):
        value = GPIO.input(pin)
        self._log(f"[INFO] Read value {value} from GPIO pin {pin}.")
        return value

    def toggle(self, pin):
        current = GPIO.input(pin)
        GPIO.output(pin, not current)
        self._log(f"[INFO] Toggled GPIO pin {pin} to {not current}.")

    def release(self):
        for pin in self._pin_config:
            GPIO.cleanup(pin)
            self._log(f"[INFO] GPIO pin {pin} released.")

    def enable_logging(self):
        self._logging_enabled = True

    def disable_logging(self):
        self._logging_enabled = False

    def _log(self, message):
        if self._logging_enabled and self._logger:
            self._logger.log(message)

class RPiPWM_API(ABC):
    @abstractmethod
    def set_duty_cycle(self, duty_cycle):
        pass
    
    @abstractmethod
    def set_frequency(self, frequency):
        pass

    @abstractmethod
    def enable_logging(self):
        pass

    @abstractmethod
    def disable_logging(self):
        pass

class RPiPWM(RPiPWM_API):
    def __init__(self, pin, frequency=1000, logger=None, logging_enabled=True):
        self.pin = pin
        self.frequency = frequency
        self.pwm = None
        self.logger = logger
        self.logging_enabled = logging_enabled

    def get_required_resources(self):
        return {"pins": [self.pin]}

    def initialize(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT)
        self.pwm = GPIO.PWM(self.pin, self.frequency)
        self.pwm.start(0)
        self._log(f"[INFO] Started PWM on pin {self.pin} with frequency {self.frequency} Hz.")

    def set_duty_cycle(self, duty_cycle):
        if self.pwm:
            self.pwm.ChangeDutyCycle(duty_cycle)
            self._log(f"[INFO] Set duty cycle to {duty_cycle}% on pin {self.pin}.")

    def set_frequency(self, frequency):
        if self.pwm:
            self.pwm.ChangeFrequency(frequency)
            self._log(f"[INFO] Changed frequency to {frequency} Hz on pin {self.pin}.")

    def release(self):
        if self.pwm:
            self.pwm.stop()
            self._log(f"[INFO] Stopped PWM on pin {self.pin}.")
        GPIO.cleanup(self.pin)
        self._log(f"[INFO] Released pin {self.pin}.")

    def enable_logging(self):
        self.logging_enabled = True

    def disable_logging(self):
        self.logging_enabled = False

    def _log(self, message):
        if self.logging_enabled and self.logger:
            self.logger.log(message)

class RPiUART_API(ABC):
    @abstractmethod
    def initialize(self):
        pass
    
    @abstractmethod
    def send(self, data):
        pass

    @abstractmethod
    def receive(self, size=1):
        pass
    
    @abstractmethod
    def readline(self):
        pass

    @abstractmethod
    def enable_logging(self):
        pass

    @abstractmethod
    def disable_logging(self):
        pass

class RPiUART(RPiUART_API):
    def __init__(self, port='/dev/serial0', baudrate=9600, timeout=1,
                 parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
                 logger=None, logging_enabled=True):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.parity = parity
        self.stopbits = stopbits
        self.serial = None
        self.reserved_pins = [14, 15]  # TXD, RXD
        self.logger = logger
        self.logging_enabled = logging_enabled

    def get_required_resources(self):
        return {"pins": self.reserved_pins, "ports": [self.port]}

    def initialize(self):
        self.serial = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout,
            parity=self.parity,
            stopbits=self.stopbits
        )
        self._log(f"[INFO] UART initialized on {self.port} with baudrate {self.baudrate}.")

    def send(self, data):
        if self.serial and self.serial.is_open:
            self.serial.write(data.encode() if isinstance(data, str) else data)
            self._log(f"[INFO] Sent data over UART: {data}")

    def receive(self, size=1):
        if self.serial and self.serial.is_open:
            data = self.serial.read(size)
            self._log(f"[INFO] Received data from UART: {data}")
            return data
        return b''

    def readline(self):
        if self.serial and self.serial.is_open:
            line = self.serial.readline()
            self._log(f"[INFO] Read line from UART: {line}")
            return line
        return b''

    def release(self):
        if self.serial and self.serial.is_open:
            self.serial.close()
            self._log(f"[INFO] UART on port {self.port} closed.")

    def get_initialized_params(self):
        return {
            "port": self.port,
            "baudrate": self.baudrate,
            "stopbits": self.stopbits,
            "parity": self.parity,
            "timeout": self.timeout
        }

    def enable_logging(self):
        self.logging_enabled = True

    def disable_logging(self):
        self.logging_enabled = False

    def _log(self, message):
        if self.logging_enabled and self.logger:
            self.logger.log(message)


class RPiI2C_API(ABC):

    @abstractmethod
    def scan(self) -> list[int]:
        """Skanuje magistralę w poszukiwaniu urządzeń I2C."""
        pass

    @abstractmethod
    def read(self, address: int, register: int, length: int) -> list[int]:
        """Odczytuje blok danych z urządzenia I2C."""
        pass

    @abstractmethod
    def write(self, address: int, register: int, data: list[int]) -> None:
        """Wysyła blok danych do urządzenia I2C."""
        pass

    @abstractmethod
    def read_byte(self, address: int) -> int:
        """Odczytuje pojedynczy bajt z urządzenia I2C."""
        pass

    @abstractmethod
    def write_byte(self, address: int, value: int) -> None:
        """Wysyła pojedynczy bajt do urządzenia I2C."""
        pass

    @abstractmethod
    def read_word(self, address: int, register: int) -> int:
        """Odczytuje słowo (2 bajty) z urządzenia I2C."""
        pass

    @abstractmethod
    def write_word(self, address: int, register: int, value: int) -> None:
        """Zapisuje słowo (2 bajty) do urządzenia I2C."""
        pass

    @abstractmethod
    def enable_logging(self):
        pass

    @abstractmethod
    def disable_logging(self):
        pass

class RPiI2C(RPiI2C_API):
    def __init__(self, bus: int = 1, frequency: int = 100000):
        """
        Klasa do obsługi magistrali I2C.
        :param bus: Numer magistrali I2C (0 lub 1).
        :param frequency: Częstotliwość magistrali (tylko informacyjnie).
        """
        self.bus_number = bus
        self.frequency = frequency
        self.bus: SMBus | None = None

        # Przypisanie pinów zależnie od magistrali
        if self.bus_number == 1:
            self.reserved_pins = [2, 3]  # SDA, SCL
        elif self.bus_number == 0:
            self.reserved_pins = [0, 1]  # SDA, SCL
        else:
            raise ValueError(f"Invalid bus number: {self.bus_number}. Only 0 and 1 are supported.")

    def get_required_resources(self) -> dict:
        """
        Zwraca wymagane zasoby sprzętowe: piny GPIO i interfejs systemowy.
        """
        return {
            "pins": self.reserved_pins,
            "ports": [f"/dev/i2c-{self.bus_number}"]
        }

    def get_initialized_params(self) -> dict:
        """
        Zwraca parametry konfiguracyjne po inicjalizacji magistrali.
        """
        return {
            "bus": f"I2C{self.bus_number}",
            "frequency": self.frequency
        }

    def initialize(self) -> None:
        """
        Inicjalizuje magistralę I2C poprzez otwarcie odpowiedniego urządzenia.
        """
        self.bus = SMBus(self.bus_number)

    def release(self) -> None:
        """
        Zamyka otwartą magistralę I2C.
        """
        if self.bus:
            self.bus.close()
            self.bus = None

    def read(self, address: int, register: int, length: int) -> list[int]:
        """
        Odczytuje blok danych z urządzenia I2C.
        :param address: Adres urządzenia.
        :param register: Rejestr początkowy.
        :param length: Liczba bajtów do odczytania.
        :return: Lista bajtów.
        """
        return self.bus.read_i2c_block_data(address, register, length)

    def write(self, address: int, register: int, data: list[int]) -> None:
        """
        Wysyła blok danych do urządzenia I2C.
        :param address: Adres urządzenia.
        :param register: Rejestr docelowy.
        :param data: Lista bajtów do wysłania.
        """
        self.bus.write_i2c_block_data(address, register, data)

    def scan(self) -> list[int]:
        """
        Skanuje magistralę w poszukiwaniu aktywnych urządzeń I2C.
        :return: Lista wykrytych adresów.
        """
        devices = []
        for address in range(0x08, 0x78):  # Zakres sensownych adresów
            try:
                self.bus.write_quick(address)
                devices.append(address)
            except Exception:
                continue
        return devices

    def write_byte(self, address: int, value: int) -> None:
        """
        Wysyła pojedynczy bajt do urządzenia I2C.
        :param address: Adres urządzenia.
        :param value: Bajt do wysłania.
        """
        self.bus.write_byte(address, value)

    def read_byte(self, address: int) -> int:
        """
        Odczytuje pojedynczy bajt z urządzenia I2C.
        :param address: Adres urządzenia.
        :return: Bajt odczytany.
        """
        return self.bus.read_byte(address)

    def read_word(self, address: int, register: int) -> int:
        """
        Odczytuje słowo (2 bajty) z określonego rejestru.
        :param address: Adres urządzenia.
        :param register: Rejestr do odczytu.
        :return: Słowo (2 bajty).
        """
        return self.bus.read_word_data(address, register)

    def write_word(self, address: int, register: int, value: int) -> None:
        """
        Zapisuje słowo (2 bajty) do określonego rejestru.
        :param address: Adres urządzenia.
        :param register: Rejestr docelowy.
        :param value: Wartość do zapisania.
        """
        self.bus.write_word_data(address, register, value)
    
    def enable_logging(self):
        self.logging_enabled = True

    def disable_logging(self):
        self.logging_enabled = False

    def _log(self, message):
        if self.logging_enabled and self.logger:
            self.logger.log(message)



class RPiSPI_API(ABC):
    @abstractmethod
    def transfer(self, data: List[int]) -> List[int]:
        """Przesyła dane przez SPI i odbiera odpowiedź."""
        pass

    @abstractmethod
    def transfer_bytes(self, data: bytes) -> bytes:
        """Przesyła dane jako bytes i odbiera odpowiedź jako bytes."""
        pass

    @abstractmethod
    def write_bytes(self, data: List[int]) -> None:
        """Wysyła dane bez oczekiwania odpowiedzi."""
        pass

    @abstractmethod
    def read_bytes(self, length: int) -> List[int]:
        """Odczytuje określoną liczbę bajtów z magistrali SPI."""
        pass

    @abstractmethod
    def transfer2(self, data: List[int]) -> List[int]:
        """Pełny transfer SPI z trzymaniem CS pomiędzy bajtami."""
        pass

    @abstractmethod
    def enable_logging(self):
        pass

    @abstractmethod
    def disable_logging(self):
        pass
    

class RPiSPI(RPiSPI_API):
    def __init__(
        self,
        bus: int = 0,
        device: int = 0,
        max_speed_hz: int = 50000,
        mode: int = 0,
        bits_per_word: int = 8,
        cs_high: bool = False,
        lsbfirst: bool = False,
        timeout: float = 1.0,
    ):
        # (jak wcześniej)
        ...

    def get_required_resources(self) -> dict:
        return {
            "pins": self.reserved_pins,
            "ports": [f"/dev/spidev{self.bus}.{self.device}"]
        }

    def get_initialized_params(self) -> dict:
        return {
            "device": f"spidev{self.bus}.{self.device}",
            "max_speed_hz": self.max_speed_hz,
            "mode": self.mode,
            "bits_per_word": self.bits_per_word,
            "cs_high": self.cs_high,
            "lsbfirst": self.lsbfirst
        }

    def initialize(self) -> None:
        self.spi.open(self.bus, self.device)
        self.spi.max_speed_hz = self.max_speed_hz
        self.spi.mode = self.mode
        self.spi.bits_per_word = self.bits_per_word
        self.spi.cshigh = self.cs_high
        self.spi.lsbfirst = self.lsbfirst

    def release(self) -> None:
        self.spi.close()

    def transfer(self, data: list[int]) -> list[int]:
        """
        Wysyła dane i odbiera odpowiedź z urządzenia SPI.
        :param data: Lista bajtów do wysłania.
        :return: Lista odebranych bajtów.
        """
        return self.spi.xfer(data)

    def transfer_bytes(self, data: bytes) -> bytes:
        """
        Wysyła dane w postaci bajtów i odbiera odpowiedź.
        :param data: Dane wejściowe jako bytes.
        :return: Odpowiedź również jako bytes.
        """
        return bytes(self.spi.xfer(list(data)))

    def write_bytes(self, data: list[int]) -> None:
        """
        Wysyła dane bez odbierania odpowiedzi.
        :param data: Lista bajtów do wysłania.
        """
        self.spi.writebytes(data)

    def read_bytes(self, length: int) -> list[int]:
        """
        Odczytuje określoną liczbę bajtów z magistrali SPI.
        :param length: Liczba bajtów do odczytu.
        :return: Odczytane bajty.
        """
        return self.spi.readbytes(length)

    def transfer2(self, data: list[int]) -> list[int]:
        """
        Wysyła dane i odbiera odpowiedź, trzymając CS między bajtami.
        :param data: Lista bajtów.
        :return: Lista odpowiedzi.
        """
        return self.spi.xfer2(data)
    
    def enable_logging(self):
        self.logging_enabled = True

    def disable_logging(self):
        self.logging_enabled = False

    def _log(self, message):
        if self.logging_enabled and self.logger:
            self.logger.log(message)


class RPi1Wire_API(ABC):
    @abstractmethod
    def list_devices(self):
        """Zwraca listę urządzeń 1-Wire podłączonych do magistrali."""
        pass

    @abstractmethod
    def read_device(self, device_id, filename='w1_slave'):
        """Odczytuje zawartość pliku urządzenia 1-Wire."""
        pass

    @abstractmethod
    def read_temperature(self, device_id=None):
        """Odczytuje temperaturę z urządzenia DS18B20 lub innego."""
        pass

    @abstractmethod
    def reset_bus(self):
        """Resetuje magistralę 1-Wire."""
        pass

    @abstractmethod
    def write_byte(self, device_id, value):
        """Wysyła bajt do urządzenia 1-Wire (opcjonalne)."""
        pass

    @abstractmethod
    def enable_logging(self):
        pass

    @abstractmethod
    def disable_logging(self):
        pass


class RPi1Wire(RPi1Wire_API):
    def __init__(self, pin):
        """
        Klasa do obsługi magistrali 1-Wire na Raspberry Pi.
        :param pin: Numer pinu GPIO do komunikacji 1-Wire (BCM).
        """
        self.pin = pin
        self.device_files = []

    def get_required_resources(self):
        """Zwraca listę pinów używanych przez magistralę 1-Wire."""
        return {"pins": [self.pin]}

    def initialize(self):
        """
        Inicjalizuje interfejs 1-Wire oraz ładuje odpowiednie moduły jądra.
        Wyszukuje dostępne urządzenia na magistrali i zapisuje ich pliki.
        """
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.IN)

        os.system("modprobe w1-gpio")
        os.system("modprobe w1-therm")

        base_dir = '/sys/bus/w1/devices/'
        # odczekaj chwilę na załadowanie urządzeń
        time.sleep(1)
        self.device_files = glob.glob(base_dir + '28*')  # czujniki temperatury DS18B20 jako przykład

        if not self.device_files:
            print("Nie znaleziono urządzeń 1-Wire. Sprawdź połączenia.")

    def list_devices(self):
        """
        Zwraca listę identyfikatorów urządzeń podłączonych do magistrali 1-Wire.
        """
        base_dir = '/sys/bus/w1/devices/'
        devices = glob.glob(base_dir + '*/')
        return [os.path.basename(d.strip('/')) for d in devices if 'w1_bus_master' not in d]

    def read_device(self, device_id, filename='w1_slave'):
        """
        Odczytuje zawartość pliku urządzenia 1-Wire.
        :param device_id: Identyfikator urządzenia 1-Wire.
        :param filename: Nazwa pliku do odczytu w katalogu urządzenia.
        :return: Zawartość pliku jako string.
        """
        device_path = f'/sys/bus/w1/devices/{device_id}/{filename}'
        with open(device_path, 'r') as f:
            return f.read()

    def read_temperature(self, device_id=None):
        """
        Odczytuje temperaturę z wybranego urządzenia DS18B20.
        :param device_id: ID urządzenia, jeśli None to używa pierwszego znalezionego.
        :return: Temperatura w stopniach Celsjusza.
        """
        if device_id is None:
            if not self.device_files:
                raise RuntimeError("Brak wykrytych urządzeń 1-Wire.")
            device_id = os.path.basename(self.device_files[0])

        data = self.read_device(device_id)
        lines = data.split('\n')
        if 'YES' not in lines[0]:
            raise IOError("Błąd odczytu danych z czujnika.")
        equals_pos = lines[1].find('t=')
        if equals_pos == -1:
            raise IOError("Nie znaleziono danych temperatury.")
        temp_string = lines[1][equals_pos + 2:]
        return float(temp_string) / 1000.0

    def reset_bus(self):
        """
        Resetuje magistralę 1-Wire.
        (Na Raspberry Pi to zazwyczaj wiąże się z odładowaniem i załadowaniem modułów).
        """
        os.system("modprobe -r w1_gpio")
        os.system("modprobe w1_gpio")
        time.sleep(0.5)

    def write_byte(self, device_id, value):
        """
        Zapisuje bajt do urządzenia 1-Wire (jeśli urządzenie i sterownik to obsługują).
        Na Raspberry Pi typowo odczyt/zapis odbywa się poprzez sysfs i jest ograniczony.
        Ta metoda może wymagać dedykowanych sterowników.
        """
        raise NotImplementedError("Bezpośredni zapis bajtu nie jest standardowo wspierany przez sysfs.")

    def release(self):
        """Zwalnia zasoby GPIO oraz odładowuje moduły 1-Wire."""
        GPIO.cleanup(self.pin)
        os.system("modprobe -r w1-gpio")
        os.system("modprobe -r w1-therm")
    
    def enable_logging(self):
        self.logging_enabled = True

    def disable_logging(self):
        self.logging_enabled = False

    def _log(self, message):
        if self.logging_enabled and self.logger:
            self.logger.log(message)


class RPiADC_API(ABC):
    @abstractmethod
    def get_required_resources(self):
        """Zwraca zasoby wymagane przez ADC."""
        pass

    @abstractmethod
    def initialize(self):
        """Inicjalizuje połączenie z ADC."""
        pass

    @abstractmethod
    def read(self):
        """Odczytuje wartość analogową z ADC."""
        pass

    @abstractmethod
    def read_all_channels(self):
        """Odczytuje wartości ze wszystkich kanałów ADC."""
        pass

    @abstractmethod
    def release(self):
        """Zwalnia zasoby ADC."""
        pass

    @abstractmethod
    def enable_logging(self):
        pass

    @abstractmethod
    def disable_logging(self):
        pass

class RPiADC(RPiADC_API):
    def __init__(self, channel=0):
        """
        Klasa do obsługi przetwornika ADC (np. MCP3008) przez SPI.
        :param channel: Kanał ADC (0-7).
        """
        if channel not in range(8):
            raise ValueError("Kanał musi być z zakresu 0-7.")
        self.channel = channel
        self.spi = spidev.SpiDev()

    def get_required_resources(self):
        """Zwraca zasoby wymagane przez ADC (standardowe piny SPI)."""
        return {"pins": [7, 8, 9, 10, 11]}  # piny SPI0

    def initialize(self):
        """Inicjalizuje połączenie SPI i ustawia parametry ADC."""
        self.spi.open(0, 0)
        self.spi.max_speed_hz = 1350000

    def read(self):
        """
        Czyta wartość analogową z wybranego kanału ADC.
        :return: Wartość 10-bitowa (0-1023).
        """
        adc = self.spi.xfer2([1, (8 + self.channel) << 4, 0])
        return ((adc[1] & 3) << 8) + adc[2]

    def read_all_channels(self):
        """
        Odczytuje wartości ze wszystkich kanałów ADC (0-7).
        :return: Lista wartości analogowych z każdego kanału.
        """
        values = []
        for ch in range(8):
            adc = self.spi.xfer2([1, (8 + ch) << 4, 0])
            val = ((adc[1] & 3) << 8) + adc[2]
            values.append(val)
        return values

    def release(self):
        """Zamyka połączenie SPI."""
        self.spi.close()
    
    def enable_logging(self):
        self.logging_enabled = True

    def disable_logging(self):
        self.logging_enabled = False

    def _log(self, message):
        if self.logging_enabled and self.logger:
            self.logger.log(message)


class RPiCAN_API(ABC):
    @abstractmethod
    def send_message(self, arbitration_id, data, extended_id=False):
        """Wysyła wiadomość CAN.
        :param arbitration_id: ID wiadomości CAN
        :param data: dane jako bytes lub list[int]
        :param extended_id: czy ID jest rozszerzone
        """
        pass

    @abstractmethod
    def receive_message(self, timeout=1.0):
        """Odbiera wiadomość CAN z timeoutem (sekundy).
        :return: Obiekt wiadomości CAN lub None, jeśli timeout
        """
        pass

    @abstractmethod
    def enable_logging(self):
        pass

    @abstractmethod
    def disable_logging(self):
        pass

class RPiCAN(RPiCAN_API):
    def __init__(self, interface='can0', bitrate=500000):
        """
        Klasa do obsługi interfejsu CAN przez SocketCAN.
        :param interface: Nazwa interfejsu CAN (np. 'can0').
        :param bitrate: Prędkość magistrali CAN w bitach/s.
        """
        self.interface = interface
        self.bitrate = bitrate
        self.bus = None

    def get_required_resources(self):
        """Zwraca wymagane zasoby - CAN zwykle nie używa GPIO."""
        return {"pins": []}

    def initialize(self):
        """Uruchamia interfejs CAN z podanym bitrate oraz tworzy obiekt bus."""
        # Włącz interfejs CAN w systemie Linux
        os.system(f'sudo ip link set {self.interface} up type can bitrate {self.bitrate}')
        # Tworzymy obiekt CAN bus
        self.bus = can.interface.Bus(channel=self.interface, bustype='socketcan')

    def send_message(self, arbitration_id, data, extended_id=False):
        """
        Wysyła wiadomość CAN.
        :param arbitration_id: ID wiadomości CAN (int)
        :param data: dane do wysłania (bytes lub lista int)
        :param extended_id: czy ID jest rozszerzone (bool)
        """
        msg = can.Message(arbitration_id=arbitration_id,
                          data=data,
                          is_extended_id=extended_id)
        try:
            self.bus.send(msg)
        except can.CanError as e:
            raise RuntimeError(f"Błąd podczas wysyłania wiadomości CAN: {e}")

    def receive_message(self, timeout=1.0):
        """
        Odbiera wiadomość CAN.
        :param timeout: czas oczekiwania w sekundach (float)
        :return: Obiekt wiadomości CAN lub None, jeśli timeout
        """
        msg = self.bus.recv(timeout)
        return msg

    def release(self):
        """Zamyka interfejs CAN (wyłącza go w systemie)."""
        if self.bus is not None:
            self.bus.shutdown()
            self.bus = None
        os.system(f'sudo ip link set {self.interface} down')
    
    def enable_logging(self):
        self.logging_enabled = True

    def disable_logging(self):
        self.logging_enabled = False

    def _log(self, message):
        if self.logging_enabled and self.logger:
            self.logger.log(message)

class RPiHardwarePWM_API(ABC):

    @abstractmethod
    def set_duty_cycle(self, duty_cycle):
        """Ustawia wypełnienie PWM (0-100%)."""
        pass

    @abstractmethod
    def set_frequency(self, frequency):
        """Ustawia częstotliwość PWM w Hz."""
        pass

    @abstractmethod
    def enable_logging(self):
        pass

    @abstractmethod
    def disable_logging(self):
        pass

class RPiHardwarePWM(RPiHardwarePWM_API):
    def __init__(self, pin, frequency=1000):
        """
        Klasa do obsługi sprzętowego PWM na Raspberry Pi.
        :param pin: Numer pinu GPIO.
        :param frequency: Częstotliwość sygnału PWM w Hz.
        """
        self.pin = pin
        self.frequency = frequency
        self.pwm = None

    def get_required_resources(self):
        """Zwraca wymagane zasoby (piny GPIO)."""
        return {"pins": [self.pin]}

    def initialize(self):
        """Inicjalizuje PWM na danym pinie."""
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT)
        self.pwm = GPIO.PWM(self.pin, self.frequency)
        self.pwm.start(0)  # domyślnie 0% wypełnienia

    def set_duty_cycle(self, duty_cycle):
        """
        Ustawia wypełnienie PWM.
        :param duty_cycle: Wypełnienie w procentach (0-100).
        """
        if self.pwm:
            self.pwm.ChangeDutyCycle(duty_cycle)

    def set_frequency(self, frequency):
        """
        Ustawia częstotliwość PWM.
        :param frequency: Częstotliwość w Hz.
        """
        if self.pwm:
            self.pwm.ChangeFrequency(frequency)

    def release(self):
        """Zatrzymuje i czyści PWM."""
        if self.pwm:
            self.pwm.stop()
        GPIO.cleanup(self.pin)

    def enable_logging(self):
        self.logging_enabled = True

    def disable_logging(self):
        self.logging_enabled = False

    def _log(self, message):
        if self.logging_enabled and self.logger:
            self.logger.log(message)

