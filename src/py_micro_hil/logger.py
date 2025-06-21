### --- LOGGER.PY ---
import re
from termcolor import colored
from py_micro_hil.report_generator import ReportGenerator


class Logger:
    def __init__(self, log_file=None, html_file=None):
        self.log_file = log_file
        self.html_file = html_file
        self.log_buffer = ""
        self._file_initialized = False
        self.log_entries = []
        self.report_generator = ReportGenerator(html_file) if html_file else None

        if self.log_file:
            self._initialize_log_file()

    def log(self, message, to_console=True, to_log_file=False, html_log=False):
        if to_console:
            self._log_to_console(message)
        if to_log_file and self.log_file:
            self._log_to_file(message)
        if html_log and self.report_generator:
            if not self.log_entries or self.log_entries[-1]["message"] != message:
                self.log_entries.append({"level": self._extract_level(message), "message": message})

    def _log_to_console(self, message):
        message_with_color = re.sub(
            r'\[(PASS|FAIL|INFO|WARNING|ERROR)\]',
            lambda m: '[' + colored(
                m.group(1),
                'green' if m.group(1) == 'PASS' else
                'red' if m.group(1) in ('FAIL', 'ERROR') else
                'blue' if m.group(1) == 'INFO' else 'yellow') + ']',
            message
        )
        print(message_with_color)

    def _log_to_file(self, message):
        if not self._file_initialized:
            self._initialize_log_file()
        with open(self.log_file, 'a') as f:
            f.write(message + "\n")

    def _initialize_log_file(self):
        with open(self.log_file, 'w') as f:
            f.write("")
        self._file_initialized = True

    def flush_log(self):
        if not self.log_file:
            return
        with open(self.log_file, 'a') as log_file:
            log_file.write(self.log_buffer)
        self.log_buffer = ""

    def generate_html_report(self, test_groups):
        if self.report_generator:
            self.report_generator.generate(test_groups, self.log_entries)

    def _extract_level(self, message):
        match = re.search(r'\[(PASS|FAIL|INFO|WARNING|ERROR)\]', message)
        return match.group(1) if match else "INFO"

