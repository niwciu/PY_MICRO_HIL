import yaml
from core.RPiPeripherals import RPiGPIO, RPiPWM, RPiUART, RPiI2C, RPiSPI, RPi1Wire, RPiADC, RPiCAN, RPiHardwarePWM
from core.protocols import ModbusRTU
import RPi.GPIO as GPIO

def load_peripheral_configuration(yaml_file='peripherals_config.yaml'):
    """
    Ładuje konfigurację peryferiów z pliku YAML.
    :param yaml_file: Ścieżka do pliku YAML.
    :return: Zwraca słownik z peryferiami i protokołami do załadowania.
    """
    with open(yaml_file, 'r') as f:
        config = yaml.safe_load(f)  # Załadowanie pliku YAML
    
    peripherals = []
    protocols = []

# Modbus Protocol
    if 'modbus' in config.get('protocols', {}):
        modbus_config = config['protocols']['modbus']
        if isinstance(modbus_config, dict):
            # Pobieramy wszystkie parametry z konfiguracji
            port = modbus_config.get('port', '/dev/ttyUSB0')  # Domyślnie '/dev/ttyUSB0'
            baudrate = modbus_config.get('baudrate', 9600)     # Domyślnie 9600
            parity = modbus_config.get('parity', 'N')          # Domyślnie 'N' (None)
            stopbits = modbus_config.get('stopbits', 1)        # Domyślnie 1
            timeout = modbus_config.get('timeout', 1)          # Domyślnie 1 sekunda
            
            # Tworzymy obiekt ModbusTRU z pełną konfiguracją
            modbus = ModbusRTU(port=port, baudrate=baudrate, 
                            parity=parity, stopbits=stopbits, timeout=timeout)
            protocols.append(modbus)
        else:
            raise ValueError("Invalid configuration for Modbus, expected dictionary with key 'port'.")

    # UART
    if 'uart' in config.get('peripherals', {}):
        uart_config = config['peripherals']['uart']
        if isinstance(uart_config, dict):
            # Pobieramy wszystkie parametry z konfiguracji
            port = uart_config.get('port', '/dev/ttyUSB0')  # Domyślnie '/dev/ttyUSB0'
            baudrate = uart_config.get('baudrate', 9600)     # Domyślnie 9600
            parity = uart_config.get('parity', 'N')          # Domyślnie 'N' (None)
            stopbits = uart_config.get('stopbits', 1)        # Domyślnie 1
            timeout = uart_config.get('timeout', 1)          # Domyślnie 1 sekunda
            
            uart = RPiUART(port=port, baudrate=baudrate, 
                            parity=parity, stopbits=stopbits, timeout=timeout)
            peripherals.append(uart)
        else:
            raise ValueError("Invalid configuration for UART, expected dictionary with keys 'port' and 'baudrate'.")

    # GPIO
    if 'gpio' in config.get('peripherals', {}):
        for gpio_config in config['peripherals']['gpio']:
            if isinstance(gpio_config, dict):
                if 'pin' in gpio_config and 'mode' in gpio_config:  # Sprawdzenie poprawności słownika
                    pin = int(gpio_config.get('pin'))  # Konwersja na int, jeśli to string
                    mode_str = gpio_config.get('mode').upper()  # Upewnij się, że jest to wielkimi literami
                    initial_str = gpio_config.get('initial', 'LOW').upper()  # Domyślnie 'LOW' jeśli brak

                    # Parsowanie 'mode'
                    if mode_str == "IN" or mode_str == "in" or mode_str == "GPIO.IN": 
                        mode = GPIO.IN
                    elif mode_str == "OUT" or mode_str == "out"or mode_str == "GPIO.OUT":
                        mode = GPIO.OUT
                    else:
                        raise ValueError(f"Invalid GPIO mode: {mode_str}")

                    # Parsowanie 'initial'
                    if initial_str == "LOW" or initial_str == "low" or initial_str == "GPIO.LOW" :
                        initial = GPIO.LOW
                    elif initial_str == "HIGH" or initial_str == "high" or initial_str == "GPIO.HIGH":
                        initial = GPIO.HIGH
                    else:
                        raise ValueError(f"Invalid GPIO initial value: {initial_str}")

                    # Tworzenie GPIO
                    gpio = RPiGPIO(pin_config={pin: {'mode': mode, 'initial': initial}})
                    peripherals.append(gpio)
                else:
                    raise ValueError("Invalid GPIO configuration, 'pin' and 'mode' are required.")
            else:
                raise ValueError("Invalid configuration for GPIO, expected dictionary.")

    # PWM
    if 'pwm' in config.get('peripherals', {}):
        for pwm_config in config['peripherals']['pwm']:
            if isinstance(pwm_config, dict):
                pwm = RPiPWM(pwm_config['pin'], pwm_config.get('frequency', 1000))
                peripherals.append(pwm)
            else:
                raise ValueError("Invalid configuration for PWM, expected dictionary with keys 'pin' and 'frequency'.")

    # I2C
    if 'i2c' in config.get('peripherals', {}):
        i2c_config = config['peripherals']['i2c']
        if isinstance(i2c_config, dict):
            i2c = RPiI2C(i2c_config.get('bus', 1),i2c_config.get('frequency', 100000))
            peripherals.append(i2c)
        else:
            raise ValueError("Invalid configuration for I2C, expected dictionary with key 'bus'.")

    # SPI
    if 'spi' in config.get('peripherals', {}):
        spi_config = config['peripherals']['spi']
        if isinstance(spi_config, dict):
            bus = spi_config.get('bus', 0)  # Numer magistrali SPI (0 lub 1)
            device = spi_config.get('device', 0)  # Numer urządzenia (0 lub 1)
            max_speed_hz = spi_config.get('max_speed_hz', 50000)  # Maksymalna prędkość transmisji
            mode = spi_config.get('mode', 0)  # Tryb SPI (0-3)
            bits_per_word = spi_config.get('bits_per_word', 8)  # Liczba bitów na słowo
            cs_high = spi_config.get('cs_high', False)  # Czy linia Chip Select jest aktywna na wysokim poziomie
            lsbfirst = spi_config.get('lsbfirst', False)  # Czy bity są przesyłane od najmniej znaczącego bitu
            timeout = spi_config.get('timeout', 1)  # Czas oczekiwania na odpowiedź

            # Tworzenie instancji SPI z odpowiednimi parametrami
            spi = RPiSPI(bus=bus, device=device, max_speed_hz=max_speed_hz, mode=mode,
                        bits_per_word=bits_per_word, cs_high=cs_high, lsbfirst=lsbfirst, timeout=timeout)
            peripherals.append(spi)
        else:
            raise ValueError("Invalid configuration for SPI, expected dictionary with keys 'bus', 'device', and other SPI parameters.")

    # # CAN
    # if 'can' in config.get('peripherals', {}):
    #     can_config = config['peripherals']['can']
    #     if isinstance(can_config, dict):
    #         can = RPiCAN(can_config['interface'])
    #         peripherals.append(can)
    #     else:
    #         raise ValueError("Invalid configuration for CAN, expected dictionary with key 'interface'.")

    # # ADC
    # if 'adc' in config.get('peripherals', {}):
    #     adc_config = config['peripherals']['adc']
    #     if isinstance(adc_config, dict):
    #         adc = RPiADC(adc_config['channel'])
    #         peripherals.append(adc)
    #     else:
    #         raise ValueError("Invalid configuration for ADC, expected dictionary with key 'channel'.")

    # # EEPROM
    # if 'eeprom' in config.get('peripherals', {}):
    #     eeprom_config = config['peripherals']['eeprom']
    #     if isinstance(eeprom_config, dict):
    #         eeprom = RPiHATEEPROM(eeprom_config['bus'], eeprom_config['address'])
    #         peripherals.append(eeprom)
    #     else:
    #         raise ValueError("Invalid configuration for EEPROM, expected dictionary with keys 'bus' and 'address'.")



    # Return final dictionaries for peripherals and protocols
    return {
        "peripherals": peripherals,
        "protocols": protocols
    }
