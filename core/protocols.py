from pymodbus.client import ModbusSerialClient as ModbusClient
from abc import ABC, abstractmethod

class ModbusRTU_API(ABC):
    @abstractmethod
    def read_holding_registers(self, slave_address, address, count):
        """
        Odczytuje rejestry holding z urządzenia Modbus RTU.
        """
        pass

    @abstractmethod
    def write_single_register(self, slave_address, address, value):
        """
        Zapisuje pojedynczy rejestr w urządzeniu Modbus RTU.
        """
        pass

    @abstractmethod
    def write_multiple_registers(self, slave_address, address, values):
        """
        Zapisuje wiele rejestrów w urządzeniu Modbus RTU.
        """
        pass

    @abstractmethod
    def read_coils(self, slave_address, address, count):
        """
        Odczytuje status cewek (coils) - wartości typu bool.
        """
        pass

    @abstractmethod
    def read_discrete_inputs(self, slave_address, address, count):
        """
        Odczytuje dyskretne wejścia (read-only bool).
        """
        pass

    @abstractmethod
    def read_input_registers(self, slave_address, address, count):
        """
        Odczytuje rejestry wejściowe (input registers).
        """
        pass

    @abstractmethod
    def write_single_coil(self, slave_address, address, value):
        """
        Zapisuje pojedynczą cewkę (True/False).
        """
        pass

    @abstractmethod
    def write_multiple_coils(self, slave_address, address, values):
        """
        Zapisuje wiele cewek.
        """
        pass


    @abstractmethod
    def get_initialized_params(self):
        """
        Zwraca parametry konfiguracji klienta.
        """
        pass


class ModbusRTU(ModbusRTU_API):
    def __init__(self, port='/dev/ttyUSB0', baudrate=115200, stopbits=1, parity='N', timeout=1):
        """
        Klasa do obsługi Modbus RTU.
        :param port: Port szeregowy do komunikacji.
        :param baudrate: Szybkość transmisji w baudach.
        :param stopbits: Liczba bitów stopu.
        :param parity: Parzystość ('N', 'E', 'O').
        :param timeout: Czas oczekiwania na odpowiedź w sekundach.
        """
        self.port = port
        self.baudrate = baudrate
        self.stopbits = stopbits
        self.parity = parity
        self.timeout = timeout
        self.client = None

    def get_required_resources(self):
        """
        Zwraca zasoby wymagane przez Modbus RTU (port szeregowy).
        """
        return {"ports": [self.port]}

    def initialize(self):
        """
        Inicjalizuje klienta Modbus RTU.
        """
        self.client = ModbusClient(
            port=self.port,
            baudrate=self.baudrate,
            stopbits=self.stopbits,
            parity=self.parity,
            timeout=self.timeout
        )
        if not self.client.connect():
            raise ConnectionError(f"Unable to connect to Modbus RTU server on port {self.port}.")

    def release(self):
        """
        Zamyka połączenie Modbus RTU.
        """
        if self.client:
            self.client.close()

    def get_initialized_params(self):
        """
        Zwraca parametry, z którymi zostały zainicjalizowane porty Modbus RTU.
        """
        return {
            "port": self.port,
            "baudrate": self.baudrate,
            "stopbits": self.stopbits,
            "parity": self.parity,
            "timeout": self.timeout
        }

    def read_holding_registers(self, slave_address, address, count):
        """
        Odczytuje rejestry holding z urządzenia Modbus RTU.
        :param slave_address: Adres urządzenia slave.
        :param address: Adres początkowego rejestru.
        :param count: Liczba rejestrów do odczytania.
        :return: Lista wartości rejestrów.
        """
        response = self.client.read_holding_registers(address, count, slave=slave_address)
        if response.isError():
            raise ValueError(f"Modbus error: {response}")
        return response.registers

    def write_single_register(self, slave_address, address, value):
        """
        Zapisuje pojedynczy rejestr w urządzeniu Modbus RTU.
        :param slave_address: Adres urządzenia slave.
        :param address: Adres rejestru.
        :param value: Wartość do zapisania.
        :return: Odpowiedź z urządzenia.
        """
        response = self.client.write_register(address, value, slave=slave_address)
        if response.isError():
            raise ValueError(f"Modbus error: {response}")
        return response

    def write_multiple_registers(self, slave_address, address, values):
        """
        Zapisuje wiele rejestrów w urządzeniu Modbus RTU.
        :param slave_address: Adres urządzenia slave.
        :param address: Adres początkowego rejestru.
        :param values: Lista wartości do zapisania.
        :return: Odpowiedź z urządzenia.
        """
        response = self.client.write_registers(address, values, slave=slave_address)
        if response.isError():
            raise ValueError(f"Modbus error: {response}")
        return response

    def read_coils(self, slave_address, address, count):
        """
        Odczytuje status cewek (coils) - wartości typu bool.
        :param slave_address: Adres urządzenia slave.
        :param address: Adres początkowej cewki.
        :param count: Liczba cewek do odczytania.
        :return: Lista wartości bool.
        """
        response = self.client.read_coils(address, count, slave=slave_address)
        if response.isError():
            raise ValueError(f"Modbus error: {response}")
        return response.bits

    def read_discrete_inputs(self, slave_address, address, count):
        """
        Odczytuje dyskretne wejścia (read-only bool).
        :param slave_address: Adres urządzenia slave.
        :param address: Adres początkowego wejścia.
        :param count: Liczba wejść do odczytania.
        :return: Lista wartości bool.
        """
        response = self.client.read_discrete_inputs(address, count, slave=slave_address)
        if response.isError():
            raise ValueError(f"Modbus error: {response}")
        return response.bits

    def read_input_registers(self, slave_address, address, count):
        """
        Odczytuje rejestry wejściowe (input registers).
        :param slave_address: Adres urządzenia slave.
        :param address: Adres początkowego rejestru.
        :param count: Liczba rejestrów do odczytania.
        :return: Lista wartości rejestrów.
        """
        response = self.client.read_input_registers(address, count, slave=slave_address)
        if response.isError():
            raise ValueError(f"Modbus error: {response}")
        return response.registers

    def write_single_coil(self, slave_address, address, value):
        """
        Zapisuje pojedynczą cewkę (True/False).
        :param slave_address: Adres urządzenia slave.
        :param address: Adres cewki.
        :param value: Wartość bool do zapisania.
        :return: Odpowiedź z urządzenia.
        """
        response = self.client.write_coil(address, value, slave=slave_address)
        if response.isError():
            raise ValueError(f"Modbus error: {response}")
        return response

    def write_multiple_coils(self, slave_address, address, values):
        """
        Zapisuje wiele cewek.
        :param slave_address: Adres urządzenia slave.
        :param address: Adres początkowej cewki.
        :param values: Lista wartości bool do zapisania.
        :return: Odpowiedź z urządzenia.
        """
        response = self.client.write_coils(address, values, slave=slave_address)
        if response.isError():
            raise ValueError(f"Modbus error: {response}")
        return response

