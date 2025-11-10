import types

# --- Dummy GPIO ---
GPIO = types.SimpleNamespace(
    BCM="BCM",
    IN="IN",
    OUT="OUT",
    HIGH=1,
    LOW=0,
    PWM=lambda pin, freq: types.SimpleNamespace(
        start=lambda d: None,
        stop=lambda: None,
        ChangeDutyCycle=lambda d: None,
        ChangeFrequency=lambda f: None
    ),
    setmode=lambda mode: None,
    setup=lambda pin, mode, **kw: None,
    output=lambda pin, value: None,
    input=lambda pin: 0,
    cleanup=lambda pin=None: None,
)

# --- Dummy SPI ---
class DummySPI:
    def open(self, bus, device): pass
    def xfer(self, data): return data
    def xfer2(self, data): return data
    def writebytes(self, data): pass
    def readbytes(self, length): return [0] * length
    def close(self): pass
spidev = types.SimpleNamespace(SpiDev=DummySPI)

# --- Dummy SMBus (I2C) ---
class DummySMBus:
    def __init__(self, bus): pass
    def close(self): pass
    def read_i2c_block_data(self, a, r, l): return [0] * l
    def write_i2c_block_data(self, a, r, d): pass
    def read_byte(self, a): return 0
    def write_byte(self, a, v): pass
    def read_word_data(self, a, r): return 0
    def write_word_data(self, a, r, v): pass
    def write_quick(self, a): pass
SMBus = DummySMBus

# --- Dummy Serial (UART) ---
class DummySerial:
    def __init__(self, *a, **kw): pass
    def write(self, data): pass
    def read(self, size=1): return b"\x00" * size
    def readline(self): return b"\n"
    def close(self): pass
serial = types.SimpleNamespace(
    Serial=DummySerial,
    PARITY_NONE="N",
    PARITY_EVEN="E",
    PARITY_ODD="O",
    STOPBITS_ONE=1,
    STOPBITS_TWO=2,
)
