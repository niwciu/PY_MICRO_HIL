# Raspberry Pi Peripheral Layer API Documentation

This document describes the public API surface of the Raspberry Pi hardware abstraction layer.

---

# Mixins

## LoggingMixin

### Constructor
```python
LoggingMixin(logger=None, logging_enabled=True)
```

### Methods
- `enable_logging()`
- `disable_logging()`
- `_log(message, level=logging.INFO)`

---

## ResourceMixin

### Methods
- `__enter__()`  
  Calls `.initialize()`  
- `__exit__()`  
  Calls `.release()`

---

# GPIO

## RPiGPIO_API (interface)

### Methods
- `write(pin, value)`
- `read(pin)`
- `toggle(pin)`
- `enable_logging()`
- `disable_logging()`

---

## RPiGPIO (implementation)

### Constructor
```python
RPiGPIO(pin_config, logger=None, logging_enabled=True)
```

### Methods
- `get_required_resources()`
- `initialize()`
- `write(pin, value)`
- `read(pin)`
- `toggle(pin)`
- `release()`
- `get_gpio_interface()` (static)

---

# Software PWM

## RPiPWM_API (interface)

Methods:
- `set_duty_cycle(value)`
- `set_frequency(value)`
- `enable_logging()`
- `disable_logging()`

## RPiPWM

Constructor:
```python
RPiPWM(pin, frequency=1000.0, logger=None, logging_enabled=True)
```

Methods:
- `get_required_resources()`
- `initialize()`
- `set_duty_cycle(value)`
- `set_frequency(value)`
- `release()`

---

# UART

## RPiUART_API

Methods:
- `initialize()`
- `send(data)`
- `receive(size=1)`
- `readline()`
- `release()`

## RPiUART

Constructor:
```python
RPiUART(port="/dev/serial0", baudrate=9600, timeout=1.0, parity=..., stopbits=..., logger=None)
```

Methods:
- `get_required_resources()`
- `initialize()`
- `get_initialized_params()`
- `send(data)`
- `receive(size)`
- `readline()`
- `release()`

---

# I2C

## RPiI2C_API

Methods:
- `scan()`
- `read(addr, reg, len)`
- `write(addr, reg, data)`
- `read_byte(addr)`
- `write_byte(addr, value)`
- `read_word(addr, reg)`
- `write_word(addr, reg, value)`
- `enable_logging()`
- `disable_logging()`

## RPiI2C

Constructor:
```python
RPiI2C(bus_number=1, frequency=100000, logger=None)
```

Methods as defined in the interface, plus:
- `get_required_resources()`
- `initialize()`
- `get_initialized_params()`
- `release()`

---

# SPI

## RPiSPI_API

Methods:
- `transfer(data)`
- `transfer_bytes(data)`
- `write_bytes(data)`
- `read_bytes(length)`
- `transfer2(data)`
- `enable_logging()`
- `disable_logging()`

## RPiSPI

Constructor:
```python
RPiSPI(bus=0, device=0, max_speed_hz=500000, mode=0, bits_per_word=8, ...)
```

Methods:
- `get_required_resources()`
- `initialize()`
- `get_initialized_params()`
- Full SPI API
- `release()`

---

# Hardware PWM

## RPiHardwarePWM_API
Methods:
- `set_duty_cycle()`
- `set_frequency()`

## RPiHardwarePWM

Constructor:
```python
RPiHardwarePWM(pin, frequency=1000.0, logger=None)
```

Methods:
- `get_required_resources()`
- `initialize()`
- `set_duty_cycle()`
- `set_frequency()`
- `release()`

