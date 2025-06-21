from py_micro_hil.logger import Logger
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
        """
        Runs all test groups and generates logs/reports.
        """
        self.logger.log("\n=================== INITIALIZATION ===================", to_console=True)
        self.peripheral_manager.initialize_all()

        self.logger.log("\n=================== TEST EXECUTION ===================", to_console=True)
        for group in self.test_groups:
            group.run_tests(self)

        self.logger.log("\n==================== RESOURCE CLEANUP ====================", to_console=True)
        self.peripheral_manager.release_all()

        self.print_summary()

        # Generate HTML report if enabled
        if self.logger.html_file:
            self.logger.generate_html_report()

        if self.fail_count > 0:
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
            self.logger.log(summary, to_console=False, to_log_file=True)

    def report_test_result(self, group_name, test_name, passed, details=None):
        """
        Reports the result of a single test.
        :param group_name: Name of the test group.
        :param test_name: Name of the individual test.
        :param passed: Boolean indicating whether the test passed or failed.
        :param details: Additional information about the test result.
        """
        self.total_tests += 1

        # Determine test status
        if passed:
            status = "PASS"
            self.pass_count += 1
        else:
            status = "FAIL"
            self.fail_count += 1

        # Log to console
        message = f"[{status}] {group_name} -> {test_name}"
        if details:
            message += f": {details}"
        self.logger.log(message, to_console=True)

        # Log to file if --log is enabled
        if self.logger.log_file:
            self.logger.log(message, to_console=False, to_log_file=True)

        # Collect data for HTML report
        if self.logger.html_file:
            self.logger.log_entries.append({
                "group_name": group_name,
                "test_name": test_name,
                "level": status,
                "message": details or "",
                "additional_info": "-"
            })




    def report_test_info(self, group_name, test_name, message):
        message = f"[INFO] {group_name}, {test_name}: {message}"
        self.logger.log(message, to_console=True)
        if self.logger.log_file:
            self.logger.log(message, to_console=False, to_log_file=True)


class TestGroup:
    def __init__(self, name, test_file=None):
        """
        :param name: Nazwa grupy testowej.
        :param test_file: Ścieżka do pliku zawierającego definicje testów.
        """
        self.name = name
        self.tests = []
        self.setup = None
        self.teardown = None
        self.test_file = test_file  # Ścieżka do pliku testów

    def add_test(self, test):
        self.tests.append(test)

    def set_setup(self, setup_func):
        self.setup = setup_func

    def set_teardown(self, teardown_func):
        self.teardown = teardown_func

    # def run_tests(self, framework):
    #     """
    #     Uruchamia wszystkie testy w grupie.
    #     """
    #     # Uruchom setup grupy, jeśli istnieje
    #     if self.setup:
    #         self.setup(framework)

    #     # Uruchom testy
    #     for test in self.tests:
    #         test.run(framework, self.name)

    #     # Uruchom teardown grupy, jeśli istnieje
    #     if self.teardown:
    #         self.teardown(framework)


    def run_tests(self, framework):
        """
        Uruchamia wszystkie testy w grupie.
        """
        # log_line = f"[INFO] Running Test Group:  {self.name}"
        # framework.logger.log(log_line, to_console=True)
        # if framework.logger.log_file:
        #     framework.logger.log(log_line, to_console=False, to_log_file=True)

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
    def __init__(self, name, test_func, original_func=None):
        """
        :param name: Wyświetlana nazwa testu.
        :param test_func: Funkcja wykonująca test (opakowana).
        :param original_func: Oryginalna funkcja testowa (do pobierania kodu).
        """
        self.name = name
        self.test_func = test_func
        self.original_func = original_func

    def run(self, framework, group_name):
        try:
            self.test_func(framework)
        except Exception as e:
            framework.report_test_result(group_name, self.name, False, str(e))

