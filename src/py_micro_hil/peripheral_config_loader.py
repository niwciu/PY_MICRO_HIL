import yaml
import serial
from pathlib import Path

from py_micro_hil.peripherals.RPiPeripherals import (
    RPiGPIO,
    RPiPWM,
    RPiUART,
    RPiI2C,
    RPiSPI,
    RPiHardwarePWM,
    RPiOneWire,
)
from py_micro_hil.peripherals.protocols import ModbusRTU
from py_micro_hil.utils.system import is_raspberry_pi

# Valid GPIO pins exposed on 40-pin header (BCM numbering)
VALID_GPIO_PINS = set(range(0, 28))  # 0–27 on Raspberry Pi 4B

# Hardware PWM-capable pins (BCM)
HARDWARE_PWM_PINS = {12, 13, 18, 19}

# Internal UART ports for Raspberry Pi
VALID_UART_INTERNAL_PORTS = {
    "/dev/ttyAMA0",
    "/dev/ttyAMA1",
    "/dev/ttyAMA2",
    "/dev/ttyAMA3",
    "/dev/ttyAMA4",
    "/dev/ttyS0",
    "/dev/serial0",
    "/dev/serial1",
}


def _is_usb_uart_port(port: str) -> bool:
    return port.startswith("/dev/ttyUSB") or port.startswith("/dev/ttyACM")


# -------------------------------------------------------------------
# SYSTEM-LEVEL HELPERS
# -------------------------------------------------------------------
def _read_file(path: str) -> str:
    try:
        return Path(path).read_text()
    except Exception:
        return ""


def _list_dir(path: str):
    try:
        return [str(p.name) for p in Path(path).iterdir()]
    except Exception:
        return []


def _dt_overlays_active() -> set:
    overlays_path = "/sys/kernel/config/device-tree/overlays"
    return set(_list_dir(overlays_path))


def _dev_exists(dev: str) -> bool:
    return Path(dev).exists()


def _gpio_consumers() -> dict:
    """
    Zwraca słownik {bcm_pin: consumer_name} dla pinów faktycznie zajętych
    przez kernelowe sterowniki — SPI, UART, I2C, 1-Wire itp.

    Źródło informacji: /sys/kernel/debug/gpio

    Przykładowe linie (bcm2711):

        gpio-519 (GPIO7               |spi0 CS1            ) out hi ACTIVE LOW
        gpio-516 (GPIO4               |onewire@0           ) out hi
        gpio-529 (GPIO17              ) in  hi

    Zasady parsowania:
    - globalny numer GPIO (np. gpio-519) → BCM = global - 512
      dla gpiochip0 (512–569 → BCM 0–27),
    - faktyczny „konsument” istnieje tylko, jeśli w nawiasie pojawia się '|':
          (GPIO7 |spi0 CS1)  → consumer = "spi0 CS1"
          (GPIO4 |onewire@0) → consumer = "onewire@0"
      jeśli nawias zawiera tylko "GPIO17" → pin jest wolny,
      NIE dodajemy go do słownika.
    """

    gpio_debug = "/sys/kernel/debug/gpio"
    text = _read_file(gpio_debug)
    consumers: dict[int, str] = {}

    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("gpio-"):
            continue

        try:
            # global index np. 'gpio-519'
            global_pin = int(line.split()[0].replace("gpio-", ""))

            # środek nawiasów: np. "GPIO7 |spi0 CS1"
            if "(" not in line or ")" not in line:
                continue

            inside = line[line.index("(") + 1 : line.index(")")].strip()

            # brak '|' → brak faktycznego konsumenta → pin wolny
            if "|" not in inside:
                continue

            # konsument to część po '|'
            consumer = inside.split("|", 1)[1].strip()
            if not consumer:
                continue

            # mapowanie global → BCM dla gpiochip0 (512–569)
            if 512 <= global_pin <= 569:
                bcm_pin = global_pin - 512
                consumers[bcm_pin] = consumer

        except Exception:
            continue

    return consumers


# -------------------------------------------------------------------
# ONE-WIRE KERNEL DETECTION
# -------------------------------------------------------------------
def _detect_kernel_onewire_pin():
    """
    Próba wykrycia pinu używanego przez kernelowy sterownik w1-gpio.

    Metoda:
    - skan /sys/kernel/debug/gpio w poszukiwaniu konsumentów: w1, w1-gpio, w1_gpio, onewire
    - fallback: jeśli istnieje /sys/bus/w1/devices, zakładamy domyślnie GPIO4
    """
    consumers = _gpio_consumers()
    for pin, consumer in consumers.items():
        if consumer.lower() in ("w1", "w1-gpio", "w1_gpio", "onewire", "onewire@0"):
            return pin

    # Fallback: jeśli istnieje magistrala 1-Wire, domyślny pin to 4
    if Path("/sys/bus/w1/devices").exists():
        return 4

    return None


# -------------------------------------------------------------------
# MAIN LOADER
# -------------------------------------------------------------------
def load_peripheral_configuration(yaml_file=None, logger=None):
    """
    Ładuje konfigurację peryferiów z pliku YAML.
    Jeśli wystąpi JAKIKOLWIEK [ERROR], funkcja na końcu zwraca None,
    ale w międzyczasie próbuje zweryfikować całą konfigurację i
    wypisać wszystkie błędy.
    """

    errors_occurred = False  # ustawiane przy każdym [ERROR]

    def log_or_raise(msg, warning=False):
        nonlocal errors_occurred

        tag = "[WARNING]" if warning else "[ERROR]"
        full = f"{tag} {msg}"

        if logger:
            logger.log(full, to_console=True, to_log_file=not warning)
        else:
            print(full)

        if not warning:
            errors_occurred = True

    def check_gpio_conflicts(owner: str, pins):
        """
        Sprawdza, czy któryś z pinów w 'pins' jest już używany przez kernel.
        Zwraca True, jeśli brak konfliktów. Przy konflikcie loguje [ERROR] i zwraca False.
        """
        consumers = _gpio_consumers()
        owner_lower = owner.lower()

        if logger:
            logger.log(
                f"[INFO] Following consumers of GPIO pins were found in kernel: {consumers}",
                to_console=True,
                to_log_file=False,
            )

        for pin in pins:
            if pin not in consumers:
                continue

            consumer = consumers[pin]
            cons_lower = consumer.lower()

            # Specjalna ścieżka dla 1-Wire z YAML
            if "onewire" in owner_lower or "1-wire" in owner_lower:
                if cons_lower in ("w1", "w1-gpio", "w1_gpio", "onewire", "onewire@0"):
                    log_or_raise(
                        f"GPIO {pin} is already used by kernel 1-Wire ({consumer}) "
                        f"and cannot be reused by {owner} from configuration."
                    )
                    return False
                else:
                    log_or_raise(
                        f"GPIO {pin} is already used by '{consumer}' "
                        f"and cannot be used by {owner}."
                    )
                    return False

            # Zwykły konflikt np. GPIO/SPI/PWM/I2C z czymkolwiek
            log_or_raise(
                f"GPIO {pin} is already used by '{consumer}' " f"and cannot be used by {owner}."
            )
            return False

        return True

    # Info when not running on real RPi
    if not is_raspberry_pi():
        log_or_raise(
            "Running outside Raspberry Pi — dummy interfaces active.",
            warning=True,
        )

    # 1) Locate YAML file
    if yaml_file is None:
        yaml_file = Path.cwd() / "peripherals_config.yaml"
    else:
        yaml_file = Path(yaml_file)

    if not yaml_file.exists():
        log_or_raise(f"Peripheral config file not found: {yaml_file.resolve()}")
        return None  # tutaj nie ma czego dalej sprawdzać

    # 2) Parse YAML
    try:
        with yaml_file.open("r") as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        log_or_raise(f"Failed to parse YAML: {e}")
        return None

    # 3) Validate top-level
    if config is None:
        log_or_raise("Peripheral configuration file is empty.")
        return None
    if not isinstance(config, dict):
        log_or_raise("YAML content must be a dictionary at the top level.")
        return None

    peripherals_cfg = config.get("peripherals") or {}
    protocols_cfg = config.get("protocols") or {}

    # -------------------------------
    # VALIDATE CONFIG CONFLICTS (YAML-only)
    # -------------------------------
    def validate_resource_conflicts():
        pins_registry = {}
        ports_registry = {}
        conflicts = []

        def register(registry, key, owner, resource_name):
            if key is None:
                return
            if key in registry:
                conflicts.append(
                    f"{resource_name} {key} conflict between {registry[key]} and {owner}."
                )
            else:
                registry[key] = owner

        # GPIO
        if isinstance(peripherals_cfg.get("gpio"), list):
            for idx, gpio_cfg in enumerate(peripherals_cfg["gpio"]):
                if isinstance(gpio_cfg, dict):
                    register(pins_registry, gpio_cfg.get("pin"), f"GPIO[{idx}]", "Pin")

        # SW PWM
        if isinstance(peripherals_cfg.get("pwm"), list):
            for idx, pwm_cfg in enumerate(peripherals_cfg["pwm"]):
                if isinstance(pwm_cfg, dict):
                    register(pins_registry, pwm_cfg.get("pin"), f"PWM[{idx}]", "Pin")

        # HW PWM
        if isinstance(peripherals_cfg.get("hardware_pwm"), list):
            for idx, hpw_cfg in enumerate(peripherals_cfg["hardware_pwm"]):
                if isinstance(hpw_cfg, dict):
                    register(pins_registry, hpw_cfg.get("pin"), f"HW PWM[{idx}]", "Pin")

        # UART port
        if isinstance(peripherals_cfg.get("uart"), dict):
            register(
                ports_registry,
                peripherals_cfg["uart"].get("port"),
                "UART",
                "Port",
            )

        # Modbus RTU port
        if isinstance(protocols_cfg.get("modbus"), dict):
            register(
                ports_registry,
                protocols_cfg["modbus"].get("port"),
                "ModbusRTU",
                "Port",
            )

        # SPI port (Linux device)
        if isinstance(peripherals_cfg.get("spi"), dict):
            spi_cfg = peripherals_cfg["spi"]
            dev_path = f"/dev/spidev{spi_cfg.get('bus', 0)}.{spi_cfg.get('device', 0)}"
            register(ports_registry, dev_path, "SPI", "Port")

        # 1-Wire pin w YAML też może konfliktować z GPIO/pwm itd. (historycznie)
        if isinstance(peripherals_cfg.get("onewire"), dict):
            register(
                pins_registry,
                peripherals_cfg["onewire"].get("pin", 4),
                "1-Wire",
                "Pin",
            )

        if conflicts:
            for msg in conflicts:
                log_or_raise(msg)
            return False

        return True

    validate_resource_conflicts()  # nie przerywamy, tylko zbieramy błędy

    # -------------------------------
    # VALIDATE SYSTEM STATE (/dev nodes)
    # -------------------------------
    def validate_system_state():
        # I2C
        if "i2c" in peripherals_cfg and isinstance(peripherals_cfg["i2c"], dict):
            i2c_cfg = peripherals_cfg["i2c"]
            bus = i2c_cfg.get("bus", 1)
            dev = f"/dev/i2c-{bus}"

            if not _dev_exists(dev):
                log_or_raise(f"I2C bus {bus} is not enabled in system (missing {dev}).")

        # SPI
        if "spi" in peripherals_cfg and isinstance(peripherals_cfg["spi"], dict):
            spi_cfg = peripherals_cfg["spi"]
            bus = spi_cfg.get("bus", 0)
            device = spi_cfg.get("device", 0)
            dev = f"/dev/spidev{bus}.{device}"

            if not _dev_exists(dev):
                log_or_raise(f"SPI {bus}.{device} is not enabled in system (missing {dev}).")

        # UART (tylko wewnętrzne)
        if "uart" in peripherals_cfg and isinstance(peripherals_cfg["uart"], dict):
            uart_cfg = peripherals_cfg["uart"]
            port = uart_cfg.get("port", "/dev/serial0")

            if port in VALID_UART_INTERNAL_PORTS and not _dev_exists(port):
                log_or_raise(f"UART port {port} is not available in system (missing device).")

    validate_system_state()  # również nie przerywamy

    peripherals = []
    protocols = []

    # ---------------------------------------------
    # AUTO-DETECT KERNEL ONE-WIRE
    # ---------------------------------------------
    kernel_w1_pin = _detect_kernel_onewire_pin()
    if kernel_w1_pin is not None:
        if logger:
            logger.log(f"[INFO] Kernel 1-Wire detected on GPIO{kernel_w1_pin}")
        peripherals.append(
            RPiOneWire(
                pin=kernel_w1_pin,
                logger=logger,
                logging_enabled=True,
            )
        )

    # ---------------------------------------------
    # PROTOKOŁY – MODBUS
    # ---------------------------------------------
    if "modbus" in protocols_cfg:
        modbus_config = protocols_cfg["modbus"]
        if isinstance(modbus_config, dict):
            port = modbus_config.get("port", "/dev/ttyUSB0")
            baudrate = modbus_config.get("baudrate", 9600)
            parity_char = modbus_config.get("parity", "N")
            stopbits_val = modbus_config.get("stopbits", 1)
            timeout = modbus_config.get("timeout", 1)

            if not isinstance(baudrate, int) or baudrate <= 0:
                log_or_raise(f"Invalid Modbus baudrate: {baudrate}")
            elif parity_char not in ("N", "E", "O"):
                log_or_raise(f"Invalid Modbus parity: {parity_char}")
            elif stopbits_val not in (1, 2):
                log_or_raise(f"Invalid Modbus stopbits: {stopbits_val}")
            elif not isinstance(timeout, (int, float)) or timeout < 0:
                log_or_raise(f"Invalid Modbus timeout: {timeout}")
            else:
                protocols.append(
                    ModbusRTU(
                        port=port,
                        baudrate=baudrate,
                        parity=parity_char,
                        stopbits=stopbits_val,
                        timeout=timeout,
                        logger=logger,
                        logging_enabled=True,
                    )
                )
        else:
            log_or_raise(
                "Invalid configuration for Modbus – expected dictionary.",
            )

    # ---------------------------------------------
    # UART
    # ---------------------------------------------
    parity_map = {
        "N": serial.PARITY_NONE,
        "E": serial.PARITY_EVEN,
        "O": serial.PARITY_ODD,
    }
    stopbits_map = {1: serial.STOPBITS_ONE, 2: serial.STOPBITS_TWO}

    if "uart" in peripherals_cfg:
        uart_config = peripherals_cfg["uart"]
        if isinstance(uart_config, dict):
            port = uart_config.get("port", "/dev/ttyUSB0")
            baudrate = uart_config.get("baudrate", 9600)
            parity_char = uart_config.get("parity", "N")
            stopbits_val = uart_config.get("stopbits", 1)
            timeout = uart_config.get("timeout", 1)

            if not (port in VALID_UART_INTERNAL_PORTS or _is_usb_uart_port(port)):
                log_or_raise(f"Invalid UART port: {port}")
            elif not isinstance(baudrate, int) or baudrate <= 0:
                log_or_raise(f"Invalid UART baudrate: {baudrate}")
            elif parity_char not in parity_map:
                log_or_raise(f"Invalid UART parity: {parity_char}")
            elif stopbits_val not in stopbits_map:
                log_or_raise(f"Invalid UART stopbits: {stopbits_val}")
            elif not isinstance(timeout, (int, float)) or timeout < 0:
                log_or_raise(f"Invalid UART timeout: {timeout}")
            else:
                # Konflikt z kernelowym UART (tylko dla portów wewnętrznych)
                if port in VALID_UART_INTERNAL_PORTS:
                    required_pins = (
                        RPiUART(port=port, baudrate=baudrate)
                        .get_required_resources()
                        .get("pins", [])
                    )
                    if not check_gpio_conflicts(f"UART {port}", required_pins):
                        # nie dodajemy UART, ale walidacja idzie dalej
                        pass
                    else:
                        peripherals.append(
                            RPiUART(
                                port=port,
                                baudrate=baudrate,
                                parity=parity_map[parity_char],
                                stopbits=stopbits_map[stopbits_val],
                                timeout=timeout,
                                logger=logger,
                                logging_enabled=True,
                            )
                        )
                else:
                    # USB/UART bez konfliktu GPIO
                    peripherals.append(
                        RPiUART(
                            port=port,
                            baudrate=baudrate,
                            parity=parity_map[parity_char],
                            stopbits=stopbits_map[stopbits_val],
                            timeout=timeout,
                            logger=logger,
                            logging_enabled=True,
                        )
                    )
        else:
            log_or_raise(
                "Invalid configuration for UART – expected dictionary.",
            )

    # ---------------------------------------------
    # GPIO
    # ---------------------------------------------
    if "gpio" in peripherals_cfg:
        used_gpio_names: set[str] = set()
        combined_gpio_config: dict[int, dict] = {}
        for gpio_config in peripherals_cfg["gpio"]:
            if not isinstance(gpio_config, dict):
                log_or_raise(
                    "Invalid GPIO configuration format – expected dictionary.",
                )
                continue
            try:
                GPIO_mod = RPiGPIO.get_gpio_interface()
                pin = int(gpio_config["pin"])
                mode_str = gpio_config["mode"].upper()
                initial_str = gpio_config.get("initial", "LOW").upper()
                name = gpio_config.get("name")
                if name is not None:
                    if not isinstance(name, str) or not name.strip():
                        log_or_raise(f"Invalid GPIO name for pin {pin}: {name}", warning=True)
                        name = None
                    else:
                        normalized_name = name.strip().lower()
                        if normalized_name in used_gpio_names:
                            log_or_raise(f"Duplicate GPIO name detected: {name}", warning=True)
                            name = None
                        else:
                            used_gpio_names.add(normalized_name)

                if pin not in VALID_GPIO_PINS:
                    log_or_raise(f"Invalid GPIO pin: {pin}")
                    continue

                mode = (
                    GPIO_mod.IN
                    if mode_str in ("IN", "GPIO.IN")
                    else GPIO_mod.OUT if mode_str in ("OUT", "GPIO.OUT") else None
                )
                initial = (
                    GPIO_mod.LOW
                    if initial_str in ("LOW", "GPIO.LOW")
                    else GPIO_mod.HIGH if initial_str in ("HIGH", "GPIO.HIGH") else None
                )

                if mode is None:
                    log_or_raise(f"Invalid GPIO mode: {mode_str}", warning=True)
                    continue
                if initial is None:
                    log_or_raise(f"Invalid GPIO initial value: {initial_str}", warning=True)
                    continue

                if not check_gpio_conflicts("GPIO", [pin]):
                    continue

                combined_gpio_config[pin] = {
                    "mode": mode,
                    "initial": initial,
                    "name": name,
                }
            except Exception as e:
                log_or_raise(
                    f"Invalid GPIO config: {gpio_config} – {e}",
                )

        if combined_gpio_config:
            RPiGPIO.register_label_constants(combined_gpio_config)
            peripherals.append(
                RPiGPIO(
                    pin_config=combined_gpio_config,
                    logger=logger,
                    logging_enabled=True,
                )
            )

    # ---------------------------------------------
    # SOFTWARE PWM
    # ---------------------------------------------
    if "pwm" in peripherals_cfg:
        for pwm_config in peripherals_cfg["pwm"]:
            if not isinstance(pwm_config, dict):
                log_or_raise(
                    "Invalid PWM configuration format – expected dictionary.",
                )
                continue
            try:
                pin = pwm_config["pin"]
                frequency = pwm_config.get("frequency", 1000)

                if not isinstance(pin, int) or pin not in VALID_GPIO_PINS:
                    log_or_raise(f"Invalid PWM pin: {pin}")
                    continue
                if not isinstance(frequency, (int, float)) or frequency <= 0:
                    log_or_raise(f"Invalid PWM frequency: {frequency}")
                    continue

                if not check_gpio_conflicts("software PWM", [pin]):
                    continue

                peripherals.append(
                    RPiPWM(
                        pin=pin,
                        frequency=frequency,
                        logger=logger,
                        logging_enabled=True,
                    )
                )
            except Exception as e:
                log_or_raise(
                    f"Invalid PWM configuration: {pwm_config} – {e}",
                )

    # ---------------------------------------------
    # I2C
    # ---------------------------------------------
    if "i2c" in peripherals_cfg:
        i2c_config = peripherals_cfg["i2c"]
        if isinstance(i2c_config, dict):
            bus_number = i2c_config.get("bus", 1)
            frequency = i2c_config.get("frequency", 100000)

            if not isinstance(bus_number, int) or bus_number < 0:
                log_or_raise(f"Invalid I2C bus number: {bus_number}")
            elif bus_number not in (0, 1, 3, 4, 5, 6) and bus_number < 10:
                log_or_raise(
                    f"Invalid I2C bus for Raspberry Pi: {bus_number} "
                    "(only 0,1,3,4,5,6 or >=10 for external adapters are allowed)"
                )
            elif not isinstance(frequency, int) or frequency <= 0:
                log_or_raise(f"Invalid I2C frequency: {frequency}")
            else:
                if bus_number in (0, 1, 3, 4, 5, 6):
                    required = RPiI2C(
                        bus_number=bus_number, frequency=frequency
                    ).get_required_resources()
                    pins = required.get("pins", [])
                    if not check_gpio_conflicts(f"I2C bus {bus_number}", pins):
                        pass
                    else:
                        peripherals.append(
                            RPiI2C(
                                bus_number=bus_number,
                                frequency=frequency,
                                logger=logger,
                                logging_enabled=True,
                            )
                        )
                else:
                    # zewnętrzne adaptery I2C (np. USB) – bez konfliktów GPIO
                    peripherals.append(
                        RPiI2C(
                            bus_number=bus_number,
                            frequency=frequency,
                            logger=logger,
                            logging_enabled=True,
                        )
                    )
        else:
            log_or_raise(
                "Invalid configuration for I2C – expected dictionary.",
            )

    # ---------------------------------------------
    # SPI
    # ---------------------------------------------
    if "spi" in peripherals_cfg:
        spi_config = peripherals_cfg["spi"]
        if isinstance(spi_config, dict):
            bus = spi_config.get("bus", 0)
            device = spi_config.get("device", 0)
            max_speed_hz = spi_config.get("max_speed_hz", 50000)
            mode = spi_config.get("mode", 0)
            bits_per_word = spi_config.get("bits_per_word", 8)
            cs_high = spi_config.get("cs_high", False)
            lsbfirst = spi_config.get("lsbfirst", False)

            if not isinstance(bus, int) or bus < 0:
                log_or_raise(f"Invalid SPI bus: {bus}")
            elif not isinstance(device, int) or device < 0:
                log_or_raise(f"Invalid SPI device (chip select): {device}")
            elif bus == 0 and device not in (0, 1):
                log_or_raise(
                    f"Invalid SPI device for SPI0: CE{device} "
                    "(only CE0=0 and CE1=1 are available on-board)"
                )
            elif bus in (1, 2) and device not in (0, 1, 2):
                log_or_raise(
                    f"Invalid SPI device for SPI{bus}: CE{device} "
                    "(only CE0=0, CE1=1, CE2=2 are available on-board)"
                )
            elif not isinstance(max_speed_hz, int) or max_speed_hz <= 0:
                log_or_raise(f"Invalid SPI max_speed_hz: {max_speed_hz}")
            elif mode not in (0, 1, 2, 3):
                log_or_raise(f"Invalid SPI mode: {mode}")
            elif not isinstance(bits_per_word, int) or bits_per_word <= 0:
                log_or_raise(f"Invalid SPI bits_per_word: {bits_per_word}")
            elif not isinstance(cs_high, bool):
                log_or_raise(f"Invalid SPI cs_high (must be bool): {cs_high}")
            elif not isinstance(lsbfirst, bool):
                log_or_raise(f"Invalid SPI lsbfirst (must be bool): {lsbfirst}")
            else:
                required = RPiSPI(
                    bus=bus,
                    device=device,
                    max_speed_hz=max_speed_hz,
                    mode=mode,
                    bits_per_word=bits_per_word,
                    cs_high=cs_high,
                    lsbfirst=lsbfirst,
                ).get_required_resources()
                pins = required.get("pins", [])
                if not check_gpio_conflicts(f"SPI{bus}.{device}", pins):
                    pass
                else:
                    peripherals.append(
                        RPiSPI(
                            bus=bus,
                            device=device,
                            max_speed_hz=max_speed_hz,
                            mode=mode,
                            bits_per_word=bits_per_word,
                            cs_high=cs_high,
                            lsbfirst=lsbfirst,
                            logger=logger,
                            logging_enabled=True,
                        )
                    )
        else:
            log_or_raise(
                "Invalid configuration for SPI – expected dictionary.",
            )

    # ---------------------------------------------
    # HARDWARE PWM
    # ---------------------------------------------
    if "hardware_pwm" in peripherals_cfg:
        for hpw_config in peripherals_cfg["hardware_pwm"]:
            if not isinstance(hpw_config, dict):
                log_or_raise(
                    "Invalid Hardware PWM format – expected dictionary.",
                )
                continue
            try:
                pin = hpw_config["pin"]
                frequency = hpw_config.get("frequency", 1000)

                if not isinstance(pin, int) or pin not in VALID_GPIO_PINS:
                    log_or_raise(f"Invalid Hardware PWM pin: {pin}")
                    continue
                if pin not in HARDWARE_PWM_PINS:
                    log_or_raise(f"Pin {pin} does not support hardware PWM on Raspberry Pi.")
                    continue
                if not isinstance(frequency, (int, float)) or frequency <= 0:
                    log_or_raise(f"Invalid Hardware PWM frequency: {frequency}")
                    continue

                if not check_gpio_conflicts("hardware PWM", [pin]):
                    continue

                peripherals.append(
                    RPiHardwarePWM(
                        pin=pin,
                        frequency=frequency,
                        logger=logger,
                        logging_enabled=True,
                    )
                )
            except Exception as e:
                log_or_raise(
                    f"Invalid Hardware PWM config: {hpw_config} – {e}",
                )

    # ---------------------------------------------
    # 1-WIRE (YAML-LEVEL)
    # ---------------------------------------------
    if "onewire" in peripherals_cfg:

        ow_cfg = peripherals_cfg["onewire"]

        # Dozwolone są tylko:
        # onewire: true
        # onewire: {}
        if ow_cfg not in (True, {}, None):
            log_or_raise(
                "Invalid configuration for 1-Wire – expected 'onewire: true' or 'onewire: {}'. "
                "Pin configuration is not allowed.",
            )
        else:
            # Kernel musi wystawić w1-gpio. Jeśli nie → ERROR.
            kernel_w1_pin_yaml = _detect_kernel_onewire_pin()
            if kernel_w1_pin_yaml is None:
                log_or_raise(
                    "1-Wire is defined in configuration, but kernel 1-Wire driver (w1-gpio) is not active. "
                    "Please enable dtoverlay=w1-gpio in config.txt."
                )
            else:
                if check_gpio_conflicts("1-Wire", [kernel_w1_pin_yaml]):
                    peripherals.append(
                        RPiOneWire(
                            pin=kernel_w1_pin_yaml,
                            logger=logger,
                            logging_enabled=True,
                        )
                    )

    # ---------------------------------------------
    # FINAL DECISION
    # ---------------------------------------------
    if errors_occurred:
        if logger:
            logger.log(
                "[ERROR] ❌ Peripheral configuration contains one or more errors. Aborting.",
                to_console=True,
                to_log_file=False,
            )
        else:
            print("[ERROR] ❌ Peripheral configuration contains one or more errors. Aborting.")
        return None

    return {
        "peripherals": peripherals,
        "protocols": protocols,
    }
