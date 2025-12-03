from pymodbus.client import ModbusSerialClient as ModbusClient
from abc import ABC, abstractmethod
import time
import logging
from typing import Any, Optional
from pprint import pformat


# Mixins for logging
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

    @abstractmethod
    def enable_logging(self) -> None:
        """Enable debug logging."""
        pass

    @abstractmethod
    def disable_logging(self) -> None:
        """Disable debug logging."""
        pass


class ModbusRTU(ModbusRTU_API, LoggingMixin):
    def __init__(
        self,
        port="/dev/ttyUSB0",
        baudrate=115200,
        stopbits=1,
        parity="N",
        timeout=1,
        logger: Optional[logging.Logger] = None,
        logging_enabled: bool = True,
    ):
        """
        Class for handling Modbus RTU communication.
        :param port: Serial port for communication.
        :param baudrate: Baud rate.
        :param stopbits: Number of stop bits.
        :param parity: Parity ('N', 'E', 'O').
        :param timeout: Response timeout in seconds.
        :param logger: Optional logger instance for debug logging.
        :param logging_enabled: Whether to enable debug logging.
        """
        LoggingMixin.__init__(self, logger, logging_enabled)
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
            timeout=self.timeout,
        )
        if not self.client.connect():
            raise ConnectionError(f"Unable to connect to Modbus RTU server on port {self.port}.")
        # Flush receive buffer to clear any garbage data from connection handshake
        self.client.socket.reset_input_buffer()
        self.client.socket.reset_output_buffer()
        # Add inter-character timeout to prevent frame parsing issues
        # This gives the serial port time to stabilize after connection
        time.sleep(0.1)
        self._log(f"[INFO] Initialized Modbus RTU on {self.port} at {self.baudrate}bps")

    def release(self):
        """
        Closes the Modbus RTU connection.
        """
        if self.client and self.client.connected:
            self.client.close()
            self._log(f"[INFO] Closed Modbus RTU on {self.port}")

    # Explicitly implement logging control methods to satisfy the ABC
    def enable_logging(self) -> None:
        """Enable debug logging for this Modbus client."""
        self._logging_enabled = True

    def disable_logging(self) -> None:
        """Disable debug logging for this Modbus client."""
        self._logging_enabled = False

    def _sync_serial_port(self):
        """
        Synchronizes the serial port state by resetting buffers and adding delay.
        Prevents frame parsing errors when reusing the same connection between tests.

        WHY PYMODBUS DOESN'T HANDLE THIS:
        - pymodbus assumes a *continuously running* stable serial connection
        - It doesn't account for port state changes between test boundaries
        - When switching test contexts, the RS-485 transceiver can be in an undefined state
        - The hardware needs time to stabilize before a new Modbus transaction can start
        - Frame parsing relies on detecting inter-character gaps (silence) - this fails if
          the port is electrically unstable from the previous test

        This inter-test synchronization is a framework-level concern, not a protocol-level one.
        Each Modbus operation (read/write) now ensures the port is synchronized before sending.
        """
        if self.client and self.client.socket:
            try:
                # Reset both input and output buffers of the serial port
                self.client.socket.reset_input_buffer()
                self.client.socket.reset_output_buffer()
            except Exception:
                pass
            # Small delay to ensure serial port is ready (solves inter-test timing issues)
            time.sleep(0.05)

    def _serialize_obj(self, obj: Any, _depth: int = 0) -> Any:
        """Recursively convert objects into basic Python types for pretty printing.

        Limits recursion depth to avoid blowing the log on unexpected complex objects.
        """
        MAX_DEPTH = 3
        if _depth >= MAX_DEPTH:
            try:
                return repr(obj)
            except Exception:
                return "<unserializable>"

        # Basic types
        if obj is None or isinstance(obj, (str, int, float, bool)):
            return obj

        if isinstance(obj, dict):
            return {k: self._serialize_obj(v, _depth + 1) for k, v in obj.items()}

        if isinstance(obj, (list, tuple, set)):
            return [self._serialize_obj(v, _depth + 1) for v in obj]

        # Objects with a dict
        try:
            if hasattr(obj, "__dict__") and isinstance(obj.__dict__, dict) and obj.__dict__:
                return {k: self._serialize_obj(v, _depth + 1) for k, v in obj.__dict__.items()}
        except Exception:
            pass

        # Fallback: inspect readable attributes
        try:
            attrs = [a for a in dir(obj) if not a.startswith("_")]
            data = {}
            for a in attrs:
                try:
                    val = getattr(obj, a)
                except Exception:
                    continue
                if callable(val):
                    continue
                data[a] = self._serialize_obj(val, _depth + 1)
            if data:
                return data
        except Exception:
            pass

        # Final fallback
        try:
            return repr(obj)
        except Exception:
            return "<unrepresentable>"

    def _format_response(self, response: Any) -> str:
        """Return a pretty multi-line string representation for a response object."""
        if response is None:
            return "<None>"

        # If response has isError, include that status
        try:
            is_err = getattr(response, "isError", None)
            if callable(is_err) and is_err():
                # include the repr for error responses
                pretty_err = pformat({"error": repr(response)})
                return "\n".join(["\t" + line for line in pretty_err.splitlines()])
        except Exception:
            pass

        try:
            ser = self._serialize_obj(response)
            pretty = pformat(ser, width=120)
            # indent each line so the multi-line block is clearly part of the DEBUG log
            return "\n".join(["\t" + line for line in pretty.splitlines()])
        except Exception:
            try:
                pretty = pformat(repr(response))
                return "\n".join(["\t" + line for line in pretty.splitlines()])
            except Exception:
                return "<unrepresentable>"

    def get_initialized_params(self):
        """
        Returns the parameters used for initializing the Modbus RTU client.
        """
        return {
            "port": self.port,
            "baudrate": self.baudrate,
            "stopbits": self.stopbits,
            "parity": self.parity,
            "timeout": self.timeout,
        }

    def read_holding_registers(self, slave_address, address, count):
        if not self.client:
            raise RuntimeError("Modbus client not initialized.")
        # Synchronize serial port state before reading
        self._sync_serial_port()
        self._log(
            f"[DEBUG] send read_holding_registers cmd: slave_address={slave_address}, address={address}, count={count}"
        )
        response = self.client.read_holding_registers(
            address=address, count=count, device_id=slave_address
        )
        if not response or response.isError():
            raise IOError(f"[Modbus] Error response received: {response}")
        pretty = self._format_response(response)
        self._log(f"[DEBUG] recv read_holding_registers response:\n{pretty}")
        return response.registers

    def write_single_register(self, slave_address, address, value):
        if not self.client:
            raise RuntimeError("Modbus client not initialized.")
        # Synchronize serial port state before writing
        self._sync_serial_port()
        self._log(
            f"[DEBUG] send write_single_register cmd: slave_address={slave_address}, address={address}, value={value}"
        )
        response = self.client.write_register(address=address, value=value, device_id=slave_address)
        if not response or response.isError():
            raise IOError(f"[Modbus] Error response received: {response}")
        pretty = self._format_response(response)
        self._log(f"[DEBUG] recv write_single_register response:\n{pretty}")
        return response

    def write_multiple_registers(self, slave_address, address, values):
        if not self.client:
            raise RuntimeError("Modbus client not initialized.")
        # Synchronize serial port state before writing
        self._sync_serial_port()
        self._log(
            f"[DEBUG] send write_multiple_registers cmd: slave_address={slave_address}, address={address}, values={values}"
        )
        response = self.client.write_registers(
            address=address, value=values, device_id=slave_address
        )
        if not response or response.isError():
            raise IOError(f"[Modbus] Error response received: {response}")
        pretty = self._format_response(response)
        self._log(f"[DEBUG] recv write_multiple_registers response:\n{pretty}")
        return response

    def read_coils(self, slave_address, address, count):
        if not self.client:
            raise RuntimeError("Modbus client not initialized.")
        # Synchronize serial port state before reading
        self._sync_serial_port()
        self._log(
            f"[DEBUG] send read_coils cmd: slave_address={slave_address}, address={address}, count={count}"
        )
        response = self.client.read_coils(address=address, count=count, device_id=slave_address)
        if not response or response.isError():
            raise IOError(f"[Modbus] Error response received: {response}")
        pretty = self._format_response(response)
        self._log(f"[DEBUG] recv read_coils response:\n{pretty}")
        return response.bits

    def read_discrete_inputs(self, slave_address, address, count):
        if not self.client:
            raise RuntimeError("Modbus client not initialized.")
        # Synchronize serial port state before reading
        self._sync_serial_port()
        self._log(
            f"[DEBUG] send read_discrete_inputs cmd: slave_address={slave_address}, address={address}, count={count}"
        )
        response = self.client.read_discrete_inputs(
            address=address, count=count, device_id=slave_address
        )
        if not response or response.isError():
            raise IOError(f"[Modbus] Error response received: {response}")
        pretty = self._format_response(response)
        self._log(f"[DEBUG] recv read_discrete_inputs response:\n{pretty}")
        return response.bits

    def read_input_registers(self, slave_address, address, count):
        if not self.client:
            raise RuntimeError("Modbus client not initialized.")
        # Synchronize serial port state before reading
        self._sync_serial_port()
        self._log(
            f"[DEBUG] send read_input_registers cmd: slave_address={slave_address}, address={address}, count={count}"
        )
        response = self.client.read_input_registers(
            address=address, count=count, device_id=slave_address
        )
        if not response or response.isError():
            raise IOError(f"[Modbus] Error response received: {response}")
        pretty = self._format_response(response)
        self._log(f"[DEBUG] recv read_input_registers response:\n{pretty}")
        return response.registers

    def write_single_coil(self, slave_address, address, value):
        if not self.client:
            raise RuntimeError("Modbus client not initialized.")
        # Synchronize serial port state before writing
        self._sync_serial_port()
        self._log(
            f"[DEBUG] send write_single_coil cmd: slave_address={slave_address}, address={address}, value={value}"
        )
        response = self.client.write_coil(address=address, value=value, device_id=slave_address)
        if not response or response.isError():
            raise IOError(f"[Modbus] Error response received: {response}")
        pretty = self._format_response(response)
        self._log(f"[DEBUG] recv write_single_coil response:\n{pretty}")
        return response

    def write_multiple_coils(self, slave_address, address, values):
        if not self.client:
            raise RuntimeError("Modbus client not initialized.")
        # Synchronize serial port state before writing
        self._sync_serial_port()
        self._log(
            f"[DEBUG] send write_multiple_coils cmd: slave_address={slave_address}, address={address}, values={values}"
        )
        response = self.client.write_coils(address=address, value=values, device_id=slave_address)
        if not response or response.isError():
            raise IOError(f"[Modbus] Error response received: {response}")
        pretty = self._format_response(response)
        self._log(f"[DEBUG] recv write_multiple_coils response:\n{pretty}")
        return response
