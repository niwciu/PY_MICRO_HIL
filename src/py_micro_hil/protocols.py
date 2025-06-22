from pymodbus.client import ModbusSerialClient as ModbusClient
from abc import ABC, abstractmethod


class ModbusRTU_API(ABC):
    @abstractmethod
    def read_holding_registers(self, slave_address, address, count):
        """
        Reads holding registers from a Modbus RTU device.
        """
        pass

    @abstractmethod
    def write_single_register(self, slave_address, address, value):
        """
        Writes a single register to a Modbus RTU device.
        """
        pass

    @abstractmethod
    def write_multiple_registers(self, slave_address, address, values):
        """
        Writes multiple registers to a Modbus RTU device.
        """
        pass

    @abstractmethod
    def read_coils(self, slave_address, address, count):
        """
        Reads coil statuses (boolean values).
        """
        pass

    @abstractmethod
    def read_discrete_inputs(self, slave_address, address, count):
        """
        Reads discrete inputs (read-only boolean values).
        """
        pass

    @abstractmethod
    def read_input_registers(self, slave_address, address, count):
        """
        Reads input registers.
        """
        pass

    @abstractmethod
    def write_single_coil(self, slave_address, address, value):
        """
        Writes a single coil (True/False).
        """
        pass

    @abstractmethod
    def write_multiple_coils(self, slave_address, address, values):
        """
        Writes multiple coils.
        """
        pass

    @abstractmethod
    def get_initialized_params(self):
        """
        Returns the configuration parameters of the client.
        """
        pass


class ModbusRTU(ModbusRTU_API):
    def __init__(self, port='/dev/ttyUSB0', baudrate=115200, stopbits=1, parity='N', timeout=1):
        """
        Class for handling Modbus RTU communication.
        :param port: Serial port for communication.
        :param baudrate: Baud rate.
        :param stopbits: Number of stop bits.
        :param parity: Parity ('N', 'E', 'O').
        :param timeout: Response timeout in seconds.
        """
        self.port = port
        self.baudrate = baudrate
        self.stopbits = stopbits
        self.parity = parity
        self.timeout = timeout
        self.client = None

    def get_required_resources(self):
        """
        Returns the required system resources (serial port).
        """
        return {"ports": [self.port]}

    def initialize(self):
        """
        Initializes the Modbus RTU client.
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
        Closes the Modbus RTU connection.
        """
        if self.client and self.client.connected:
            self.client.close()

    def get_initialized_params(self):
        """
        Returns the parameters used for initializing the Modbus RTU client.
        """
        return {
            "port": self.port,
            "baudrate": self.baudrate,
            "stopbits": self.stopbits,
            "parity": self.parity,
            "timeout": self.timeout
        }

    def read_holding_registers(self, slave_address, address, count):
        if not self.client:
            raise RuntimeError("Modbus client not initialized.")
        response = self.client.read_holding_registers(address, count, slave=slave_address)
        if not response or response.isError():
            raise IOError(f"[Modbus] Error response received: {response}")
        return response.registers

    def write_single_register(self, slave_address, address, value):
        if not self.client:
            raise RuntimeError("Modbus client not initialized.")
        response = self.client.write_register(address, value, slave=slave_address)
        if not response or response.isError():
            raise IOError(f"[Modbus] Error response received: {response}")
        return response

    def write_multiple_registers(self, slave_address, address, values):
        if not self.client:
            raise RuntimeError("Modbus client not initialized.")
        response = self.client.write_registers(address, values, slave=slave_address)
        if not response or response.isError():
            raise IOError(f"[Modbus] Error response received: {response}")
        return response

    def read_coils(self, slave_address, address, count):
        if not self.client:
            raise RuntimeError("Modbus client not initialized.")
        response = self.client.read_coils(address, count, slave=slave_address)
        if not response or response.isError():
            raise IOError(f"[Modbus] Error response received: {response}")
        return response.bits

    def read_discrete_inputs(self, slave_address, address, count):
        if not self.client:
            raise RuntimeError("Modbus client not initialized.")
        response = self.client.read_discrete_inputs(address, count, slave=slave_address)
        if not response or response.isError():
            raise IOError(f"[Modbus] Error response received: {response}")
        return response.bits

    def read_input_registers(self, slave_address, address, count):
        if not self.client:
            raise RuntimeError("Modbus client not initialized.")
        response = self.client.read_input_registers(address, count, slave=slave_address)
        if not response or response.isError():
            raise IOError(f"[Modbus] Error response received: {response}")
        return response.registers

    def write_single_coil(self, slave_address, address, value):
        if not self.client:
            raise RuntimeError("Modbus client not initialized.")
        response = self.client.write_coil(address, value, slave=slave_address)
        if not response or response.isError():
            raise IOError(f"[Modbus] Error response received: {response}")
        return response

    def write_multiple_coils(self, slave_address, address, values):
        if not self.client:
            raise RuntimeError("Modbus client not initialized.")
        response = self.client.write_coils(address, values, slave=slave_address)
        if not response or response.isError():
            raise IOError(f"[Modbus] Error response received: {response}")
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
