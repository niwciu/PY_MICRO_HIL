import os
import re
import shutil
import inspect
from jinja2 import Environment, FileSystemLoader


class ReportGenerationError(RuntimeError):
    """Raised when report generation fails due to missing files or templates."""

    pass


class ReportGenerator:
    """
    Responsible for generating HTML reports from test results using Jinja2 templates.
    """

    def __init__(self, logger, template_dir: str | None = None):
        """
        Initializes the report generator with templates and a logger.

        :param logger: Logger instance for console/file logging.
        :param template_dir: Optional path to custom template directory.
        :raises FileNotFoundError: If required templates or CSS are missing.
        """
        self.logger = logger
        self.template_path = template_dir or os.path.join(os.path.dirname(__file__), "templates")

        self.template_file = os.path.join(self.template_path, "report_template.html")
        self.group_template_file = os.path.join(self.template_path, "test_code_template.html")
        self.css_file = os.path.join(self.template_path, "styles.css")

        # Verify template and CSS existence
        for required_file, label in (
            (self.template_file, "HTML template"),
            (self.group_template_file, "Test code template"),
            (self.css_file, "CSS"),
        ):
            if not os.path.exists(required_file):
                message = (
                    f"Required template not found: {required_file}"
                    if "template" in label.lower()
                    else f"{label} file not found: {required_file}"
                )
                self._log(message)
                raise FileNotFoundError(message)

        # Initialize Jinja2 environment when available; fallback rendering is used otherwise
        self.env = None
        self.template = None
        self.group_template = None
        try:
            self.env = Environment(loader=FileSystemLoader(self.template_path))
            self.template = self.env.get_template("report_template.html")
            self.group_template = self.env.get_template("test_code_template.html")
        except Exception:
            self.env = None
            self.template = None
            self.group_template = None

        if self.env and not self.env.__class__.__module__.startswith("jinja2"):
            self.template = None
            self.group_template = None

    # -------------------------------------------------------------------------
    # Logging helper
    # -------------------------------------------------------------------------

    def _log(self, msg: str) -> None:
        """Logs a message using the provided logger, or prints to console if unavailable."""
        if hasattr(self.logger, "log"):
            self.logger.log(msg, to_console=True)
        else:
            print(msg)

    # -------------------------------------------------------------------------
    # Main report generation
    # -------------------------------------------------------------------------

    def generate(self, test_groups: list) -> None:
        """
        Generates a complete HTML test report, including per-group test code pages.

        :param test_groups: List of test group objects containing test metadata.
        :raises ReportGenerationError: If generation fails due to I/O or rendering issues.
        """
        html_file = getattr(self.logger, "html_file", None)
        if not html_file:
            self._log("⚠️  No HTML file provided, skipping report generation.")
            return

        html_path = os.path.abspath(html_file)
        html_dir = os.path.dirname(html_path)
        os.makedirs(html_dir, exist_ok=True)

        if not test_groups:
            self._log("⚠️  No test groups provided. Generating empty report.")

        try:
            self.generate_test_code_pages(test_groups, html_dir)

            grouped_tests = {}
            for entry in getattr(self.logger, "log_entries", []):
                group_name = entry.get("group_name", "Ungrouped")
                if group_name not in grouped_tests:
                    grouped_tests[group_name] = {
                        "id": group_name.replace(" ", "_").lower(),
                        "name": group_name,
                        "tests": [],
                        "status": "PASS",
                        "summary": "",
                    }

                grouped_tests[group_name]["tests"].append(
                    {
                        "name": entry.get("test_name", "Unnamed Test"),
                        "status": entry["level"],
                        "details": entry.get("message", ""),
                        "info": entry.get("additional_info", "N/A"),
                    }
                )

                if entry["level"] == "FAIL":
                    grouped_tests[group_name]["status"] = "FAIL"

            summary = {
                "passed": len([e for e in self.logger.log_entries if e["level"] == "PASS"]),
                "failed": len([e for e in self.logger.log_entries if e["level"] == "FAIL"]),
            }
            summary["total_tests"] = summary["passed"] + summary["failed"]
            summary["pass_percentage"] = (
                round((summary["passed"] / summary["total_tests"]) * 100, 1)
                if summary["total_tests"]
                else 0.0
            )
            summary["fail_percentage"] = round(100 - summary["pass_percentage"], 1)

            for group in grouped_tests.values():
                pass_count = len([t for t in group["tests"] if t["status"] == "PASS"])
                fail_count = len([t for t in group["tests"] if t["status"] == "FAIL"])
                group["summary"] = f"{pass_count} PASS, {fail_count} FAIL"

            context = {
                "total_tests": summary["total_tests"],
                "passed": summary["passed"],
                "failed": summary["failed"],
                "pass_percentage": summary["pass_percentage"],
                "fail_percentage": summary["fail_percentage"],
                "test_results": list(grouped_tests.values()),
            }

            if self.template:
                rendered_html = self.template.render(**context)
            else:
                rendered_html = self._render_simple_report(context)

            with open(html_path, "w", encoding="utf-8") as f:
                f.write(rendered_html)

            try:
                shutil.copy(self.css_file, os.path.join(html_dir, "styles.css"))
            except Exception as e:
                self._log(f"⚠️  Could not copy CSS file: {e}")

            self._log(f"✅ HTML report generated at: {html_path}")

        except Exception as e:
            raise ReportGenerationError(f"Failed to generate HTML report: {e}") from e

    # -------------------------------------------------------------------------
    # Per-group source pages
    # -------------------------------------------------------------------------

    def generate_test_code_pages(self, test_groups: list, html_dir: str) -> None:
        """
        Generates individual HTML pages for each test group, showing test source code.

        :param test_groups: List of test group objects containing test functions.
        :param html_dir: Path to directory where HTML files should be saved.
        """
        for group in test_groups:
            group_name = group.name
            group_file_name = f"{group_name.replace(' ', '_').lower()}_tests.html"
            group_file = os.path.join(html_dir, group_file_name)

            test_code_entries = []
            for test in group.tests:
                if test.original_func:
                    try:
                        test_code = inspect.getsource(test.original_func)
                        test_id = re.sub(r"[^a-zA-Z0-9_]", "_", test.name).lower()
                        test.info = f"{group_file_name}#{test_id}"

                        for entry in self.logger.log_entries:
                            if (
                                entry.get("test_name") == test.name
                                and entry.get("group_name") == group.name
                            ):
                                entry["additional_info"] = test.info

                        test_code_entries.append(
                            {
                                "test_name": test.name,
                                "code": test_code,
                                "id": test_id,
                            }
                        )
                    except Exception as e:
                        self._log(f"⚠️  Could not extract source for test '{test.name}': {e}")
                        continue

            if self.group_template:
                rendered = self.group_template.render(
                    group_name=group_name, tests=test_code_entries
                )
            else:
                rendered = self._render_simple_group_page(group_name, test_code_entries)
            with open(group_file, "w", encoding="utf-8") as f:
                f.write(rendered)

            self._log(f"Generated test code page: {group_file_name}")

    # ---------------------------------------------------------------------
    # Fallback rendering helpers (used when Jinja2 is not available)
    # ---------------------------------------------------------------------

    def _render_simple_report(self, context: dict) -> str:
        """Render a minimal HTML report without Jinja2 dependencies."""
        rows = []
        for group in context["test_results"]:
            rows.append(
                f"<div class='group'><h2>{group['name']}</h2>"
                + "".join(
                    f"<div class='test {t['status'].lower()}'><strong>{t['name']}</strong>"
                    f" - {t['status']}: {t['details']}</div>"
                    for t in group["tests"]
                )
                + "</div>"
            )

        return (
            "<html><body>"
            f"<h1>Test Summary</h1>"
            f"Total: {context['total_tests']}, Passed: {context['passed']}, Failed: {context['failed']}"
            + "".join(rows)
            + "</body></html>"
        )

    def _render_simple_group_page(self, group_name: str, tests: list[dict]) -> str:
        body = [f"<html><body><h2>{group_name}</h2>"]
        for test in tests:
            body.append(
                f"<div id='{test['id']}'><h3>{test['test_name']}</h3><pre>{test['code']}</pre></div>"
            )
        body.append("</body></html>")
        return "".join(body)
