import sys
import os
import importlib.util
from pathlib import Path
import argparse

from py_micro_hil.test_framework import TestFramework
from py_micro_hil.logger import Logger
from py_micro_hil.peripheral_manager import PeripheralManager
from py_micro_hil.peripheral_config_loader import load_peripheral_configuration
from py_micro_hil.test_group_factory import create_test_group_from_module


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
        # User provided full path to file
        path.parent.mkdir(parents=True, exist_ok=True)
        return str(path)

    # User provided path to folder
    output_dir = path / "html_report"
    output_dir.mkdir(parents=True, exist_ok=True)
    return str(output_dir / "report.html")


def parse_args():
    """Parse command line arguments and return structured results."""
    parser = argparse.ArgumentParser(
        description=(
            "Hardware-In-the-Loop (HIL) Test Runner.\n"
            "Automatically discovers and runs tests in the 'hil_tests' directory."
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "--log",
        metavar="FILE",
        help="Optional path to save the test log file (e.g. ./logs/run.log).",
    )

    parser.add_argument(
        "--html",
        nargs="?",
        const=None,
        metavar="PATH",
        help=(
            "Generate an HTML report.\n"
            "If no path is given → ./html_report/report.html\n"
            "If a directory is given → <dir>/html_report/report.html\n"
            "If a file (.html) is given → save directly there."
        ),
    )

    parser.add_argument(
        "--list-tests",
        action="store_true",
        help="List all discovered test groups and exit without running them.",
    )

    parser.add_argument(
        "--test-dir",
        default=str(Path.cwd() / "hil_tests"),
        metavar="DIR",
        help="Path to directory containing test files (default: ./hil_tests).",
    )

    args = parser.parse_args()

    # Resolve HTML path only if --html is present
    args.html = resolve_html_path(args.html) if args.html is not None else None

    return args


def load_test_groups(test_directory):
    """Dynamically loads test groups from test modules in a specified directory."""
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
    args = parse_args()

    # Initialize logger
    logger = Logger(log_file=args.log, html_file=args.html)

    # Initialize peripherals
    peripheral_manager = PeripheralManager(devices={}, logger=logger)
    peripheral_manager.devices = load_peripheral_configuration(logger=logger)
    print(f"Discovered peripherals: {peripheral_manager.devices}")

    # Initialize test framework
    test_framework = TestFramework(peripheral_manager, logger)

    # Locate and load tests
    test_directory = Path(args.test_dir)
    if not test_directory.exists():
        print(f"❌ Test directory '{test_directory}' does not exist.")
        sys.exit(1)

    test_groups = load_test_groups(test_directory)
    print(f"Discovered test groups: {[group.name for group in test_groups]}")

    # Only list tests if requested
    if args.list_tests:
        print("\nAvailable test groups:")
        for group in test_groups:
            print(f" - {group.name}")
        sys.exit(0)

    # Add and run tests
    for group in test_groups:
        test_framework.add_test_group(group)

    try:
        test_framework.run_all_tests()
    except SystemExit as e:
        sys.exit(e.code)


if __name__ == "__main__":
    main()
