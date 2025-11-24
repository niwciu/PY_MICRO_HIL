import types


# --- Dummy GPIO ---
class DummyPWM:
    def __init__(self, pin, freq):
        self.pin = pin
        self.freq = freq
        self.duty = 0
        self.started = False

    def start(self, duty):
        self.started = True
        self.duty = duty

    def ChangeDutyCycle(self, duty):
        if not 0 <= duty <= 100:
            raise ValueError("Duty cycle must be 0-100%")
        self.duty = duty

    def ChangeFrequency(self, freq):
        if freq <= 0:
            raise ValueError("Frequency must be > 0Hz")
        self.freq = freq

    def stop(self):
        self.started = False


GPIO = types.SimpleNamespace(
    BCM="BCM",
    IN="IN",
    OUT="OUT",
    HIGH=1,
    LOW=0,
    PWM=lambda pin, freq: DummyPWM(pin, freq),
    setmode=lambda mode: None,
    setup=lambda pin, mode, **kw: None,
    output=lambda pin, value: None,
    input=lambda pin: 0,
    cleanup=lambda pin=None: None,
)


# --- Dummy SPI ---
class DummySPI:
    def __init__(self):
        self.bus = None
        self.device = None

    def open(self, bus, device):
        self.bus, self.device = bus, device

    def xfer(self, data):  # test wymaga odwróconej listy
        return list(reversed(data))

    def xfer2(self, data):  # test oczekuje tego samego
        return data

    def writebytes(self, data):
        self.last_write = data

    def readbytes(self, length):
        return [0] * length

    def close(self):
        self.bus = None


spidev = types.SimpleNamespace(SpiDev=DummySPI)


# --- Dummy SMBus (I2C) ---
class DummySMBus:
    def __init__(self, bus):
        self.bus = bus

    def close(self):
        pass

    def write_quick(self, addr):
        # test oczekuje wyjątku dla addr == 0x09
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


SMBus = DummySMBus


# --- Dummy Serial (UART) ---
class DummySerial:
    def __init__(self, *a, **kw):
        self.buffer = b""

    def write(self, data):
        if isinstance(data, str):
            data = data.encode()
        self.buffer += data

    def read(self, size=1):  # test oczekuje b"x"
        return b"x" * size

    def readline(self):  # test oczekuje b"ok\n"
        return b"ok\n"

    def close(self):
        pass


serial = types.SimpleNamespace(
    Serial=DummySerial,
    PARITY_NONE="N",
    PARITY_EVEN="E",
    PARITY_ODD="O",
    STOPBITS_ONE=1,
    STOPBITS_TWO=2,
)
