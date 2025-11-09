from pathlib import Path

def is_raspberry_pi() -> bool:
    try:
        with open("/proc/cpuinfo", "r") as f:
            content = f.read().lower()
        return "raspberry pi" in content or "bcm" in content
    except FileNotFoundError:
        return False
