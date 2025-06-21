import sys
import os
import importlib.util
from pathlib import Path

from py_micro_hil.test_framework import TestFramework
from py_micro_hil.logger import Logger
from py_micro_hil.peripheral_manager import PeripheralManager
from py_micro_hil.peripheral_config_loader import load_peripheral_configuration
from py_micro_hil.test_group_factory import create_test_group_from_module
import RPi.GPIO as GPIO


def load_test_groups(test_directory):
    """
    Dynamically loads test groups from test modules in a specified directory.
    :param test_directory: Path to the directory containing test modules.
    :return: A list of TestGroup objects.
    """
    test_groups = []
    for root, _, files in os.walk(test_directory):
        for file in files:
            if file.startswith("test_") and file.endswith(".py"):
                module_path = os.path.join(root, file)
                module_name = os.path.splitext(os.path.relpath(module_path, test_directory))[0].replace(os.sep, '.')
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                group = create_test_group_from_module(module)
                test_groups.append(group)
    return test_groups


def main():
    # Parse arguments for log and HTML report
    log_file = None
    html_file = None
    if '--log' in sys.argv:
        log_index = sys.argv.index('--log')
        log_file = sys.argv[log_index + 1] if log_index + 1 < len(sys.argv) else None
    if '--html' in sys.argv:
        html_index = sys.argv.index('--html')
        html_file = sys.argv[html_index + 1] if html_index + 1 < len(sys.argv) else None

    # Initialize logger
    logger = Logger(log_file=log_file, html_file=html_file)

    # Initialize PeripheralManager
    peripheral_manager = PeripheralManager(devices={}, logger=logger)
    peripheral_manager.devices = load_peripheral_configuration()
    print(f"Discovered peripherals: {peripheral_manager.devices}")

    # Initialize TestFramework
    test_framework = TestFramework(peripheral_manager, logger)

    # Locate test directory
    test_directory = Path.cwd() / "hil_tests"
    if not test_directory.exists():
        print(f"❌ Test directory '{test_directory}' does not exist.")
        sys.exit(1)

    # Load test groups dynamically
    test_groups = load_test_groups(test_directory)
    print(f"Discovered test groups: {[group.name for group in test_groups]}")

    # Add test groups to the framework
    for group in test_groups:
        test_framework.add_test_group(group)

    try:
        # Run all tests
        test_framework.run_all_tests()
    except SystemExit as e:
        # Handle test failures or early exits
        if html_file:
            logger.generate_html_report(test_groups=test_groups)
        logger.log(f"[INFO] Test execution stopped with exit code {e.code}.")
        sys.exit(e.code)

    # Generate HTML report if requested and not yet generated
    if html_file and not logger.html_file:
        logger.generate_html_report(test_groups=test_groups)


if __name__ == "__main__":
    main()
