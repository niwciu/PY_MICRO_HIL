from unittest.mock import MagicMock
from py_micro_hil.logger import Logger


# ---------------------------------------------------------------------
# Basic logging behaviour
# ---------------------------------------------------------------------


def test_log_to_console_only(capsys):
    logger = Logger()
    logger.log("[INFO] This is a console message")
    captured = capsys.readouterr()
    assert "This is a console message" in captured.out


def test_log_to_file(tmp_path):
    log_file = tmp_path / "test_log.log"
    logger = Logger(log_file=str(log_file))
    logger.log("[INFO] File log message", to_console=False, to_log_file=True)
    content = log_file.read_text()
    assert "File log message" in content


def test_flush_log_buffer(tmp_path):
    log_file = tmp_path / "buffered.log"
    logger = Logger(log_file=str(log_file))
    logger.log_buffer = "Buffered log"
    logger.flush_log()
    assert "Buffered log" in log_file.read_text()
    assert logger.log_buffer == ""


def test_flush_log_without_file_and_empty_buffer():
    logger = Logger()
    logger.flush_log()  # should do nothing and not raise


# ---------------------------------------------------------------------
# HTML logging
# ---------------------------------------------------------------------


def test_html_log_deduplication():
    mock_report = MagicMock()
    logger = Logger(html_file="dummy.html")
    logger.report_generator = mock_report
    logger.log("[PASS] Duplicate", html_log=True)
    logger.log("[PASS] Duplicate", html_log=True)  # should not be added twice
    assert len(logger.log_entries) == 1


def test_should_log_to_html_limits_entries():
    logger = Logger(html_file="dummy.html")
    logger.report_generator = MagicMock()
    logger.log_entries = [{"message": f"m{i}"} for i in range(10_001)]
    result = logger._should_log_to_html("new message")
    assert result is True
    assert len(logger.log_entries) == 10_000  # oldest trimmed


def test_generate_html_report_success():
    logger = Logger(html_file="dummy.html")
    logger.report_generator = MagicMock()
    logger.generate_html_report(["group1"])
    logger.report_generator.generate.assert_called_once()


def test_generate_html_report_failure(capsys):
    logger = Logger(html_file="dummy.html")
    mock_report = MagicMock()
    mock_report.generate.side_effect = RuntimeError("boom")
    logger.report_generator = mock_report
    logger.generate_html_report([])
    captured = capsys.readouterr()
    assert "Failed to generate HTML report" in captured.out


# ---------------------------------------------------------------------
# Console and color formatting
# ---------------------------------------------------------------------


def test_log_coloring(monkeypatch):
    logger = Logger()
    monkeypatch.setattr("builtins.print", lambda msg: setattr(logger, "_printed", msg))
    logger.log("[FAIL] should be red")
    assert "[" in logger._printed and "]" in logger._printed


def test_log_to_console_fallback(monkeypatch):
    logger = Logger()
    # simulate print raising error
    monkeypatch.setattr(
        "builtins.print", lambda msg: (_ for _ in ()).throw(RuntimeError("no stdout"))
    )
    logger._log_to_console("[INFO] test")  # should not raise


# ---------------------------------------------------------------------
# File handling and initialization
# ---------------------------------------------------------------------


def test_initialize_log_file(tmp_path):
    log_file = tmp_path / "init.log"
    Logger(log_file=str(log_file))
    assert log_file.exists()
    assert log_file.read_text() == ""


def test_log_to_file_creates_file(tmp_path):
    log_file = tmp_path / "logfile.log"
    logger = Logger(log_file=str(log_file))
    logger._file_initialized = False  # Force re-init
    logger._log_to_file("[INFO] Trigger init")
    assert log_file.read_text().strip() == "[INFO] Trigger init"


def test_log_to_file_handles_exception(monkeypatch):
    logger = Logger(log_file="/nonexistent_dir/test.log")
    monkeypatch.setattr("builtins.open", MagicMock(side_effect=OSError("IO error")))
    # should print warning, not raise
    logger._log_to_file("msg")


def test_initialize_log_file_failure(monkeypatch):
    monkeypatch.setattr("builtins.open", MagicMock(side_effect=OSError("init fail")))
    logger = Logger(log_file="bad.log")
    assert not logger._file_initialized


# ---------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------


def test_context_manager(tmp_path):
    log_file = tmp_path / "ctx.log"
    with Logger(log_file=str(log_file)) as logger:
        logger.log_buffer = "Context log"
    assert "Context log" in log_file.read_text()


# ---------------------------------------------------------------------
# Extraction and levels
# ---------------------------------------------------------------------


def test_extract_level_variants():
    logger = Logger()
    assert logger._extract_level("[FAIL] Something broke") == "FAIL"
    assert logger._extract_level("[info] lower") == "INFO"
    assert logger._extract_level("No tag") == "INFO"


# ---------------------------------------------------------------------
# HTML + File combined
# ---------------------------------------------------------------------


def test_log_to_html_and_file(tmp_path):
    log_file = tmp_path / "combo.log"
    logger = Logger(log_file=str(log_file), html_file="dummy.html")
    logger.report_generator = MagicMock()
    logger.log("[PASS] Combo", to_log_file=True, html_log=True, to_console=False)
    assert logger.log_entries[0]["message"] == "[PASS] Combo"
    assert "Combo" in log_file.read_text()
