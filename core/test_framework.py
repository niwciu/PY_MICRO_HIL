# test_framework.py
from core.logger import Logger
from abc import ABC, abstractmethod
import sys 


class Peripheral(ABC):
    @abstractmethod
    def initialize(self):
        pass

    @abstractmethod
    def release(self):
        pass

class TestFramework:
    def __init__(self, peripheral_manager, logger):
        self.peripheral_manager = peripheral_manager
        self.test_groups = []
        self.total_tests = 0
        self.pass_count = 0
        self.fail_count = 0
        self.logger = logger

    def add_test_group(self, group):
        self.test_groups.append(group)

    def run_all_tests(self):
        log_line=("\n=================== INITIALIZATION ===================")
        self.logger.log(log_line, to_console=True)
        self.peripheral_manager.initialize_all()

        log_line="\n=================== TEST EXECUTION ===================\n"
        self.logger.log(log_line, to_console=True)
        if hasattr(self.logger, "log_file") and self.logger.log_file:
            self.logger.log(log_line, to_console=False, to_log_file = True)
        for group in self.test_groups:
            group.run_tests(self)

        log_line="\n==================== RESOURCE CLEANUP ===================="
        self.logger.log(log_line, to_console=True)
        self.peripheral_manager.release_all()

        self.print_summary()

        if (self.fail_count !=0):
            sys.exit(1)

    def print_summary(self):
        total = self.total_tests
        passed = self.pass_count
        failed = self.fail_count

        # Formatowanie podsumowania
        summary = (
            "\n=================== TEST SUMMARY ===================\n"
            f"> Total Tests Run:     {total}\n"
            f"> Passed:              {passed} ✅\n"
            f"> Failed:              {failed} ❌\n"
            "\n======================== STATUS =====================\n"
            f"\nOVERALL STATUS: {'✅ PASSED' if failed == 0 else '❌ FAILED'} : Please check logs for details.\n"
        )

        # Wyświetlanie w konsoli
        self.logger.log(summary, to_console=True)

        # Opcjonalnie zapis do pliku (jeśli logger ma ustawiony log_file)
        if hasattr(self.logger, "log_file") and self.logger.log_file:
            self.logger.log(summary, to_console=False, to_log_file = True)

    def report_test_result(self, group_name, test_name, passed, details=None):
        self.total_tests += 1
        if passed:
            message = f"[PASS] {group_name}, {test_name}"
            self.pass_count += 1
        else:
            message = f"[FAIL] {group_name}, {test_name}:"
            self.fail_count += 1
            if details:
                message += f" {details}"
        self.logger.log(message, to_console=True)
        if self.logger.log_file:
            self.logger.log(message, to_console=False, to_log_file=True)

    def report_test_info(self, group_name, test_name, message):
        message = f"[INFO] {group_name}, {test_name}: {message}"
        self.logger.log(message,to_console=True)
        if self.logger.log_file:
            self.logger.log(message, to_console=False, to_log_file=True)

class TestGroup:
    def __init__(self, name):
        self.name = name
        self.tests = []
        self.setup = None
        self.teardown = None

    def add_test(self, test):
        self.tests.append(test)

    def set_setup(self, setup_func):
        self.setup = setup_func

    def set_teardown(self, teardown_func):
        self.teardown = teardown_func

    def run_tests(self, framework):
        """
        Uruchamia wszystkie testy w grupie.
        """
        # print(f"[RUNNING TEST GROUP] {self.name}")
        # Uruchom setup grupy, jeśli istnieje
        if self.setup:
            self.setup(framework)
        # Uruchom testy
        for test in self.tests:
            test.run(framework, self.name)
        # Uruchom teardown grupy, jeśli istnieje
        if self.teardown:
            self.teardown(framework)


class Test:
    def __init__(self, name, test_func):
        self.name = name
        self.test_func = test_func

    def run(self, framework, group_name):
        try:
            self.test_func(framework, group_name, self.name)
        except Exception as e:
            framework.report_test_result(group_name, self.name, False, str(e))
