# Py-Micro-HIL

> **Py-Micro-HIL** is a modular, lightweight **Hardware-in-the-Loop (HIL) testing framework** for Python.  
> It provides a unified interface for testing embedded systems, sensors, and communication buses  
> (Modbus RTU, SPI, I2C, UART, GPIO) both on **Raspberry Pi hardware** and in **PC simulation mode**.

---

## 🚀 Overview

**Py-Micro-HIL** enables automated functional and integration testing of embedded systems.  
It supports both **real hardware execution** on Raspberry Pi and **simulated environments** on any PC.

With this framework you can:
- Write and organize test suites for hardware peripherals.
- Interface with GPIO, SPI, I2C, UART, or Modbus RTU devices.
- Use mocks for offline or CI/CD testing.
- Generate structured HTML and console reports.
- Integrate easily with pipelines or GitHub Actions.

---

## 🔗 Documentation

📚 Full developer and user documentation is available here:  
➡️ [https://niwciu.github.io/PY_MICRO_HIL](https://niwciu.github.io/PY_MICRO_HIL)

---

## ⚙️ Installation

### 🧰 Option 1 – From PyPI (recommended for most users)

```bash
pip install py-micro-hil
```

### 🧪 Option 2 – From source (for contributors)

```bash
git clone https://github.com/niwciu/PY_MICRO_HIL.git
cd PY_MICRO_HIL
pip install -e .
```

> 💡 On your hil test server, you can use the flag `--break-system-packages` to simplify installation and usage for CI/CD environments:
> ```bash
> pip install py-micro-hil --break-system-packages
> ```
> It will make your life easier whe using it in services like GitHub Actions

### dependencies

```
pymodbus, pytest, smbus2, spidev, pyserial
```

### Developer setup

For development and contribution:

```bash
git clone https://github.com/niwciu/PY_MICRO_HIL.git
cd PY_MICRO_HIL
pip install -e .[dev]
```

---

## 🧩 Example usage

### 1️⃣ Create a configuration file

In the project root for your project hil tests main folder, create a file `peripherals_config.yaml`, for example:

```yaml
peripherals:
  gpio:
    - pin: 17
      mode: out
      initial: low
    - pin: 18
      mode: in
```

Full configuration reference:  
📖 [Configuration and YAML guide →](https://niwciu.github.io/PY_MICRO_HIL/configuration/)

---

### 2️⃣ Create test files

Create a directory named `hil_tests/` and add your test groups there.  
Each .py file should start it's name from **test** and represents a **test group**.

Example: `hil_tests/test_gpio_led.py`

```python
from py_micro_hil.assertions import *
from py_micro_hil.framework_API import *

def setup_group():
    TEST_INFO_MESSAGE("Setting up gpio led test group")

def teardown_group():
    TEST_INFO_MESSAGE("Tearing down gpio led test group")

def test_led_toggle():
    gpio = get_RPiGPIO_peripheral()
    gpio.write(17, 1)
    TEST_
    TEST_ASSERT_EQUAL (1, gpio.read(18))
```

---

### 3️⃣ Run the tests
Before running tests check available options by typing:
```bash
hiltests --help
```

Use the built-in **CLI runner**:

```bash
hiltests --config ./peripherals_config.yaml --test-dir ./hil_tests
```

Generate a starter group from the editable template without executing any tests:

```bash
hiltests --create-test-group gpio_smoke ./hil_tests
```

If both the YAML configuration and the `hil_tests` folder are in the same directory,  
simply open this directory and run:

```bash
hiltests
```

---

### 4️⃣ Generate reports

`Py-Micro-HIL` can generate both **console log files** and **HTML reports**.

Example:

```bash
hiltests --log ./reports/log.txt
```

or

```bash
hiltests --html ./reports/report.html
```

Reports can be customized with name and path.  
See: [Reports and Logging →](https://niwciu.github.io/PY_MICRO_HIL/reports/)

---

## 💡 Features

- ✅ Unified test structure (`TestFramework`, `TestGroup`, `Test`)  
- ✅ Automatic setup/teardown with context isolation  
- ✅ YAML-driven configuration system  
- ✅ Dynamic test discovery (`tests_group_factory`)  
- ✅ Mock peripherals for PC environment (not RPi) 
- ✅ Full logging and HTML report generation  
- ✅ Native CLI interface (`hiltests`)  
- ✅ Compatible with Raspberry Pi and Linux hosts  

---

## 🧰 Supported peripherals & protocols

| Peripheral | Class | Description |
|-------------|--------|-------------|
| **GPIO** | `RPiGPIO` | Digital I/O control |
| **PWM** | `RPiPWM`, `RPiHardwarePWM` | Software and hardware PWM |
| **UART** | `RPiUART` | Serial communication via `pyserial` |
| **I²C** | `RPiI2C` | SMBus-compatible interface |
| **SPI** | `RPiSPI` | SPI interface via `spidev` |
| **1-Wire** | `RPiOneWire` | DS18B20 temperature sensors via w1-gpio |
| **Modbus RTU** | `ModbusRTU` | RS-485 communication via `pymodbus` |

> 🧩 These are the currently implemented peripherals.  
> You can easily extend the framework by adding your own peripherals in the  
> `src/py_micro_hil/peripherals/` directory and implementing the required abstract interfaces.  
> The developer documentation includes full guidance on this process.

---

## 🤝 Contributing

We welcome contributions from the community!  
Please ensure your code follows **PEP-8** style and includes tests.

1. Fork this repository  
2. Clone and install in development mode:
   ```bash
   git clone <link to your fork>.git
   cd PY_MICRO_HIL
   pip install -e .[dev]
   ```
3. Create a new branch:
   ```bash
   git checkout -b feature/my-feature
   ```
4. Make your changes and test:
   ```bash
   pytest -v
   ```
5. Submit a pull request with a clear description and test coverage.

Full contribution guide:  
📘 [Developer Guide →](https://niwciu.github.io/PY_MICRO_HIL/contributing/)

---

## 📄 License

MIT License © 2025 – [@niwciu](https://github.com/niwciu)

---

<p align="center">
  <img src="https://github.com/user-attachments/assets/f4825882-e285-4e02-a75c-68fc86ff5716" alt="myEmbeddedWayBanner"><br>

</p>

---