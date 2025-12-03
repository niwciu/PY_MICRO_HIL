import os
import pytest
from unittest.mock import Mock, patch
from py_micro_hil.report_generator import ReportGenerator


@pytest.fixture
def dummy_templates(tmp_path):
    """Tworzy zestaw minimalnych szablonów HTML i CSS potrzebnych do działania ReportGenerator."""
    template_dir = tmp_path / "templates"
    template_dir.mkdir()

    (template_dir / "report_template.html").write_text(
        """
        <html><body>
        <h1>Test Summary</h1>
        Total: {{ total_tests }}, Passed: {{ passed }}, Failed: {{ failed }}
        </body></html>
    """,
        encoding="utf-8",
    )

    (template_dir / "test_code_template.html").write_text(
        """
        <html><body>
        <h2>{{ group_name }}</h2>
        {% for test in tests %}
        <div id="{{ test.id }}">{{ test.test_name }}<pre>{{ test.code }}</pre></div>
        {% endfor %}
        </body></html>
    """,
        encoding="utf-8",
    )

    (template_dir / "styles.css").write_text("body { font-family: sans-serif; }", encoding="utf-8")

    return template_dir


# -----------------------------------------------------------------------------
# MAIN REPORT GENERATION
# -----------------------------------------------------------------------------


def test_generate_report(tmp_path, dummy_templates):
    """Generuje kompletny raport HTML i kopiuje plik CSS."""
    mock_logger = Mock()
    mock_logger.html_file = str(tmp_path / "output" / "report.html")
    mock_logger.log_entries = [
        {
            "group_name": "Group A",
            "test_name": "Test A1",
            "level": "PASS",
            "message": "OK",
            "additional_info": "-",
        },
        {
            "group_name": "Group A",
            "test_name": "Test A2",
            "level": "FAIL",
            "message": "FAIL",
            "additional_info": "-",
        },
    ]

    mock_test = Mock()
    mock_test.name = "Test A1"
    mock_test.original_func = None

    mock_group = Mock()
    mock_group.name = "Group A"
    mock_group.tests = [mock_test]

    generator = ReportGenerator(mock_logger, template_dir=str(dummy_templates))
    generator.generate([mock_group])

    html_path = tmp_path / "output" / "report.html"
    css_path = tmp_path / "output" / "styles.css"
    assert html_path.exists()
    assert css_path.exists()

    content = html_path.read_text(encoding="utf-8")
    assert "Total: 2" in content
    assert "Passed: 1" in content
    assert "Failed: 1" in content
    mock_logger.log.assert_any_call(
        f"✅ HTML report generated at: {os.path.abspath(html_path)}", to_console=True
    )


def test_generate_empty_groups(tmp_path, dummy_templates):
    """Sprawdza, że brak grup testowych nie powoduje błędu i generuje pusty raport."""
    mock_logger = Mock()
    mock_logger.html_file = str(tmp_path / "empty" / "report.html")
    mock_logger.log_entries = []

    generator = ReportGenerator(mock_logger, template_dir=str(dummy_templates))
    generator.generate([])

    html_path = tmp_path / "empty" / "report.html"
    assert html_path.exists()
    content = html_path.read_text(encoding="utf-8")
    assert "Total:" in content


def test_generate_skips_if_no_html(tmp_path, dummy_templates):
    """Jeśli logger.html_file = None, raport nie jest generowany."""
    mock_logger = Mock()
    mock_logger.html_file = None
    mock_logger.log_entries = []

    generator = ReportGenerator(mock_logger, template_dir=str(dummy_templates))
    generator.generate([])

    # brak pliku
    output_dir = tmp_path / "output"
    assert not any(output_dir.glob("*.html"))


# -----------------------------------------------------------------------------
# TEST CODE PAGES
# -----------------------------------------------------------------------------


def test_generate_test_code_pages(tmp_path, dummy_templates):
    """Generuje strony kodu źródłowego testów."""
    html_dir = tmp_path / "html"
    html_dir.mkdir()

    def dummy_test_func():
        pass

    mock_test = Mock()
    mock_test.name = "Example Test"
    mock_test.original_func = dummy_test_func

    mock_group = Mock()
    mock_group.name = "Some Group"
    mock_group.tests = [mock_test]

    mock_logger = Mock()
    mock_logger.html_file = str(html_dir / "report.html")
    mock_logger.log_entries = []

    generator = ReportGenerator(mock_logger, template_dir=str(dummy_templates))
    generator.generate_test_code_pages([mock_group], str(html_dir))

    test_file = html_dir / "some_group_tests.html"
    assert test_file.exists()
    content = test_file.read_text(encoding="utf-8")
    assert "Example Test" in content
    assert "def dummy_test_func" in content


def test_source_extraction_failure(tmp_path, dummy_templates):
    """Błąd przy pobieraniu źródła funkcji nie przerywa generowania."""

    class BrokenFunc:
        def __getattr__(self, item):
            raise Exception("Cannot inspect")

    mock_test = Mock()
    mock_test.name = "Bad Test"
    mock_test.original_func = BrokenFunc()

    mock_group = Mock()
    mock_group.name = "Group Broken"
    mock_group.tests = [mock_test]

    mock_logger = Mock()
    mock_logger.html_file = str(tmp_path / "report.html")
    mock_logger.log_entries = []

    generator = ReportGenerator(mock_logger, template_dir=str(dummy_templates))

    # Powinien utworzyć plik mimo błędu
    generator.generate_test_code_pages([mock_group], str(tmp_path))
    broken_file = tmp_path / "group_broken_tests.html"
    assert broken_file.exists()
    assert "Bad Test" not in broken_file.read_text(encoding="utf-8")


# -----------------------------------------------------------------------------
# FILE VALIDATION
# -----------------------------------------------------------------------------


def test_missing_template_raises(tmp_path):
    """Brak pliku report_template.html powoduje wyjątek."""
    broken_template_dir = tmp_path / "broken"
    broken_template_dir.mkdir()
    (broken_template_dir / "styles.css").write_text("", encoding="utf-8")

    with pytest.raises(FileNotFoundError):
        ReportGenerator(Mock(), template_dir=str(broken_template_dir))


def test_missing_css_raises(tmp_path):
    """Brak pliku styles.css powoduje wyjątek."""
    broken_template_dir = tmp_path / "broken"
    broken_template_dir.mkdir()
    (broken_template_dir / "report_template.html").write_text("", encoding="utf-8")

    with pytest.raises(FileNotFoundError):
        ReportGenerator(Mock(), template_dir=str(broken_template_dir))


def test_template_not_found_raises(tmp_path):
    """Brak pliku test_code_template.html powoduje wyjątek."""
    broken_template_dir = tmp_path / "missing_template"
    broken_template_dir.mkdir()
    (broken_template_dir / "report_template.html").write_text("OK", encoding="utf-8")
    (broken_template_dir / "styles.css").write_text("body{}", encoding="utf-8")

    with pytest.raises(FileNotFoundError) as exc:
        ReportGenerator(Mock(), template_dir=str(broken_template_dir))
    assert "Required template not found" in str(exc.value)


# -----------------------------------------------------------------------------
# LOGGING & FALLBACK
# -----------------------------------------------------------------------------


def test_log_falls_back_to_print(tmp_path, dummy_templates, capsys):
    """Jeśli logger nie ma metody log(), _log() powinno użyć print()."""
    logger_without_log = Mock(spec=[])
    logger_without_log.html_file = None
    logger_without_log.log_entries = []

    generator = ReportGenerator(logger_without_log, template_dir=str(dummy_templates))
    generator._log("test message")
    captured = capsys.readouterr()
    assert "test message" in captured.out


def test_failed_copy_css_logs_warning(tmp_path, dummy_templates):
    """Błąd przy kopiowaniu CSS nie przerywa generowania raportu."""
    mock_logger = Mock()
    mock_logger.html_file = str(tmp_path / "out" / "report.html")
    mock_logger.log_entries = []

    generator = ReportGenerator(mock_logger, template_dir=str(dummy_templates))

    with patch("shutil.copy", side_effect=PermissionError("no permission")):
        generator.generate([])

    # Sprawdź, że w logach pojawiła się informacja o błędzie CSS
    calls = [str(call.args[0]) for call in mock_logger.log.call_args_list]
    assert any("Could not copy CSS" in msg for msg in calls)
