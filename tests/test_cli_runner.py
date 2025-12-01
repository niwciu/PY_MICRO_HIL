import sys
import types
import importlib.util
import importlib.metadata
from pathlib import Path
import pytest

import py_micro_hil.cli as cli  # upewnij się, że to prawidłowa ścieżka do Twojego pliku CLI


# ---------------------------------------------------------------------
# resolve_html_path
# ---------------------------------------------------------------------

def test_resolve_html_path_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = cli.resolve_html_path(None)
    assert result.endswith("html_report/report.html")
    assert (tmp_path / "html_report").exists()


def test_resolve_html_path_with_html_file(tmp_path):
    file_path = tmp_path / "report.html"
    result = cli.resolve_html_path(str(file_path))
    assert result.endswith("report.html")
    assert file_path.parent.exists()


def test_resolve_html_path_with_directory(tmp_path):
    result = cli.resolve_html_path(str(tmp_path))
    assert result.endswith("html_report/report.html")
    assert (tmp_path / "html_report").exists()


# ---------------------------------------------------------------------
# parse_args
# ---------------------------------------------------------------------

def test_parse_args_basic(monkeypatch):
    argv = ["prog", "--log", "mylog.txt", "--config", "conf.yaml", "--html", "report.html"]
    monkeypatch.setattr(sys, "argv", argv)
    args = cli.parse_args()
    assert args.log == "mylog.txt"
    assert args.config.endswith("conf.yaml")
    assert args.html.endswith("report.html")
    assert args.strict_imports is False


def test_parse_args_no_html(monkeypatch):
    argv = ["prog"]
    monkeypatch.setattr(sys, "argv", argv)
    args = cli.parse_args()
    assert args.html is None
    assert args.strict_imports is False


def test_parse_args_html_directory(monkeypatch, tmp_path):
    argv = ["prog", "--html", str(tmp_path)]
    monkeypatch.setattr(sys, "argv", argv)
    args = cli.parse_args()
    assert args.html.endswith("html_report/report.html")
    assert (tmp_path / "html_report").exists()


# ---------------------------------------------------------------------
# get_project_version
# ---------------------------------------------------------------------


def test_get_project_version_reads_pyproject(monkeypatch):
    def raise_not_found(*args, **kwargs):
        raise importlib.metadata.PackageNotFoundError()

    monkeypatch.setattr(importlib.metadata, "version", raise_not_found)
    version = cli.get_project_version()
    assert version == "0.1.3"


# ---------------------------------------------------------------------
# create_test_group_file
# ---------------------------------------------------------------------


def test_create_test_group_file_success(tmp_path, monkeypatch):
    template = tmp_path / "template.py"
    template.write_text("# template\nclass {test_group_name}: pass\n")
    target_dir = tmp_path / "hil_tests"
    target_dir.mkdir()

    monkeypatch.setattr(cli, "get_template_path", lambda: template)
    logger = DummyLogger()

    created = cli.create_test_group_file("alpha", target_dir, logger)

    assert created is True
    output_file = target_dir / "test_alpha.py"
    assert output_file.exists()
    assert "class alpha" in output_file.read_text()
    assert any("Created test group template" in msg for msg in logger.messages)


def test_create_test_group_file_existing(tmp_path, monkeypatch):
    template = tmp_path / "template.py"
    template.write_text("# template\nclass {test_group_name}: pass\n")
    target_dir = tmp_path / "hil_tests"
    target_dir.mkdir()
    existing = target_dir / "test_alpha.py"
    existing.write_text("# existing")

    monkeypatch.setattr(cli, "get_template_path", lambda: template)
    logger = DummyLogger()

    created = cli.create_test_group_file("alpha", target_dir, logger)

    assert created is False
    assert any("already exists" in msg for msg in logger.messages)


def test_create_test_group_file_missing_dir(tmp_path, monkeypatch):
    template = tmp_path / "template.py"
    template.write_text("# template\nclass {test_group_name}: pass\n")
    target_dir = tmp_path / "missing"

    monkeypatch.setattr(cli, "get_template_path", lambda: template)
    logger = DummyLogger()

    created = cli.create_test_group_file("alpha", target_dir, logger)

    assert created is False
    assert any("does not exist" in msg for msg in logger.messages)


# ---------------------------------------------------------------------
# log_discovered_devices
# ---------------------------------------------------------------------


def test_log_discovered_devices_reports_attributes():
    logger = DummyLogger()
    devices = {"GPIO": [types.SimpleNamespace(pin=4)], "UART": []}

    cli.log_discovered_devices(devices, logger)

    assert "[DEBUG] Discovered peripherals:" in logger.messages[0]
    assert any("GPIO" in msg for msg in logger.messages)
    assert any("pin: 4" in msg for msg in logger.messages)


# ---------------------------------------------------------------------
# load_test_groups
# ---------------------------------------------------------------------

class DummyLogger:
    def __init__(self):
        self.messages = []

    def log(self, msg, **kwargs):
        self.messages.append(msg)


def test_load_test_groups_success(tmp_path, monkeypatch):
    file = tmp_path / "test_sample.py"
    file.write_text("x = 1")

    dummy_group = types.SimpleNamespace(name="GroupA")
    monkeypatch.setattr(cli, "create_test_group_from_module", lambda m: dummy_group)

    groups = cli.load_test_groups(tmp_path, DummyLogger())
    assert len(groups) == 1
    assert groups[0].name == "GroupA"


def test_load_test_groups_with_exception(tmp_path, monkeypatch):
    file = tmp_path / "test_fail.py"
    file.write_text("raise SyntaxError")

    def fake_exec_module(module):
        raise RuntimeError("boom")

    def fake_create_module(spec):
        return types.ModuleType("mod")

    spec = importlib.util.spec_from_file_location("mod", file)
    spec.loader = types.SimpleNamespace(
        exec_module=fake_exec_module,
        create_module=fake_create_module
    )

    monkeypatch.setattr(importlib.util, "spec_from_file_location", lambda n, p: spec)

    logger = DummyLogger()
    monkeypatch.setattr(cli, "create_test_group_from_module", lambda m: None)
    cli.load_test_groups(tmp_path, logger)
    assert any("Skipping" in msg for msg in logger.messages)


def test_load_test_groups_strict_mode_raises(tmp_path, monkeypatch):
    file = tmp_path / "test_fail.py"
    file.write_text("raise SyntaxError")

    def fake_exec_module(module):
        raise RuntimeError("boom")

    def fake_create_module(spec):
        return types.ModuleType("mod")

    spec = importlib.util.spec_from_file_location("mod", file)
    spec.loader = types.SimpleNamespace(
        exec_module=fake_exec_module,
        create_module=fake_create_module
    )

    monkeypatch.setattr(importlib.util, "spec_from_file_location", lambda n, p: spec)

    logger = DummyLogger()
    monkeypatch.setattr(cli, "create_test_group_from_module", lambda m: None)
    with pytest.raises(RuntimeError):
        cli.load_test_groups(tmp_path, logger, strict_imports=True)


# ---------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------

@pytest.fixture
def dummy_environment(tmp_path, monkeypatch):
    """Setup fake environment for main()."""

    class DummyPeripheral:
        def __init__(self, name="device", channel=1):
            self.name = name
            self.channel = channel

    class DummyLogger:
        def __init__(self, *a, **kw):
            self.logged = []
            self.html_file = None
            self.log_file = None
        def log(self, msg, **kw):
            self.logged.append(msg)

    class DummyPeripheralManager:
        def __init__(self, **kw):
            self.devices = {"GPIO": [DummyPeripheral()], "Empty": []}

    class DummyTestFramework:
        def __init__(self, pm, logger):
            self.pm = pm
            self.logger = logger
            self.groups = []
        def add_test_group(self, g):
            self.groups.append(g)
        def run_all_tests(self):
            return 0

    monkeypatch.setattr(cli, "Logger", DummyLogger)
    monkeypatch.setattr(cli, "PeripheralManager", DummyPeripheralManager)
    monkeypatch.setattr(
        cli,
        "load_peripheral_configuration",
        lambda yaml_file, logger: {"GPIO": [DummyPeripheral("pin4")], "UART": []},
    )
    monkeypatch.setattr(cli, "TestFramework", DummyTestFramework)
    monkeypatch.setattr(
        cli,
        "load_test_groups",
        lambda td, lg, strict_imports=False: [types.SimpleNamespace(name="TG1")],
    )
    monkeypatch.chdir(tmp_path)
    return tmp_path


# ---------------------------------------------------------------------
# run_main helper
# ---------------------------------------------------------------------

def run_main(monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", ["prog"] + argv)
    with pytest.raises(SystemExit) as e:
        cli.main()
    return e.value.code


# ---------------------------------------------------------------------
# main() test cases
# ---------------------------------------------------------------------

def test_main_success(monkeypatch, dummy_environment, tmp_path):
    test_dir = tmp_path / "hil_tests"
    test_dir.mkdir()
    argv = ["--test-dir", str(test_dir)]
    code = run_main(monkeypatch, argv)
    assert code == 0


def test_main_peripheral_config_error(monkeypatch, dummy_environment):
    monkeypatch.setattr(cli, "load_peripheral_configuration", lambda yaml_file, logger: None)
    code = run_main(monkeypatch, [])
    assert code == 1


def test_main_missing_test_dir(monkeypatch, dummy_environment, tmp_path):
    bad_dir = tmp_path / "missing"
    argv = ["--test-dir", str(bad_dir)]
    code = run_main(monkeypatch, argv)
    assert code == 1


def test_main_list_tests(monkeypatch, dummy_environment, tmp_path):
    test_dir = tmp_path / "hil_tests"
    test_dir.mkdir()
    monkeypatch.setattr(
        cli,
        "load_test_groups",
        lambda td, lg, strict_imports=False: [types.SimpleNamespace(name="TG1")],
    )
    argv = ["--list-tests", "--test-dir", str(test_dir)]
    code = run_main(monkeypatch, argv)
    assert code == 0


def test_main_failures(monkeypatch, dummy_environment, tmp_path):
    def failing_run(self): return 3
    monkeypatch.setattr(cli.TestFramework, "run_all_tests", failing_run)
    test_dir = tmp_path / "hil_tests"
    test_dir.mkdir()
    argv = ["--test-dir", str(test_dir)]
    code = run_main(monkeypatch, argv)
    assert code == 1


def test_main_unexpected_exception(monkeypatch, dummy_environment, tmp_path):
    def raise_exc(self): raise RuntimeError("boom")
    monkeypatch.setattr(cli.TestFramework, "run_all_tests", raise_exc)
    test_dir = tmp_path / "hil_tests"
    test_dir.mkdir()
    argv = ["--test-dir", str(test_dir)]
    code = run_main(monkeypatch, argv)
    assert code == 1
