import yaml
from pathlib import Path
from py_micro_hil.RPiPeripherals import (
    RPiGPIO, RPiPWM, RPiUART, RPiI2C, RPiSPI,
    RPi1Wire, RPiADC, RPiCAN, RPiHardwarePWM
)
from py_micro_hil.protocols import ModbusRTU
import RPi.GPIO as GPIO


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
        if not warning:
            raise ValueError(f"{tag} {msg}")

    if yaml_file is None:
        yaml_file = Path.cwd() / "peripherals_config.yaml"
    else:
        yaml_file = Path(yaml_file)

    if not yaml_file.exists():
        log_or_raise(f"Peripheral config file not found: {yaml_file.resolve()}", warning=False)

    try:
        with yaml_file.open("r") as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        log_or_raise(f"Failed to parse YAML: {e}", warning=False)

    if config is None:
        log_or_raise("Peripheral configuration file is empty – using default empty configuration.", warning=True)
        config = {}

    if not isinstance(config, dict):
        log_or_raise("YAML content must be a dictionary at the top level.", warning=False)

    peripherals_cfg = config.get("peripherals") or {}
    protocols_cfg = config.get("protocols") or {}

    peripherals = []
    protocols = []

    # --- Modbus ---
    if "modbus" in protocols_cfg:
        modbus_config = protocols_cfg["modbus"]
        if isinstance(modbus_config, dict):
            protocols.append(ModbusRTU(
                port=modbus_config.get("port", "/dev/ttyUSB0"),
                baudrate=modbus_config.get("baudrate", 9600),
                parity=modbus_config.get("parity", "N"),
                stopbits=modbus_config.get("stopbits", 1),
                timeout=modbus_config.get("timeout", 1)
            ))
        else:
            log_or_raise("Invalid configuration for Modbus – expected dictionary.", warning=True)

    # --- UART ---
    if "uart" in peripherals_cfg:
        uart_config = peripherals_cfg["uart"]
        if isinstance(uart_config, dict):
            peripherals.append(RPiUART(
                port=uart_config.get("port", "/dev/ttyUSB0"),
                baudrate=uart_config.get("baudrate", 9600),
                parity=uart_config.get("parity", "N"),
                stopbits=uart_config.get("stopbits", 1),
                timeout=uart_config.get("timeout", 1)
            ))
        else:
            log_or_raise("Invalid configuration for UART – expected dictionary.", warning=True)

    # --- GPIO ---
    if "gpio" in peripherals_cfg:
        for gpio_config in peripherals_cfg["gpio"]:
            if isinstance(gpio_config, dict):
                try:
                    pin = int(gpio_config["pin"])
                    mode_str = gpio_config["mode"].upper()
                    initial_str = gpio_config.get("initial", "LOW").upper()

                    mode = GPIO.IN if mode_str in ("IN", "GPIO.IN") else GPIO.OUT if mode_str in ("OUT", "GPIO.OUT") else None
                    initial = GPIO.LOW if initial_str in ("LOW", "GPIO.LOW") else GPIO.HIGH if initial_str in ("HIGH", "GPIO.HIGH") else None

                    if mode is None:
                        log_or_raise(f"Invalid GPIO mode: {mode_str}", warning=True)
                        continue
                    if initial is None:
                        log_or_raise(f"Invalid GPIO initial value: {initial_str}", warning=True)
                        continue

                    peripherals.append(RPiGPIO(pin_config={pin: {"mode": mode, "initial": initial}}))
                except (KeyError, ValueError, TypeError) as e:
                    log_or_raise(f"Invalid GPIO config: {gpio_config} – {e}", warning=True)
            else:
                log_or_raise("Invalid GPIO configuration format – expected dictionary.", warning=True)

    # --- PWM ---
    if "pwm" in peripherals_cfg:
        for pwm_config in peripherals_cfg["pwm"]:
            if isinstance(pwm_config, dict):
                try:
                    pwm = RPiPWM(pwm_config["pin"], pwm_config.get("frequency", 1000))
                    peripherals.append(pwm)
                except Exception as e:
                    log_or_raise(f"Invalid PWM configuration: {pwm_config} – {e}", warning=True)
            else:
                log_or_raise("Invalid PWM configuration format – expected dictionary.", warning=True)

    # --- I2C ---
    if "i2c" in peripherals_cfg:
        i2c_config = peripherals_cfg["i2c"]
        if isinstance(i2c_config, dict):
            peripherals.append(RPiI2C(
                bus=i2c_config.get("bus", 1),
                frequency=i2c_config.get("frequency", 100000)
            ))
        else:
            log_or_raise("Invalid configuration for I2C – expected dictionary.", warning=True)

    # --- SPI ---
    if "spi" in peripherals_cfg:
        spi_config = peripherals_cfg["spi"]
        if isinstance(spi_config, dict):
            peripherals.append(RPiSPI(
                bus=spi_config.get("bus", 0),
                device=spi_config.get("device", 0),
                max_speed_hz=spi_config.get("max_speed_hz", 50000),
                mode=spi_config.get("mode", 0),
                bits_per_word=spi_config.get("bits_per_word", 8),
                cs_high=spi_config.get("cs_high", False),
                lsbfirst=spi_config.get("lsbfirst", False),
                timeout=spi_config.get("timeout", 1)
            ))
        else:
            log_or_raise("Invalid configuration for SPI – expected dictionary.", warning=True)

    # --- Optional peripherals (commented) ---

    # # CAN
    # if 'can' in peripherals_cfg:
    #     can_config = peripherals_cfg['can']
    #     if isinstance(can_config, dict):
    #         peripherals.append(RPiCAN(can_config['interface']))
    #     else:
    #         log_or_raise("Invalid configuration for CAN – expected dictionary.", warning=True)

    # # ADC
    # if 'adc' in peripherals_cfg:
    #     adc_config = peripherals_cfg['adc']
    #     if isinstance(adc_config, dict):
    #         peripherals.append(RPiADC(adc_config['channel']))
    #     else:
    #         log_or_raise("Invalid configuration for ADC – expected dictionary.", warning=True)

    # # EEPROM
    # if 'eeprom' in peripherals_cfg:
    #     eeprom_config = peripherals_cfg['eeprom']
    #     if isinstance(eeprom_config, dict):
    #         peripherals.append(RPiHATEEPROM(eeprom_config['bus'], eeprom_config['address']))
    #     else:
    #         log_or_raise("Invalid configuration for EEPROM – expected dictionary.", warning=True)

    return {
        "peripherals": peripherals,
        "protocols": protocols
    }
