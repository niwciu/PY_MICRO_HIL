import RPi.GPIO as GPIO
from smbus2 import SMBus
import spidev
import serial


class RPiGPIO:
    def __init__(self, pin_config):
        """
        Klasa do obsługi GPIO.
        :param pin_config: Słownik w formacie {pin: {'mode': GPIO.OUT, 'initial': GPIO.LOW}}
        """
        self.pin_config = pin_config

    def get_required_resources(self):
        """
        Zwraca zasoby wymagane przez GPIO (lista pinów).
        """
        return {"pins": list(self.pin_config.keys())}

    def initialize(self):
        """
        Inicjalizuje piny GPIO.
        """
        GPIO.setmode(GPIO.BCM)
        for pin, config in self.pin_config.items():
            if config['mode'] == GPIO.OUT:
                GPIO.setup(pin, config['mode'], initial=config.get('initial', GPIO.LOW))
            else:
                GPIO.setup(pin, config['mode'])

    def release(self):
        """
        Zwalnia zarezerwowane piny GPIO.
        """
        for pin in self.pin_config.keys():
            GPIO.cleanup(pin)


class RPiPWM:
    def __init__(self, pin, frequency=1000):
        """
        Klasa do obsługi PWM.
        :param pin: Numer pinu GPIO.
        :param frequency: Częstotliwość PWM w Hz.
        """
        self.pin = pin
        self.frequency = frequency
        self.pwm = None

    def get_required_resources(self):
        """
        Zwraca zasoby wymagane przez PWM (lista pinów).
        """
        return {"pins": [self.pin]}

    def initialize(self):
        """
        Inicjalizuje PWM na pinie.
        """
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT)
        self.pwm = GPIO.PWM(self.pin, self.frequency)
        self.pwm.start(0)

    def set_duty_cycle(self, duty_cycle):
        """
        Ustawia wypełnienie PWM.
        :param duty_cycle: Wypełnienie w procentach (0-100).
        """
        if self.pwm:
            self.pwm.ChangeDutyCycle(duty_cycle)

    def release(self):
        """
        Zatrzymuje PWM i zwalnia pin.
        """
        if self.pwm:
            self.pwm.stop()
        GPIO.cleanup(self.pin)


class RPiUART:
    def __init__(self, port='/dev/serial0', baudrate=9600, timeout=1, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE):
        """
        Klasa do obsługi UART.
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.parity = parity
        self.stopbits = stopbits
        self.reserved_pins = [14, 15]  # Standardowe piny TXD i RXD
        self.serial = None

    def get_required_resources(self):
        """
        Zwraca zasoby wymagane przez UART (piny i port).
        """
        return {"pins": self.reserved_pins, "ports": [self.port]}

    def initialize(self):
        """
        Inicjalizuje port UART.
        """
        self.serial = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout,
            parity=self.parity,
            stopbits=self.stopbits
        )

    def release(self):
        """
        Zamyka port UART.
        """
        if self.serial:
            self.serial.close()

    def get_initialized_params(self):
        """
        Zwraca parametry, z którymi zostały zainicjalizowane porty Modbus TRU.
        """
        return {
            "port": self.port,
            "baudrate": self.baudrate,
            "stopbits": self.stopbits,
            "parity": self.parity,
            "timeout": self.timeout
        }


class RPiI2C:
    def __init__(self, bus=1, frequency=100000):
        """
        Klasa do obsługi magistrali I2C.
        :param bus: Numer magistrali I2C, domyślnie 1.
        """
        self.bus_number = bus
        
        # Określanie pinów w zależności od magistrali
        if self.bus_number == 1:
            self.reserved_pins = [2, 3]  
        elif self.bus_number == 0:
            self.reserved_pins = [0, 1]  
        else:
            raise ValueError(f"Invalid bus number: {self.bus_number}. Only 0 and 1 are supported.")
        self.frequency = frequency
        self.bus = None

    def get_required_resources(self):
        """
        Zwraca zasoby wymagane przez I2C (lista pinów oraz urządzenie systemowe).
        """
        return {
            "pins": self.reserved_pins,    # Piny GPIO (SDA, SCL)
            "ports": [f"/dev/i2c-{self.bus_number}"]  # Interfejs systemowy dla I2C (np. /dev/i2c-1)
        }
    
    def get_initialized_params(self):
        """
        Zwraca parametry magistrali I2C po inicjalizacji.
        """
        return {
            "bus": (f"I2C{self.bus_number}"),
            "frequency": self.frequency
        }

    def initialize(self):
        """
        Inicjalizuje magistralę I2C.
        """
        # Inicjalizacja samego I2C
        self.bus = SMBus(self.bus_number)
        self.bus.frequency = self.frequency

    def release(self):
        """
        Zamyka magistralę I2C.
        """
        if self.bus:
            self.bus.close()

    def read(self, address, register, length):
        """
        Odczytuje dane z urządzenia I2C.
        :param address: Adres urządzenia slave.
        :param register: Rejestr do odczytu.
        :param length: Liczba bajtów do odczytania.
        :return: Odczytane dane.
        """
        return self.bus.read_i2c_block_data(address, register, length)

    def write(self, address, register, data):
        """
        Wysyła dane do urządzenia I2C.
        :param address: Adres urządzenia slave.
        :param register: Rejestr do zapisu.
        :param data: Dane do wysłania.
        """
        self.bus.write_i2c_block_data(address, register, data)

    def scan(self):
        """
        Skanuje magistralę I2C w celu wykrycia dostępnych urządzeń.
        :return: Lista adresów urządzeń.
        """
        devices = []
        for address in range(128):
            try:
                self.bus.write_quick(address)
                devices.append(address)
            except:
                pass  # Ignoruj urządzenia, które nie odpowiadają
        return devices

    def write_byte(self, address, value):
        """
        Wysyła pojedynczy bajt do urządzenia I2C.
        :param address: Adres urządzenia slave.
        :param value: Wartość bajtu do wysłania.
        """
        self.bus.write_byte(address, value)

    def read_byte(self, address):
        """
        Odczytuje pojedynczy bajt z urządzenia I2C.
        :param address: Adres urządzenia slave.
        :return: Odczytany bajt.
        """
        return self.bus.read_byte(address)

    def read_word(self, address, register):
        """
        Odczytuje słowo (2 bajty) z urządzenia I2C.
        :param address: Adres urządzenia slave.
        :param register: Adres rejestru, z którego mają być odczytane dwa bajty.
        :return: Odczytane słowo (2 bajty).
        """
        return self.bus.read_word_data(address, register)

    def write_word(self, address, register, value):
        """
        Wysyła słowo (2 bajty) do urządzenia I2C.
        :param address: Adres urządzenia slave.
        :param register: Adres rejestru, do którego mają być zapisane dwa bajty.
        :param value: Wartość słowa (2 bajty) do wysłania.
        """
        self.bus.write_word_data(address, register, value)


class RPiSPI:
    def __init__(self, bus=0, device=0, max_speed_hz=50000, mode=0, bits_per_word=8, cs_high=False, lsbfirst=False, timeout=1.0):
        """
        Klasa do obsługi magistrali SPI.
        :param bus: Numer magistrali SPI (0 lub 1).
        :param device: Numer urządzenia SPI (0 lub 1).
        :param max_speed_hz: Maksymalna prędkość transmisji w Hz.
        :param mode: Tryb SPI (0-3), kontrolujący CPOL i CPHA.
        :param bits_per_word: Liczba bitów w jednym słowie (8 lub 16).
        :param cs_high: Czy linia Chip Select jest aktywna na wysokim poziomie (True/False).
        :param lsbfirst: Czy bity są przesyłane od najmniej znaczącego bitu (True/False).
        :param timeout: Czas oczekiwania na odpowiedź w sekundach.
        """
        self.spi = spidev.SpiDev()
        self.bus = bus
        self.device = device
        self.max_speed_hz = max_speed_hz
        self.mode = mode
        self.bits_per_word = bits_per_word
        self.cs_high = cs_high
        self.lsbfirst = lsbfirst
        self.timeout = timeout

        # Określanie pinów w zależności od magistrali SPI
        if self.bus == 1:
            self.reserved_pins = [16, 17, 18, 19, 20, 21]  # SPI1
        elif self.bus == 0:
            self.reserved_pins = [7, 8, 9, 10, 11]  # SPI0
        else:
            raise ValueError(f"Invalid bus number: {self.bus}. Only 0 and 1 are supported.")


    def get_required_resources(self):
        """
        Zwraca zasoby wymagane przez SPI (lista pinów oraz urządzenie systemowe).
        """
        return {
            "pins": self.reserved_pins,   
            "ports": [f"/dev/spidev{self.bus}.{self.device}"]  
        }
    
    def get_initialized_params(self):
        """
        Zwraca parametry magistrali I2C po inicjalizacji.
        """
        return {
            "device": (f"spidev{self.bus}.{self.device}"),
            "max_speed_hz": self.max_speed_hz
        }

    def initialize(self):
        """
        Otwiera połączenie SPI.
        """
        self.spi.open(self.bus, self.device)
        #Ustawienia parametrów SPI
        self.spi.max_speed_hz = self.max_speed_hz
        self.spi.mode = self.mode
        self.spi.bits_per_word = self.bits_per_word
        # self.spi.cs_high = self.cs_high
        self.spi.lsbfirst = self.lsbfirst
        # self.spi.timeout = self.timeout

        

    def release(self):
        """
        Zamyka połączenie SPI.
        """
        self.spi.close()


# Nowe klasy peryferiów
class RPi1Wire:
    def __init__(self, pin):
        self.pin = pin

    def get_required_resources(self):
        return {"pins": [self.pin]}

    def initialize(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.IN)

    def release(self):
        GPIO.cleanup(self.pin)


class RPiADC:
    def __init__(self, channel):
        self.channel = channel
        self.spi = spidev.SpiDev()

    def get_required_resources(self):
        return {"pins": [7, 8, 9, 10, 11]}  # Standardowe piny SPI

    def initialize(self):
        self.spi.open(0, self.channel)
        self.spi.max_speed_hz = 1350000

    def read(self):
        adc = self.spi.xfer2([1, (8 + self.channel) << 4, 0])
        return ((adc[1] & 3) << 8) + adc[2]

    def release(self):
        self.spi.close()


class RPiCAN:
    def __init__(self, interface='can0'):
        self.interface = interface

    def get_required_resources(self):
        return {"pins": []}  # CAN zwykle nie używa GPIO

    def initialize(self):
        import os
        os.system(f'sudo ip link set {self.interface} up type can bitrate 500000')

    def release(self):
        import os
        os.system(f'sudo ip link set {self.interface} down')


class RPiHATEEPROM:
    def __init__(self, bus=1, address=0x50):
        self.bus_number = bus
        self.address = address
        self.bus = None

    def get_required_resources(self):
        return {"pins": [2, 3]}  # SDA i SCL

    def initialize(self):
        self.bus = SMBus(self.bus_number)

    def read_eeprom(self, offset, length):
        return [self.bus.read_byte_data(self.address, offset + i) for i in range(length)]

    def release(self):
        if self.bus:
            self.bus.close()


class RPiHardwarePWM:
    def __init__(self, pin, frequency=1000):
        self.pin = pin
        self.frequency = frequency

    def get_required_resources(self):
        return {"pins": [self.pin]}

    def initialize(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT)

    def release(self):
        GPIO.cleanup(self.pin)
