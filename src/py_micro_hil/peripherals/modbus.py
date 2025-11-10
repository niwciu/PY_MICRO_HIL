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
