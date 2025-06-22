import os
import pytest
from unittest.mock import MagicMock, patch
from py_micro_hil.logger import Logger


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


def test_html_log_deduplication():
    mock_report = MagicMock()
    logger = Logger(html_file="dummy.html")
    logger.report_generator = mock_report
    logger.log("[PASS] Duplicate", html_log=True)
    logger.log("[PASS] Duplicate", html_log=True)  # should not be added twice
    assert len(logger.log_entries) == 1


def test_extract_level():
    logger = Logger()
    assert logger._extract_level("[FAIL] Something broke") == "FAIL"
    assert logger._extract_level("No tag") == "INFO"


def test_generate_html_report():
    logger = Logger(html_file="dummy.html")
    logger.report_generator = MagicMock()
    logger.generate_html_report(["group1"])
    logger.report_generator.generate.assert_called_once()


def test_should_log_to_html():
    logger = Logger(html_file="dummy.html")
    logger.report_generator = MagicMock()
    assert logger._should_log_to_html("[INFO] Log this") is True
    logger.log_entries.append({"message": "[INFO] Log this"})
    assert logger._should_log_to_html("[INFO] Log this") is False


def test_context_manager(tmp_path):
    log_file = tmp_path / "ctx.log"
    with Logger(log_file=str(log_file)) as logger:
        logger.log_buffer = "Context log"
    assert "Context log" in log_file.read_text()


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


def test_log_to_html_and_file(tmp_path):
    log_file = tmp_path / "combo.log"
    logger = Logger(log_file=str(log_file), html_file="dummy.html")
    logger.report_generator = MagicMock()
    logger.log("[PASS] Combo", to_log_file=True, html_log=True, to_console=False)
    assert logger.log_entries[0]["message"] == "[PASS] Combo"
    assert "Combo" in log_file.read_text()


def test_log_coloring(monkeypatch):
    logger = Logger()
    monkeypatch.setattr("builtins.print", lambda msg: setattr(logger, "_printed", msg))
    logger.log("[FAIL] should be red")
    assert "[" in logger._printed and "]" in logger._printed
