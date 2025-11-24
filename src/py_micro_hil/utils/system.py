def is_raspberry_pi() -> bool:
    """Sprawdza, czy skrypt działa na Raspberry Pi."""
    try:
        with open("/proc/device-tree/model", "r") as f:
            model = f.read().lower()
        return "raspberry pi" in model
    except Exception:
        return False
