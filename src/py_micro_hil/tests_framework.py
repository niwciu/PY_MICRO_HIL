# pylint: disable=too-many-instance-attributes, too-few-public-methods
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, List, Optional

from py_micro_hil.logger import Logger
from py_micro_hil.report_generator import ReportGenerator
from py_micro_hil.utils.system import is_raspberry_pi


# =============================================================================
# ABSTRACT BASE CLASS
# =============================================================================


class Peripheral(ABC):
    """
    Abstract base class for a peripheral device.
    Each peripheral must implement `initialize()` and `release()`.
    PeripheralManager will call these methods during setup and cleanup.
    """

    @abstractmethod
    def initialize(self) -> None:
        """Initialize hardware resources."""
        pass

    @abstractmethod
    def release(self) -> None:
        """Release hardware resources."""
        pass


# =============================================================================
# CORE TEST FRAMEWORK
# =============================================================================


class TestFramework:
    """
    Core test framework managing peripherals, test groups, and reporting.
    Expects `peripheral_manager` to implement `initialize_all()` and `release_all()`.
    """

    __test__ = False  # prevent pytest from collecting this class

    def __init__(self, peripheral_manager: Any, logger: Logger) -> None:
        self.peripheral_manager = peripheral_manager
        self.test_groups: List[TestGroup] = []
        self.total_tests = 0
        self.pass_count = 0
        self.fail_count = 0
        self.logger = logger
        self.report_generator = ReportGenerator(self.logger)
        self.current_test_status: Optional[bool] = None

    # -------------------------------------------------------------------------
    # GROUP MANAGEMENT
    # -------------------------------------------------------------------------

    def add_test_group(self, group: TestGroup) -> None:
        """Add a TestGroup to be executed."""
        self.test_groups.append(group)

    # -------------------------------------------------------------------------
    # MAIN EXECUTION FLOW
    # -------------------------------------------------------------------------

    def run_all_tests(self) -> int:
        """
        Initialize peripherals, execute all test groups, perform cleanup,
        and finally print summary and optionally generate HTML report.

        :return: Number of failed tests.
        """
        self.logger.log("\n=================== INITIALIZATION ===================", to_console=True)

        # Warn when running outside Raspberry Pi hardware
        if not is_raspberry_pi():
            self.logger.log(
                "\n[WARNING] Framework running outside Raspberry Pi. "
                "Hardware peripherals will be mocked.",
                to_console=True,
            )

        # --- Initialization phase ---
        try:
            init = getattr(self.peripheral_manager, "initialize_all", None)
            if not callable(init):
                raise AttributeError("peripheral_manager missing 'initialize_all' method")
            init()
        except Exception as e:
            self.logger.log(f"[ERROR] During peripherals initialization: {e}", to_console=True)
            self.logger.log("Aborting tests.", to_console=True)
            self.fail_count += 1
            return self.fail_count

            # --- Enable/disable logging for all peripherals based on debug_enabled flag ---
            if self.logger.debug_enabled:
                self.peripheral_manager.enable_logging_all()
            else:
                self.peripheral_manager.disable_logging_all()

        # --- Test execution phase ---
        self.logger.log("\n=================== TEST EXECUTION ===================", to_console=True)
        for group in self.test_groups:
            group.run_tests(self)

        # --- Cleanup phase ---
        self.logger.log(
            "\n==================== RESOURCE CLEANUP ====================", to_console=True
        )
        try:
            rel = getattr(self.peripheral_manager, "release_all", None)
            if not callable(rel):
                raise AttributeError("peripheral_manager missing 'release_all' method")
            rel()
        except Exception as e:
            self.logger.log(f"[ERROR] During peripherals cleanup: {e}", to_console=True)

        # --- Summary ---
        self.print_summary()

        # --- Generate HTML report if enabled ---
        if getattr(self.logger, "html_file", None):
            try:
                self.report_generator.generate(self.test_groups)
            except Exception as e:
                self.logger.log(f"[ERROR] Report generation failed: {e}", to_console=True)

        return self.fail_count

    # -------------------------------------------------------------------------
    # SUMMARY AND REPORTING
    # -------------------------------------------------------------------------

    def print_summary(self) -> None:
        """Print and log a summary of total, passed, and failed tests."""
        total = self.total_tests
        passed = self.pass_count
        failed = self.fail_count

        summary = (
            "\n=================== TEST SUMMARY ===================\n"
            f"> Total Tests Run:     {total}\n"
            f"> Passed:              {passed} ✅\n"
            f"> Failed:              {failed} ❌\n"
            "\n======================== STATUS =====================\n"
            f"\nOVERALL STATUS: {'✅ PASSED' if failed == 0 else '❌ FAILED'}"
            " : Please check logs for details.\n"
        )

        self.logger.log(summary, to_console=True)
        if getattr(self.logger, "log_file", None):
            self.logger.log(summary, to_console=False, to_log_file=True)

    def report_test_result(
        self, group_name: str, test_name: str, passed: bool, details: Optional[str] = None
    ) -> None:
        """Record and log the result of a single test."""
        self.current_test_status = passed
        self.total_tests += 1
        status = "PASS" if passed else "FAIL"

        if passed:
            self.pass_count += 1
        else:
            self.fail_count += 1

        message = f"[{status}] {group_name} -> {test_name}"
        if details:
            message += f": {details}"

        # Log to console and optionally to file
        self.logger.log(message, to_console=True)
        if getattr(self.logger, "log_file", None):
            self.logger.log(message, to_console=False, to_log_file=True)

        # Append entry for reporting (HTML or later aggregation)
        self.logger.log_entries.append(
            {
                "group_name": group_name,
                "test_name": test_name,
                "level": status,
                "message": details or "",
                "additional_info": "-",
            }
        )

    def report_test_info(self, group_name: str, test_name: str, message: str) -> None:
        """Log an informational message during a test."""
        note = f"[INFO] {group_name}, {test_name}: {message}"
        self.logger.log(note, to_console=True)
        if getattr(self.logger, "log_file", None):
            self.logger.log(note, to_console=False, to_log_file=True)


# =============================================================================
# TEST GROUP
# =============================================================================


class TestGroup:
    """
    Represents a logical group of tests with optional setup and teardown functions.
    """

    __test__ = False  # prevent pytest from collecting this class

    def __init__(self, name: str, test_file: Optional[str] = None) -> None:
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
        Execute setup, each test, and teardown.
        Exceptions in setup/teardown are caught and logged.
        """
        header = f"[INFO] Running test group: {self.name}"
        framework.logger.log(header, to_console=True)
        if getattr(framework.logger, "log_file", None):
            framework.logger.log(header, to_console=False, to_log_file=True)

        # --- Setup ---
        setup_failed = False
        if self.setup:
            try:
                self.setup(framework)
            except Exception as e:
                framework.logger.log(
                    f"[ERROR] Setup for group '{self.name}' failed: {e}", to_console=True
                )
                framework.report_test_result(self.name, "setup", False, str(e))
                setup_failed = True

        if setup_failed:
            framework.logger.log(
                f"[ERROR] Skipping tests for group '{self.name}' due to setup failure.",
                to_console=True,
            )
            return

        # --- Run all tests ---
        if not self.tests:
            framework.logger.log(
                f"[WARNING] No tests found in group '{self.name}'.", to_console=True
            )
        else:
            for test in self.tests:
                test.run(framework, self.name)

        # --- Teardown ---
        if self.teardown:
            try:
                self.teardown(framework)
            except Exception as e:
                framework.logger.log(
                    f"[WARNING] Teardown for group '{self.name}' raised: {e}", to_console=True
                )
                framework.report_test_result(self.name, "teardown", False, str(e))

        framework.logger.log(f"[INFO] Finished test group: {self.name}", to_console=True)


# =============================================================================
# TEST WRAPPER
# =============================================================================


class Test:
    """Wraps a single test function with a name for reporting."""

    __test__ = False  # prevent pytest from collecting this class

    def __init__(self, name: str, test_func: Any, original_func: Optional[Any] = None) -> None:
        self.name = name
        self.test_func = test_func
        self.original_func = original_func

    def run(self, framework: TestFramework, group_name: str) -> None:
        """Execute the test function and report its result."""
        framework.current_test_status = None
        if getattr(framework.logger, "debug_enabled", False):
            framework.logger.log(f"[DEBUG] Running test: {self.name}")
        try:
            self.test_func(framework)
        except Exception as e:
            if framework.current_test_status is not False:
                framework.report_test_result(group_name, self.name, False, str(e))
        else:
            if framework.current_test_status is None:
                framework.report_test_result(group_name, self.name, True)
