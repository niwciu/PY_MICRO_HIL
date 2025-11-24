from abc import ABC, abstractmethod


class Peripheral(ABC):
    @abstractmethod
    def initialize(self):
        pass

    @abstractmethod
    def release(self):
        pass


# TODO: Define peripheral classes for hardware other than that available on RPi.
# In general, this module should be used when the framework is running on non-RPi hardware,
# but it can also be used with RPi if any external devices are connected.

# Example:
#
# class USBVoltageMeter(Peripheral):
#     def __init__(self, port="/dev/ttyUSB0"):
#         self.port = port
#         self.connected = False
#         self.handle = None
#
#     def initialize(self):
#         # Simulate opening serial connection to voltage meter
#         self.handle = open(self.port, 'rb')
#         self.connected = True
#         print(f"USBVoltageMeter initialized on {self.port}")
#
#     def release(self):
#         if self.handle:
#             self.handle.close()
#             self.connected = False
#             print("USBVoltageMeter connection closed.")
