import os
import re
import shutil
import inspect
from termcolor import colored
from jinja2 import Environment, FileSystemLoader

class Logger:
    def __init__(self, log_file=None, html_file=None):
        """
        Initializes the logger.
        :param log_file: Path to the log file.
        :param html_file: Path to the HTML report file.
        """
        self.log_file = log_file
        self.html_file = html_file
        self.log_buffer = ""  # Buffer for log messages
        self._file_initialized = False  # Ensure log file is initialized only once
        self.log_entries = []  # Collects log entries for the HTML report

        # Initialize HTML report template if html_file is provided
        if self.html_file:
            print(f"HTML report requested. HTML file: {self.html_file}")
            template_path = os.path.join(os.path.dirname(__file__), 'templates')
            template_file = os.path.join(template_path, 'report_template.html')
            css_file = os.path.join(template_path, 'styles.css')
            print(f"Looking for HTML template at: {template_file}")
            if not os.path.exists(template_file):
                raise FileNotFoundError(f"HTML template file not found: {template_file}")
            if not os.path.exists(css_file):
                raise FileNotFoundError(f"CSS file not found: {css_file}")
            try:
                self.env = Environment(loader=FileSystemLoader(template_path))
                self.template = self.env.get_template('report_template.html')
                self.group_template = self.env.get_template('test_code_template.html')
                self.css_file = css_file
                print(f"HTML template and CSS loaded successfully from {template_path}")
            except Exception as e:
                raise RuntimeError(f"Failed to load HTML template or CSS: {e}")

        if self.log_file:
            self._initialize_log_file()

    def log(self, message, to_console=True, to_log_file=False, html_log=False):
        """
        Logs a message to console, log file, and/or HTML report.
        :param message: The message to log.
        :param to_console: Whether to log to console.
        :param to_log_file: Whether to log to file.
        :param html_log: Whether to log to HTML report.
        """
        if to_console:
            self._log_to_console(message)

        if to_log_file and self.log_file:
            self._log_to_file(message)

        if html_log and self.html_file:
            # Avoid duplicate log entries in HTML
            if not self.log_entries or self.log_entries[-1]["message"] != message:
                self.log_entries.append({"level": self._extract_level(message), "message": message})

    def _log_to_console(self, message):
        """
        Logs a message to the console with color highlighting.
        """
        message_with_color = re.sub(
            r'\[(PASS|FAIL|INFO|WARNING|ERROR)\]',
            lambda m: '[' + colored(
                m.group(1),
                'green' if m.group(1) == 'PASS' else
                'red' if m.group(1) in ('FAIL', 'ERROR') else
                'blue' if m.group(1) == 'INFO' else
                'yellow'
            ) + ']',
            message
        )
        print(message_with_color)

    def _log_to_file(self, message):
        """
        Logs a message to a log file.
        """
        if not self._file_initialized:
            self._initialize_log_file()

        with open(self.log_file, 'a') as f:
            f.write(message + "\n")

    def _initialize_log_file(self):
        """
        Clears the log file at the first initialization.
        """
        with open(self.log_file, 'w') as f:
            f.write("")  # Create an empty log file
        self._file_initialized = True

    def flush_log(self):
        """
        Flushes the log buffer to the log file.
        """
        if not self.log_file:
            return

        with open(self.log_file, 'a') as log_file:
            log_file.write(self.log_buffer)
        self.log_buffer = ""

    def generate_html_report(self, test_groups=None):
        """
        Generates an HTML report with optional subpages for test code.
        """
        if not self.html_file:
            print("No HTML file provided, skipping report generation.")
            return

        # Ensure the directory for the HTML file exists
        html_dir = os.path.dirname(self.html_file)
        if html_dir and not os.path.exists(html_dir):
            os.makedirs(html_dir, exist_ok=True)

        if test_groups is None:
            print("Error: No test groups provided to generate_html_report.")
            return

        # Step 1: Generate test code pages first
        self.generate_test_code_pages(test_groups, html_dir)

        # Debugging updated log entries
        print("[DEBUG] Log Entries Before Grouping:")
        for entry in self.log_entries:
            print(entry)
            for group in test_groups:
                if group.name == entry.get("group_name"):
                    for test in group.tests:
                        if test.name == entry.get("test_name"):
                            entry["additional_info"] = test.info
                            print(f"[DEBUG] Log Entry Updated: {entry}")
                            break

        # Step 2: Prepare summary for the main report
        summary = {
            "passed": len([entry for entry in self.log_entries if entry["level"] == "PASS"]),
            "failed": len([entry for entry in self.log_entries if entry["level"] == "FAIL"]),
        }
        summary["total_tests"] = summary["passed"] + summary["failed"]
        summary["pass_percentage"] = (
            round((summary["passed"] / summary["total_tests"] * 100),1) if summary["total_tests"] > 0 else 0
        )
        summary["fail_percentage"] = round(100 - summary["pass_percentage"],1)

        # Group test results for rendering
        grouped_tests = {}

        # Debug log entries before grouping
        print("[DEBUG] Log Entries Before Grouping:")
        for entry in self.log_entries:
            print(entry)

        for entry in self.log_entries:
            group_name = entry.get("group_name", "Ungrouped")
            if not group_name:
                print(f"[DEBUG] Skipping test: {entry} (no group_name)")
                continue

            if group_name not in grouped_tests:
                grouped_tests[group_name] = {
                    "id": group_name.replace(" ", "_").lower(),
                    "name": group_name,
                    "tests": [],
                    "status": "PASS",  # Default to PASS until a FAIL is found
                    "summary": "",
                }

            grouped_tests[group_name]["tests"].append({
                "name": entry.get("test_name", "Unnamed Test"),
                "status": entry["level"],
                "details": entry.get("message", ""),
                "info": entry.get("additional_info", "N/A"),
            })

            if entry["level"] == "FAIL":
                grouped_tests[group_name]["status"] = "FAIL"

        # Debug grouped tests
        print("[DEBUG] Grouped Tests After Grouping:")
        for group_name, group_data in grouped_tests.items():
            print(f"Group: {group_name}")
            for test in group_data["tests"]:
                print(f"  Test: {test['name']}, Status: {test['status']}, Info: {test['info']}")

        # Add summaries for groups
        print("[DEBUG] Test Results Passed to Template:")
        for group in grouped_tests.values():
            pass_count = len([t for t in group["tests"] if t["status"] == "PASS"])
            fail_count = len([t for t in group["tests"] if t["status"] == "FAIL"])
            group["summary"] = f"{pass_count} PASS, {fail_count} FAIL"
            print(f"[DEBUG] Summary for Group '{group['name']}': {group['summary']} (Total: {len(group['tests'])})")



        # Step 3: Render the main HTML report
        rendered_html = self.template.render(
            total_tests=summary["total_tests"],
            passed=summary["passed"],
            failed=summary["failed"],
            pass_percentage=summary["pass_percentage"],
            fail_percentage=summary["fail_percentage"],
            test_results=list(grouped_tests.values()),  # Przekazanie grouped_tests
        )


        # Write the main HTML report
        with open(self.html_file, "w", encoding="utf-8") as f:
            f.write(rendered_html)
        print(f"HTML report successfully written to: {self.html_file}")

        # Copy CSS file
        css_target_path = os.path.join(html_dir, "styles.css")
        shutil.copy(self.css_file, css_target_path)
        print(f"CSS file successfully copied to: {css_target_path}")



    def generate_test_code_pages(self, test_groups, html_dir):
        """
        Generates HTML subpages for test code.
        :param test_groups: List of test groups.
        :param html_dir: Directory for the generated HTML pages.
        """
        for group in test_groups:
            group_name = group.name
            group_file_name = f"{group_name.replace(' ', '_').lower()}_tests.html"
            group_file = os.path.join(html_dir, group_file_name)

            print(f"[DEBUG] Processing group: {group_name}, File: {group_file_name}")

            test_code_entries = []
            for test in group.tests:
                if test.original_func:
                    try:
                        test_file = inspect.getsourcefile(test.original_func)
                        test_code = inspect.getsource(test.original_func)
                        test_id = test.name.replace(" ", "_").lower()
                        test.info = f"{group_file_name}#{test_id}"  # Generujemy link bezpośrednio
                        test_code_entries.append({
                            "test_name": test.name,
                            "code": test_code,
                            "id": test_id,
                        })
                        print(f"[DEBUG] Test '{test.name}' found in file: {test_file}")
                    except Exception as e:
                        print(f"[DEBUG] Failed to extract code for test '{test.name}': {e}")
                else:
                    print(f"[DEBUG] Test '{test.name}' has no associated function.")

            # Render subpage for test group
            rendered_html = self.env.get_template("test_code_template.html").render(
                group_name=group_name,
                tests=test_code_entries
            )

            with open(group_file, "w", encoding="utf-8") as f:
                f.write(rendered_html)
            print(f"[DEBUG] Generated test code page for group '{group_name}': {group_file}")



    def _extract_level(self, message):
        """
        Extracts the log level from a message.
        """
        match = re.search(r'\[(PASS|FAIL|INFO|WARNING|ERROR)\]', message)
        return match.group(1) if match else "INFO"
