import sys
import os
import importlib.metadata
import importlib.util
from importlib.resources import files
from pathlib import Path
import argparse

from py_micro_hil.tests_framework import TestFramework
from py_micro_hil.logger import Logger
from py_micro_hil.peripheral_manager import PeripheralManager
from py_micro_hil.peripheral_config_loader import load_peripheral_configuration
from py_micro_hil.tests_group_factory import create_test_group_from_module


def get_project_version() -> str:
    """Return the installed or local project version."""

    try:
        return importlib.metadata.version("py-micro-hil")
    except importlib.metadata.PackageNotFoundError:
        pass

    project_root = Path(__file__).resolve().parents[2]
    pyproject_path = project_root / "pyproject.toml"

    if pyproject_path.exists():
        toml_loader = None
        try:  # Python 3.11+
            import tomllib as toml_loader  # type: ignore
        except ModuleNotFoundError:
            try:
                import tomli as toml_loader  # type: ignore
            except ModuleNotFoundError:
                toml_loader = None

        if toml_loader:
            try:
                data = toml_loader.loads(pyproject_path.read_text())
                return data.get("project", {}).get("version", "unknown")
            except Exception:
                pass

    return "unknown"


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
        "-d",
        "--debug",
        action="store_true",
        help="Show [DEBUG] messages in console/log/HTML outputs.",
    )

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {get_project_version()}",
        help="Print the runner version and exit.",
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
        "--strict-imports",
        action="store_true",
        help="Fail if any discovered test module cannot be imported.",
    )

    parser.add_argument(
        "--create-test-group",
        nargs="+",
        metavar=("GROUP_NAME", "DIR"),
        help=(
            "Create a new test group file from a template.\n"
            "Usage: --create-test-group <group_name> [target_dir]\n"
            "If no directory is provided, the value from --test-dir is used."
        ),
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


def get_template_content() -> str:
    """Load template file text from the installed package."""
    resource = files("py_micro_hil.templates") / "test_group_template.py"
    return resource.read_text()


def create_test_group_file(group_name: str, target_dir: Path, logger: Logger) -> bool:
    """
    Create a new test group file from the template.
    Returns True on success, False otherwise.
    """

    # ensure target directory exists
    if not target_dir.exists():
        logger.log(
            f"[ERROR] ❌ Test directory '{target_dir}' does not exist.",
            to_console=True,
            to_log_file=True,
        )
        return False

    destination = target_dir / f"test_{group_name}.py"

    # prevent overwriting
    if destination.exists():
        logger.log(
            f"[ERROR] ❌ File '{destination}' already exists. Aborting creation.",
            to_console=True,
            to_log_file=True,
        )
        return False

    try:
        # load template content from package (installation-safe)
        template_content = get_template_content()

        # apply formatting
        rendered = template_content.format(test_group_name=group_name)

        # write final file
        destination.write_text(rendered)

    except Exception as exc:
        logger.log(
            f"[ERROR] ❌ Failed to create test group file: {exc}",
            to_console=True,
            to_log_file=True,
        )
        return False

    logger.log(
        f"[INFO] Created test group template at '{destination}'.",
        to_console=True,
        to_log_file=True,
    )
    return True


def load_test_groups(test_directory, logger, strict_imports: bool = False):
    """Dynamically loads test groups from test modules in a specified directory."""
    test_groups = []
    for root, _, filenames in os.walk(test_directory):  # <-- zmieniono files → filenames
        for file in filenames:
            if file.startswith("test_") and file.endswith(".py"):
                module_path = os.path.join(root, file)
                module_name = os.path.splitext(os.path.relpath(module_path, test_directory))[
                    0
                ].replace(os.sep, ".")
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                module = importlib.util.module_from_spec(spec)
                try:
                    spec.loader.exec_module(module)
                    group = create_test_group_from_module(module)
                    test_groups.append(group)
                except Exception as e:
                    level = "ERROR" if strict_imports else "WARN"
                    logger.log(
                        f"[{level}] Skipping {module_path}: {e}",
                        to_console=True,
                        to_log_file=True,
                    )
                    if strict_imports:
                        raise RuntimeError(f"Failed to import test module: {module_path}") from e
    return test_groups


def log_discovered_devices(devices, logger):
    output = []
    output.append("[DEBUG] Discovered peripherals:")

    for category, items in devices.items():
        output.append(f"\t{category}:")

        if not items:
            output.append("\t\t(none)")
            continue

        for item in items:
            output.append(f"\t\t{item.__class__.__name__}:")
            attrs = item.__dict__

            if not attrs:
                output.append("\t\t\t(no attributes)")
                continue

            for key, val in attrs.items():
                output.append(f"\t\t\t{key}: {val}")

    # jedno wywołanie logera
    logger.log("\n".join(output))


def main():
    args = parse_args()

    # Initialize logger
    logger = Logger(log_file=args.log, html_file=args.html, debug_enabled=args.debug)

    if args.debug:
        logger.log(
            "[INFO] Debug logging enabled — [DEBUG] entries will be emitted.",
            to_console=True,
            to_log_file=bool(args.log),
        )

    # Handle test group creation without running the framework
    if args.create_test_group:
        if len(args.create_test_group) > 2:
            logger.log(
                "[ERROR] ❌ Too many arguments for --create-test-group. "
                "Provide <group_name> and optional [target_dir].",
                to_console=True,
                to_log_file=True,
            )
            sys.exit(1)

        group_name = args.create_test_group[0]
        target_dir = (
            Path(args.create_test_group[1])
            if len(args.create_test_group) > 1
            else Path(args.test_dir)
        )

        success = create_test_group_file(group_name, target_dir, logger)
        sys.exit(0 if success else 1)

    # Log info about YAML configuration
    if args.config:
        logger.log(
            f"[INFO] Using configuration file: {args.config}", to_console=True, to_log_file=True
        )
    else:
        default_path = Path.cwd() / "peripherals_config.yaml"
        logger.log(
            f"[INFO] Using default configuration file: {default_path}",
            to_console=True,
            to_log_file=True,
        )

    # Initialize peripherals
    peripheral_manager = PeripheralManager(devices={}, logger=logger)
    peripheral_manager.devices = load_peripheral_configuration(yaml_file=args.config, logger=logger)
    if peripheral_manager.devices is None:
        logger.log(
            "[ERROR] ❌ Peripheral configuration error. Exiting.", to_console=True, to_log_file=True
        )
        sys.exit(1)

    log_discovered_devices(peripheral_manager.devices, logger)

    # Initialize test framework
    test_framework = TestFramework(peripheral_manager, logger)

    # Locate and load tests
    test_directory = Path(args.test_dir)
    if not test_directory.exists():
        logger.log(
            f"[ERROR] ❌ Test directory '{test_directory}' does not exist.",
            to_console=True,
            to_log_file=True,
        )
        sys.exit(1)

    try:
        test_groups = load_test_groups(test_directory, logger, strict_imports=args.strict_imports)
    except Exception as e:
        logger.log(
            f"[ERROR] ❌ Failed to load test modules: {e}",
            to_console=True,
            to_log_file=True,
        )
        sys.exit(1)
    logger.log(
        f"[INFO] Loaded {len(test_groups)} test groups from '{test_directory}'", to_console=True
    )

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
        logger.log(
            f"[ERROR] Unexpected error during test execution: {e}",
            to_console=True,
            to_log_file=True,
        )
        sys.exit(1)

    sys.exit(1 if num_failures else 0)


if __name__ == "__main__":
    main()
