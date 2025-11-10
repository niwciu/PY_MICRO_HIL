# pylint: disable=...
from __future__ import annotations
import sys
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from py_micro_hil.logger import Logger
from py_micro_hil.report_generator import ReportGenerator
from py_micro_hil import utils


class Peripheral(ABC):
    """
    Abstract base class for a peripheral device.
    Peripheral manager must provide `initialize_all()` and `release_all()` methods to coordinate these.
    """
    @abstractmethod
    def initialize(self) -> None:
        """Initialize hardware resources."""
        pass

    @abstractmethod
    def release(self) -> None:
        """Release hardware resources."""
        pass


class TestFramework:
    __test__ = False  # prevent pytest from collecting this class
    """
    Core test framework managing peripherals, test groups, and reporting.
    Expects `peripheral_manager` to implement `initialize_all()` and `release_all()`.
    """
    def __init__(
        self,
        peripheral_manager: Any,
        logger: Logger
    ) -> None:
        self.peripheral_manager = peripheral_manager
        self.test_groups: List[TestGroup] = []
        self.total_tests = 0
        self.pass_count = 0
        self.fail_count = 0
        self.logger = logger
        self.report_generator = ReportGenerator(self.logger)

    def add_test_group(self, group: TestGroup) -> None:
        """Add a TestGroup to be executed."""
        self.test_groups.append(group)

    def run_all_tests(self) -> None:
        """
        Initialize peripherals, run all test groups, clean up resources,
        and then print summary and generate report.
        Exits with sys.exit(1) if any test failed.
        """
        # Initialization phase
        self.logger.log("\n=================== INITIALIZATION ===================", to_console=True)
        if not utils.is_raspberry_pi():
            self.logger.log(f"\n[WARNING] Framwork runned outside of Raspberry Pi. All RPi hardware modules will be mocked")
        try:
            init = getattr(self.peripheral_manager, 'initialize_all', None)
            if not callable(init):
                raise AttributeError("peripheral_manager missing 'initialize_all' method")
            init()
        except Exception as e:
            self.logger.log(f"[ERROR] During peripherals initialization: {e}", to_console=True)
            self.logger.log("Aborting tests.", to_console=True)
            sys.exit(1)

        # Test execution phase
        self.logger.log("\n=================== TEST EXECUTION ===================", to_console=True)
        for group in self.test_groups:
            group.run_tests(self)

        # Cleanup phase
        self.logger.log("\n==================== RESOURCE CLEANUP ====================", to_console=True)
        try:
            rel = getattr(self.peripheral_manager, 'release_all', None)
            if not callable(rel):
                raise AttributeError("peripheral_manager missing 'release_all' method")
            rel()
        except Exception as e:
            self.logger.log(f"[WARNING] During peripherals cleanup: {e}", to_console=True)

        # Summary
        self.print_summary()

        # Generate HTML report if enabled
        if getattr(self.logger, 'html_file', None):
            self.report_generator.generate(self.test_groups)

        # Exit with error if any failures
        if self.fail_count > 0:
            sys.exit(1)

    def print_summary(self) -> None:
        """
        Print and log a summary of total, passed, and failed tests.
        """
        total = self.total_tests
        passed = self.pass_count
        failed = self.fail_count
        summary = (
            "\n=================== TEST SUMMARY ===================\n"
            f"> Total Tests Run:     {total}\n"
            f"> Passed:              {passed} ✅\n"
            f"> Failed:              {failed} ❌\n"
            "\n======================== STATUS =====================\n"
            f"\nOVERALL STATUS: {'✅ PASSED' if failed == 0 else '❌ FAILED'} : Please check logs for details.\n"
        )
        self.logger.log(summary, to_console=True)
        if getattr(self.logger, 'log_file', None):
            self.logger.log(summary, to_console=False, to_log_file=True)

    def report_test_result(
        self,
        group_name: str,
        test_name: str,
        passed: bool,
        details: Optional[str] = None
    ) -> None:
        """
        Record and log the result of a single test.
        """
        self.total_tests += 1
        status = "PASS" if passed else "FAIL"
        if passed:
            self.pass_count += 1
        else:
            self.fail_count += 1
        # Console and optional file logging
        message = f"[{status}] {group_name} -> {test_name}"
        if details:
            message += f": {details}"
        self.logger.log(message, to_console=True)
        if getattr(self.logger, 'log_file', None):
            self.logger.log(message, to_console=False, to_log_file=True)
        # Append entry for HTML report
        if getattr(self.logger, 'html_file', None):
            self.logger.log_entries.append({
                "group_name": group_name,
                "test_name": test_name,
                "level": status,
                "message": details or "",
                "additional_info": "-"
            })

    def report_test_info(
        self,
        group_name: str,
        test_name: str,
        message: str
    ) -> None:
        """
        Log informational message during a test.
        """
        note = f"[INFO] {group_name}, {test_name}: {message}"
        self.logger.log(note, to_console=True)
        if getattr(self.logger, 'log_file', None):
            self.logger.log(note, to_console=False, to_log_file=True)


class TestGroup:
    __test__ = False  # prevent pytest from collecting this class
    """
    Holds a collection of Test instances along with optional setup and teardown.
    """
    __test__ = False  # Prevent pytest from collecting this class

    def __init__(
        self,
        name: str,
        test_file: Optional[str] = None
    ) -> None:
        self.name = name
        self.tests: List[Test] = []
        self.setup: Optional[Any] = None
        self.teardown: Optional[Any] = None
        self.test_file = test_file

    def add_test(self, test: Test) -> None:
        """Add a Test to the group."""
        self.tests.append(test)

    def set_setup(self, setup_func: Any) -> None:
        """Define a setup function to run before tests."""
        self.setup = setup_func

    def set_teardown(self, teardown_func: Any) -> None:
        """Define a teardown function to run after tests."""
        self.teardown = teardown_func

    def run_tests(self, framework: TestFramework) -> None:
        """
        Execute setup, each test, and teardown, logging the group header.
        Exceptions in setup/teardown are caught and logged but do not stop other groups.
        """
        header = f"[INFO] Running test group: {self.name}"
        framework.logger.log(header, to_console=True)
        if getattr(framework.logger, 'log_file', None):
            framework.logger.log(header, to_console=False, to_log_file=True)

        # Group setup
        if self.setup:
            try:
                self.setup(framework)
            except Exception as e:
                framework.logger.log(f"[ERROR] Setup for group '{self.name}' failed: {e}", to_console=True)

        # Tests
        for test in self.tests:
            test.run(framework, self.name)

        # Group teardown
        if self.teardown:
            try:
                self.teardown(framework)
            except Exception as e:
                framework.logger.log(f"[WARNING] Teardown for group '{self.name}' raised: {e}", to_console=True)


class Test:
    __test__ = False  # prevent pytest from collecting this class
    """
    Wraps a single test function with a name for reporting.
    """
    def __init__(
        self,
        name: str,
        test_func: Any,
        original_func: Optional[Any] = None
    ) -> None:
        self.name = name
        self.test_func = test_func
        self.original_func = original_func

    def run(self, framework: TestFramework, group_name: str) -> None:
        """
        Execute the test function and report pass or fail.
        """
        try:
            self.test_func(framework)
        except Exception as e:
            framework.report_test_result(group_name, self.name, False, str(e))
        else:
            framework.report_test_result(group_name, self.name, True)
