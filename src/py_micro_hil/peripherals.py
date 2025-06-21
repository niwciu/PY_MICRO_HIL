
from abc import ABC, abstractmethod

class Peripheral(ABC):
    @abstractmethod
    def initialize(self):
        pass

    @abstractmethod
    def release(self):
        pass

class SPI(Peripheral):
    def initialize(self):
        print("Initializing SPI...")

    def release(self):
        print("Releasing SPI...")
