import sys
import os
import importlib.util
from pathlib import Path
import argparse

from py_micro_hil.tests_framework import TestFramework
from py_micro_hil.logger import Logger
from py_micro_hil.peripheral_manager import PeripheralManager
from py_micro_hil.peripheral_config_loader import load_peripheral_configuration
from py_micro_hil.tests_group_factory import create_test_group_from_module


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
        "--config",
        "-c",
        metavar="YAML",
        help=(
            "Path to YAML configuration file.\n"
            "If omitted, defaults to ./peripherals_config.yaml\n"
            "Can be absolute or relative to the current working directory."
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

    # Normalize YAML path (if provided)
    args.config = str(Path(args.config).resolve()) if args.config else None

    return args


def load_test_groups(test_directory, logger):
    """Dynamically loads test groups from test modules in a specified directory."""
    test_groups = []
    for root, _, files in os.walk(test_directory):
        for file in files:
            if file.startswith("test_") and file.endswith(".py"):
                module_path = os.path.join(root, file)
                module_name = os.path.splitext(os.path.relpath(module_path, test_directory))[0].replace(os.sep, '.')
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                module = importlib.util.module_from_spec(spec)
                try:
                    spec.loader.exec_module(module)
                    group = create_test_group_from_module(module)
                    test_groups.append(group)
                except Exception as e:
                    logger.log(f"[WARN] Skipping {module_path}: {e}", to_console=True, to_log_file=True)
    return test_groups


def main():
    args = parse_args()

    # Initialize logger
    logger = Logger(log_file=args.log, html_file=args.html)

    # Log info about YAML configuration
    if args.config:
        logger.log(f"[INFO] Using configuration file: {args.config}", to_console=True, to_log_file=True)
    else:
        default_path = Path.cwd() / "peripherals_config.yaml"
        logger.log(f"[INFO] Using default configuration file: {default_path}", to_console=True, to_log_file=True)

    # Initialize peripherals
    peripheral_manager = PeripheralManager(devices={}, logger=logger)
    peripheral_manager.devices = load_peripheral_configuration(
        yaml_file=args.config,
        logger=logger
    )
    if peripheral_manager.devices is None:
        logger.log("[ERROR] ❌ Peripheral configuration error. Exiting.", to_console=True, to_log_file=True)
        sys.exit(1)

    logger.log(f"[INFO] Discovered peripherals: {peripheral_manager.devices}")

    # Initialize test framework
    test_framework = TestFramework(peripheral_manager, logger)

    # Locate and load tests
    test_directory = Path(args.test_dir)
    if not test_directory.exists():
        logger.log(f"[ERROR] ❌ Test directory '{test_directory}' does not exist.", to_console=True, to_log_file=True)
        sys.exit(1)

    test_groups = load_test_groups(test_directory, logger)
    logger.log(f"[INFO] Loaded {len(test_groups)} test groups from '{test_directory}'", to_console=True)


    # Only list tests if requested
    if args.list_tests:
        logger.log("\nAvailable test groups:", to_console=True)
        for group in test_groups:
            logger.log(f" - {group.name}", to_console=True)
        sys.exit(0)


    # Add and run tests
    for group in test_groups:
        test_framework.add_test_group(group)

    try:
        num_failures = test_framework.run_all_tests()
    except Exception as e:
        logger.log(f"[ERROR] Unexpected error during test execution: {e}", to_console=True, to_log_file=True)
        sys.exit(1)

    sys.exit(1 if num_failures else 0)


if __name__ == "__main__":
    main()
