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

# import can

# from abc import ABC, abstractmethod

# class CANBus_API(ABC):
#     @abstractmethod
#     def send_message(self, arbitration_id: int, data: bytes, extended_id: bool = False):
#         """
#         Wysyła wiadomość CAN.
#         :param arbitration_id: ID ramki CAN (standard lub rozszerzony).
#         :param data: Dane do wysłania (max 8 bajtów).
#         :param extended_id: Czy używać rozszerzonego identyfikatora (29-bit).
#         """
#         pass

#     @abstractmethod
#     def receive_message(self, timeout: float = 1.0):
#         """
#         Odbiera wiadomość CAN z zadanym timeoutem.
#         :param timeout: Czas oczekiwania w sekundach.
#         :return: Odebrana wiadomość jako obiekt.
#         """
#         pass

#     @abstractmethod
#     def get_initialized_params(self):
#         """
#         Zwraca parametry konfiguracji magistrali CAN.
#         """
#         pass

#     @abstractmethod
#     def initialize(self):
#         """
#         Inicjalizuje interfejs CAN.
#         """
#         pass

#     @abstractmethod
#     def release(self):
#         """
#         Zamyka interfejs CAN i zwalnia zasoby.
#         """
#         pass


# class CANBus(CANBus_API):
#     def __init__(self, channel='can0', bitrate=500000):
#         """
#         Klasa do obsługi magistrali CAN przez socketCAN.
#         :param channel: Nazwa interfejsu (np. 'can0').
#         :param bitrate: Prędkość magistrali CAN (bitrate).
#         """
#         self.channel = channel
#         self.bitrate = bitrate
#         self.bus = None

#     def get_required_resources(self):
#         """Zwraca wymagane zasoby systemowe."""
#         return {"interface": self.channel}

#     def get_initialized_params(self):
#         """Zwraca aktualne parametry połączenia CAN."""
#         return {
#             "channel": self.channel,
#             "bitrate": self.bitrate
#         }

#     def initialize(self):
#         """Inicjalizuje interfejs CAN."""
#         self.bus = can.interface.Bus(channel=self.channel, bustype='socketcan')

#     def release(self):
#         """Zamyka połączenie z magistralą CAN."""
#         if self.bus:
#             self.bus.shutdown()
#             self.bus = None

#     def send_message(self, arbitration_id, data, extended_id=False):
#         """Wysyła wiadomość CAN."""
#         if not isinstance(data, (bytes, bytearray)):
#             raise TypeError("Data must be of type 'bytes' or 'bytearray'.")

#         if len(data) > 8:
#             raise ValueError("CAN frame data must be 8 bytes or less.")

#         msg = can.Message(
#             arbitration_id=arbitration_id,
#             data=data,
#             is_extended_id=extended_id
#         )

#         try:
#             self.bus.send(msg)
#         except can.CanError as e:
#             raise IOError(f"CAN send failed: {e}")

#     def receive_message(self, timeout=1.0):
#         """Odbiera wiadomość CAN w określonym czasie."""
#         msg = self.bus.recv(timeout)
#         if msg is None:
#             raise TimeoutError("No CAN message received within timeout.")
#         return {
#             "timestamp": msg.timestamp,
#             "arbitration_id": msg.arbitration_id,
#             "data": bytes(msg.data),
#             "extended_id": msg.is_extended_id,
#             "dlc": msg.dlc
#         }
