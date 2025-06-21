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


def resolve_html_path(arg_value):
    """
    Determines the full path to the HTML report file:
    - If arg_value ends with .html, use it directly as the output file
    - If arg_value is a directory, append /html_report/report.html
    - If arg_value is None, use ./html_report/report.html
    """
    if not arg_value:
        output_dir = Path.cwd() / "html_report"
        output_dir.mkdir(parents=True, exist_ok=True)
        return str(output_dir / "report.html")

    path = Path(arg_value).resolve()

    if path.suffix == ".html":
        # Użytkownik podał pełną ścieżkę do pliku
        path.parent.mkdir(parents=True, exist_ok=True)
        return str(path)

    # Użytkownik podał ścieżkę do folderu
    output_dir = path / "html_report"
    output_dir.mkdir(parents=True, exist_ok=True)
    return str(output_dir / "report.html")





def main():
    # Parse arguments for log and HTML report
    log_file = None
    html_file = None
    if '--log' in sys.argv:
        log_index = sys.argv.index('--log')
        log_file = sys.argv[log_index + 1] if log_index + 1 < len(sys.argv) else None

    if '--html' in sys.argv:
        html_index = sys.argv.index('--html')
        next_index = html_index + 1
        html_arg = sys.argv[next_index] if next_index < len(sys.argv) and not sys.argv[next_index].startswith("--") else None
        html_file = resolve_html_path(html_arg)

    # Initialize logger
    logger = Logger(log_file=log_file, html_file=html_file)

    # Initialize PeripheralManager
    peripheral_manager = PeripheralManager(devices={}, logger=logger)
    peripheral_manager.devices = load_peripheral_configuration(logger=logger)
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
        # Exit code already handled inside run_all_tests()
        sys.exit(e.code)


if __name__ == "__main__":
    main()
