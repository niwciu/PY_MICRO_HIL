
def is_raspberry_pi() -> bool:
    """Check if we are running on a Raspberry Pi."""
    try:
        with open("/proc/device-tree/model", "r") as f:
            model = f.read().lower()
        return "raspberry pi" in model
    except Exception:
        return False