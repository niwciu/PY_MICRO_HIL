import re
from termcolor import colored
from py_micro_hil.report_generator import ReportGenerator


class Logger:
    """
    Logging utility for test framework output, supporting console, file, and HTML reporting.
    """

    COLORS = {
        'PASS': 'green',
        'FAIL': 'red',
        'ERROR': 'red',
        'INFO': 'blue',
        'WARNING': 'yellow'
    }

    def __init__(self, log_file=None, html_file=None):
        """
        Initializes the logger instance.
        :param log_file: Optional path to a log file.
        :param html_file: Optional path to an HTML report file.
        """
        self.log_file = log_file
        self.html_file = html_file
        self.log_buffer = ""
        self._file_initialized = False
        self.log_entries = []
        self.last_message = None
        self.report_generator = ReportGenerator(self) if html_file else None

        if self.log_file:
            self._initialize_log_file()

    def log(self, message, to_console=True, to_log_file=False, html_log=False):
        """
        Logs a message to the specified targets.
        :param message: The message to log.
        :param to_console: If True, outputs to console.
        :param to_log_file: If True, appends to the log file.
        :param html_log: If True, stores the message for HTML report generation.
        """
        self.last_message = message
        if to_console:
            self._log_to_console(message)
        if to_log_file and self.log_file:
            self._log_to_file(message)
        if html_log and self._should_log_to_html(message):
            self.log_entries.append({
                "level": self._extract_level(message),
                "message": message
            })

    def _should_log_to_html(self, message):
        """
        Determines whether the message should be included in the HTML report.
        :param message: The message to check.
        :return: True if it should be added, False otherwise.
        """
        return self.report_generator and (
            not self.log_entries or self.log_entries[-1]["message"] != message
        )

    def _log_to_console(self, message):
        """
        Outputs the message to the console with color formatting.
        :param message: The message to print.
        """
        message_with_color = re.sub(
            r'\[(PASS|FAIL|INFO|WARNING|ERROR)\]',
            lambda m: '[' + colored(m.group(1), self.COLORS.get(m.group(1), 'white')) + ']',
            message
        )
        print(message_with_color)

    def _log_to_file(self, message):
        """
        Writes the message to the log file.
        :param message: The message to write.
        """
        if not self._file_initialized:
            self._initialize_log_file()
        with open(self.log_file, 'a') as f:
            f.write(message + "\n")

    def _initialize_log_file(self):
        """
        Initializes the log file by creating or clearing it.
        """
        with open(self.log_file, 'w') as f:
            f.write("")
        self._file_initialized = True

    def flush_log(self):
        """
        Flushes the current log buffer to the log file.
        """
        if not self.log_file:
            return
        with open(self.log_file, 'a') as log_file:
            log_file.write(self.log_buffer)
        self.log_buffer = ""

    def generate_html_report(self, test_groups):
        """
        Generates an HTML report if HTML logging is enabled.
        :param test_groups: List of test group results to include in the report.
        """
        if self.report_generator:
            self.report_generator.generate(test_groups)

    def _extract_level(self, message):
        """
        Extracts the log level from a message string.
        :param message: The message string.
        :return: The log level (e.g., 'INFO', 'FAIL').
        """
        match = re.search(r'\[(PASS|FAIL|INFO|WARNING|ERROR)\]', message)
        return match.group(1) if match else "INFO"

    def __enter__(self):
        """
        Enters the logger context (used with 'with' statements).
        :return: The logger instance.
        """
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Exits the logger context, flushing any buffered log data.
        """
        self.flush_log()
