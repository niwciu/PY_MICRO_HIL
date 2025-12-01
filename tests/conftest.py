import sys
from pathlib import Path
import types

# Ensure src directory is importable without installing the package
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

# Provide lightweight fallbacks for hardware-specific dependencies when they
# are not installed in the CI environment.
if "RPi" not in sys.modules:
    sys.modules["RPi"] = types.ModuleType("RPi")

if "RPi.GPIO" not in sys.modules:
    gpio_module = types.ModuleType("RPi.GPIO")
    gpio_module.BCM = "BCM"
    gpio_module.IN = "IN"
    gpio_module.OUT = "OUT"
    gpio_module.HIGH = 1
    gpio_module.LOW = 0
    gpio_module.PWM = lambda *_, **__: None
    gpio_module.setmode = lambda *_, **__: None
    gpio_module.setup = lambda *_, **__: None
    gpio_module.output = lambda *_, **__: None
    gpio_module.input = lambda *_: 0
    gpio_module.cleanup = lambda *_, **__: None

    sys.modules["RPi.GPIO"] = gpio_module
    # make it accessible as attribute of parent
    sys.modules["RPi"].GPIO = gpio_module

if "spidev" not in sys.modules:
    class _DummySPI:
        def __init__(self):
            self.bus = None
            self.device = None

        def open(self, bus, device):
            self.bus, self.device = bus, device

        def xfer(self, data):
            return list(reversed(data))

        def xfer2(self, data):
            return data

        def writebytes(self, data):
            self.last_write = data

        def readbytes(self, length):
            return [0] * length

        def close(self):
            self.bus = None

    sys.modules["spidev"] = types.SimpleNamespace(SpiDev=_DummySPI)

if "smbus2" not in sys.modules:
    class _DummySMBus:
        def __init__(self, bus):
            self.bus = bus

        def close(self):
            pass

        def write_quick(self, addr):
            if addr == 0x09:
                raise IOError("Fake device not responding")

        def read_i2c_block_data(self, addr, reg, length):
            return [1] * length

        def write_i2c_block_data(self, addr, reg, data):
            pass

        def read_byte(self, addr):
            return 0

        def write_byte(self, addr, val):
            pass

        def read_word_data(self, addr, reg):
            return 0xABCD

        def write_word_data(self, addr, reg, val):
            pass

    sys.modules["smbus2"] = types.SimpleNamespace(SMBus=_DummySMBus)

if "serial" not in sys.modules:
    class _DummySerial:
        def __init__(self, *args, **kwargs):
            self.buffer = b""

        def write(self, data):
            if isinstance(data, str):
                data = data.encode()
            self.buffer += data

        def read(self, size=1):
            return b"x" * size

        def readline(self):
            return b"ok\n"

        def close(self):
            pass

    sys.modules["serial"] = types.SimpleNamespace(
        Serial=_DummySerial,
        PARITY_NONE="N",
        PARITY_EVEN="E",
        PARITY_ODD="O",
        STOPBITS_ONE=1,
        STOPBITS_TWO=2,
    )

if "can" not in sys.modules:
    sys.modules["can"] = types.SimpleNamespace(interface=types.SimpleNamespace(Bus=lambda *_, **__: None))

if "yaml" not in sys.modules:
    # Minimal YAML shim using Python's built-in safe eval for test purposes only
    import ast
    class _YAMLError(Exception):
        pass

    def _safe_load(stream):
        try:
            if stream is None:
                return None
            if hasattr(stream, "read"):
                stream = stream.read()
            if isinstance(stream, (bytes, bytearray)):
                stream = stream.decode()
            if not str(stream).strip():
                return None
            return ast.literal_eval(stream)
        except Exception as exc:
            raise _YAMLError(str(exc)) from exc

    def _safe_dump(data):
        return repr(data)

    sys.modules["yaml"] = types.SimpleNamespace(safe_load=_safe_load, safe_dump=_safe_dump, YAMLError=_YAMLError)

if "jinja2" not in sys.modules:
    class _DummyTemplate:
        def __init__(self, content=""):
            self.content = content

        def render(self, **kwargs):
            return self.content.format(**kwargs)

    class _DummyEnvironment:
        def __init__(self, loader=None):
            self.loader = loader

        def get_template(self, name):
            return _DummyTemplate()

    class _DummyLoader:
        def __init__(self, *args, **kwargs):
            pass

    class _TemplateNotFound(Exception):
        pass

    sys.modules["jinja2"] = types.SimpleNamespace(
        Environment=_DummyEnvironment,
        FileSystemLoader=_DummyLoader,
        TemplateNotFound=_TemplateNotFound,
    )

if "pymodbus" not in sys.modules:
    class _DummyModbusClient:
        def __init__(self, *args, **kwargs):
            self.connected = False

        def connect(self):
            self.connected = True
            return True

        def close(self):
            self.connected = False

    client_module = types.ModuleType("pymodbus.client")
    client_module.ModbusSerialClient = _DummyModbusClient

    pymodbus_pkg = types.ModuleType("pymodbus")
    pymodbus_pkg.client = client_module

    sys.modules["pymodbus"] = pymodbus_pkg
    sys.modules["pymodbus.client"] = client_module
