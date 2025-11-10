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
)
from py_micro_hil.peripherals.modbus import ModbusRTU
from py_micro_hil.utils.system import is_raspberry_pi


def load_peripheral_configuration(yaml_file=None, logger=None):
    """
    Loads peripheral configuration from a YAML file.
    If no path is provided, looks in the current working directory.

    :param yaml_file: Optional path to the YAML file.
    :param logger: Optional logger instance (uses .log()).
    :return: Dictionary with 'peripherals' and 'protocols' lists.
    """

    def log_or_raise(msg, warning=False):
        tag = "[WARNING]" if warning else "[ERROR]"
        if logger:
            logger.log(f"{tag} {msg}", to_console=True, to_log_file=not warning)
        else:
            print(f"{tag} {msg}")

    # 0) sprawdz czy pracujesz na RPi i wyslij info
    if not is_raspberry_pi():
        log_or_raise("Running outside Raspberry Pi — using dummy RPi hardware interfaces.", warning=True)
    # 1) Znajdź plik YAML
    if yaml_file is None:
        yaml_file = Path.cwd() / "peripherals_config.yaml"
    else:
        yaml_file = Path(yaml_file)

    if not yaml_file.exists():
        msg = f"Peripheral config file not found: {yaml_file.resolve()}"
        log_or_raise(f"{msg}", warning=False)
        return None


    # 2) Parsuj YAML
    try:
        with yaml_file.open("r") as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        log_or_raise(f"Failed to parse YAML: {e}", warning=False)
        return None

    # 3) Pusta lub niepoprawna struktura lub brak 
    if config is None:
        log_or_raise("Peripheral configuration file is empty.", warning=False)
        config = {}
        return None
    if not isinstance(config, dict):
        log_or_raise("YAML content must be a dictionary at the top level.", warning=False)
        return None

    peripherals_cfg = config.get("peripherals") or {}
    protocols_cfg   = config.get("protocols")   or {}

    peripherals = []
    protocols   = []

    # --- Protokoły ---
    if "modbus" in protocols_cfg:
        modbus_config = protocols_cfg["modbus"]
        if isinstance(modbus_config, dict):
            protocols.append(ModbusRTU(
                port=modbus_config.get("port",    "/dev/ttyUSB0"),
                baudrate=modbus_config.get("baudrate", 9600),
                parity=modbus_config.get("parity",   "N"),
                stopbits=modbus_config.get("stopbits", 1),
                timeout=modbus_config.get("timeout",  1)
            ))
        else:
            log_or_raise("Invalid configuration for Modbus – expected dictionary.", warning=True)

     # --- UART ---
    parity_map   = {"N": serial.PARITY_NONE, "E": serial.PARITY_EVEN, "O": serial.PARITY_ODD}
    stopbits_map = {1: serial.STOPBITS_ONE, 2: serial.STOPBITS_TWO}

    if "uart" in peripherals_cfg:
        uart_config = peripherals_cfg["uart"]
        if isinstance(uart_config, dict):
            peripherals.append(RPiUART(
                port=uart_config.get("port","/dev/ttyUSB0"),
                baudrate=uart_config.get("baudrate", 9600),
                parity=parity_map.get(uart_config.get("parity", "N"), serial.PARITY_NONE),
                stopbits=stopbits_map.get(uart_config.get("stopbits", 1), serial.STOPBITS_ONE),
                timeout=uart_config.get("timeout", 1),
                logger=logger,
                logging_enabled=True
            ))
        else:
            log_or_raise("Invalid configuration for UART – expected dictionary.", warning=True)

    # --- GPIO ---
    if "gpio" in peripherals_cfg:
        for gpio_config in peripherals_cfg["gpio"]:
            if not isinstance(gpio_config, dict):
                log_or_raise("Invalid GPIO configuration format – expected dictionary.", warning=True)
                continue
            try:
                GPIO = RPiGPIO.get_gpio_interface()
                pin         = int(gpio_config["pin"])
                mode_str    = gpio_config["mode"].upper()
                initial_str = gpio_config.get("initial", "LOW").upper()

                mode = (
                    GPIO.IN  if mode_str in ("IN",  "GPIO.IN")  else
                    GPIO.OUT if mode_str in ("OUT", "GPIO.OUT") else None
                )
                initial = (
                    GPIO.LOW  if initial_str in ("LOW",  "GPIO.LOW")  else
                    GPIO.HIGH if initial_str in ("HIGH", "GPIO.HIGH") else None
                )

                if mode    is None:
                    log_or_raise(f"Invalid GPIO mode: {mode_str}", warning=True)
                    continue
                if initial is None:
                    log_or_raise(f"Invalid GPIO initial value: {initial_str}", warning=True)
                    continue

                peripherals.append(RPiGPIO(
                    pin_config={ pin: {"mode": mode, "initial": initial} },
                    logger=logger,
                    logging_enabled=True
                ))
            except Exception as e:
                log_or_raise(f"Invalid GPIO config: {gpio_config} – {e}", warning=True)

    # --- Software PWM ---
    if "pwm" in peripherals_cfg:
        for pwm_config in peripherals_cfg["pwm"]:
            if not isinstance(pwm_config, dict):
                log_or_raise("Invalid PWM configuration format – expected dictionary.", warning=True)
                continue
            try:
                peripherals.append(RPiPWM(
                    pin=pwm_config["pin"],
                    frequency=pwm_config.get("frequency", 1000),
                    logger=logger,
                    logging_enabled=True
                ))
            except Exception as e:
                log_or_raise(f"Invalid PWM configuration: {pwm_config} – {e}", warning=True)

    # --- I2C ---
    if "i2c" in peripherals_cfg:
        i2c_config = peripherals_cfg["i2c"]
        if isinstance(i2c_config, dict):
            peripherals.append(RPiI2C(
                bus_number = i2c_config.get("bus",       1),
                frequency  = i2c_config.get("frequency",100000),
                logger     = logger,
                logging_enabled=True
            ))
        else:
            log_or_raise("Invalid configuration for I2C – expected dictionary.", warning=True)

    # --- SPI ---
    if "spi" in peripherals_cfg:
        spi_config = peripherals_cfg["spi"]
        if isinstance(spi_config, dict):
            peripherals.append(RPiSPI(
                bus          = spi_config.get("bus",          0),
                device       = spi_config.get("device",       0),
                max_speed_hz = spi_config.get("max_speed_hz",50000),
                mode         = spi_config.get("mode",         0),
                bits_per_word= spi_config.get("bits_per_word",8),
                cs_high      = spi_config.get("cs_high",     False),
                lsbfirst     = spi_config.get("lsbfirst",    False),
                logger       = logger,
                logging_enabled=True
            ))
        else:
            log_or_raise("Invalid configuration for SPI – expected dictionary.", warning=True)

    # --- Hardware PWM ---
    if "hardware_pwm" in peripherals_cfg:
        for hpw_config in peripherals_cfg["hardware_pwm"]:
            if not isinstance(hpw_config, dict):
                log_or_raise("Invalid Hardware PWM format – expected dictionary.", warning=True)
                continue
            try:
                peripherals.append(RPiHardwarePWM(
                    pin              = hpw_config["pin"],
                    frequency        = hpw_config.get("frequency", 1000),
                    logger           = logger,
                    logging_enabled  = True
                ))
            except Exception as e:
                log_or_raise(f"Invalid Hardware PWM config: {hpw_config} – {e}", warning=True)

    return {
        "peripherals": peripherals,
        "protocols":   protocols,
    }
