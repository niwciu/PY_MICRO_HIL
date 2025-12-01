import re
from typing import Any, Dict, List, Optional

try:
    from termcolor import colored
except ImportError:
    # Fallback, jeśli termcolor nie jest dostępny (np. na minimalnych systemach embedded)
    def colored(text: str, _: str) -> str:
        return text


from py_micro_hil.report_generator import ReportGenerator


class Logger:
    """
    Logging utility for test framework output, supporting console, file, and HTML reporting.
    """

    COLORS: Dict[str, str] = {
        "PASS": "green",
        "FAIL": "red",
        "ERROR": "red",
        "INFO": "blue",
        "WARNING": "yellow",
        "DEBUG": "cyan",  # ← DODANE
    }

    def __init__(
        self,
        log_file: Optional[str] = None,
        html_file: Optional[str] = None,
        debug_enabled: bool = False,
    ) -> None:
        """
        Initializes the logger instance.
        :param log_file: Optional path to a log file.
        :param html_file: Optional path to an HTML report file.
        :param debug_enabled: Controls whether `[DEBUG]` messages are emitted.
        """
        self.log_file = log_file
        self.html_file = html_file
        self.log_buffer: str = ""
        self._file_initialized: bool = False
        self.log_entries: List[Dict[str, Any]] = []
        self.last_message: Optional[str] = None
        self.debug_enabled = debug_enabled
        self.report_generator: Optional[ReportGenerator] = (
            ReportGenerator(self) if html_file else None
        )

        if self.log_file:
            self._initialize_log_file()

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def log(
        self,
        message: str,
        to_console: bool = True,
        to_log_file: bool = False,
        html_log: bool = False,
    ) -> None:
        """
        Logs a message to the specified targets.
        :param message: The message to log.
        :param to_console: If True, outputs to console.
        :param to_log_file: If True, appends to the log file.
        :param html_log: If True, stores the message for HTML report generation.
        """
        self.last_message = message

        if not self.debug_enabled and "[DEBUG]" in message:
            return

        if to_console:
            self._log_to_console(message)

        if to_log_file and self.log_file:
            self._log_to_file(message)

        if html_log and self._should_log_to_html(message):
            self.log_entries.append(
                {
                    "level": self._extract_level(message),
                    "message": message,
                }
            )

    def flush_log(self) -> None:
        """
        Flushes the current log buffer to the log file.
        """
        if not self.log_file or not self.log_buffer:
            return
        try:
            with open(self.log_file, "a", encoding="utf-8") as log_file:
                log_file.write(self.log_buffer)
            self.log_buffer = ""
        except Exception as e:
            print(f"[Logger Warning] Failed to flush log buffer: {e}")

    def generate_html_report(self, test_groups: List[Any]) -> None:
        """
        Generates an HTML report if HTML logging is enabled.
        :param test_groups: List of test group results to include in the report.
        """
        if self.report_generator:
            try:
                self.report_generator.generate(test_groups)
            except Exception as e:
                self.log(f"[ERROR] Failed to generate HTML report: {e}", to_console=True)

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _should_log_to_html(self, message: str) -> bool:
        """
        Determines whether the message should be included in the HTML report.
        Avoids duplicate consecutive messages and prevents unbounded growth.
        """
        if not self.report_generator:
            return False

        if not self.log_entries:
            return True

        if self.log_entries[-1]["message"] == message:
            return False

        # Limit stored entries to avoid memory bloat
        if len(self.log_entries) > 10_000:
            self.log_entries.pop(0)

        return True

    def _log_to_console(self, message: str) -> None:
        """
        Outputs the message to the console with color formatting.
        :param message: The message to print.
        """
        message_with_color = re.sub(
            r"\[(PASS|FAIL|INFO|WARNING|ERROR|DEBUG)\]",
            lambda m: "[" + colored(m.group(1), self.COLORS.get(m.group(1), "white")) + "]",
            message,
        )
        try:
            print(message_with_color)
        except Exception:
            # Fallback in environments with limited stdout
            pass

    def _log_to_file(self, message: str) -> None:
        """
        Writes the message to the log file.
        :param message: The message to write.
        """
        if not self._file_initialized:
            self._initialize_log_file()

        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(message + "\n")
        except Exception as e:
            print(f"[Logger Warning] Failed to write to {self.log_file}: {e}")

    def _initialize_log_file(self) -> None:
        """
        Initializes the log file by creating or clearing it.
        """
        try:
            with open(self.log_file, "w", encoding="utf-8") as f:
                f.write("")
            self._file_initialized = True
        except Exception as e:
            print(f"[Logger Warning] Could not initialize log file {self.log_file}: {e}")
            self._file_initialized = False

    def _extract_level(self, message: str) -> str:
        """
        Extracts the log level from a message string.
        :param message: The message string.
        :return: The log level (e.g., 'INFO', 'FAIL').
        """
        match = re.search(r"\[(PASS|FAIL|INFO|WARNING|ERROR|DEBUG)\]", message, re.IGNORECASE)
        return match.group(1).upper() if match else "INFO"

    # -------------------------------------------------------------------------
    # Context manager
    # -------------------------------------------------------------------------

    def __enter__(self) -> "Logger":
        """
        Enters the logger context (used with 'with' statements).
        :return: The logger instance.
        """
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """
        Exits the logger context, flushing any buffered log data.
        """
        self.flush_log()
