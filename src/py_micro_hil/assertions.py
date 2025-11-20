# pylint: disable=...
from contextvars import ContextVar
from typing import Optional, Any, Dict, Tuple

# ---------------------------------------------------------------------
# Context variables for active test state
# ---------------------------------------------------------------------

_current_framework: ContextVar[Optional[Any]] = ContextVar("framework", default=None)
_current_group_name: ContextVar[Optional[str]] = ContextVar("group_name", default=None)
_current_test_name: ContextVar[Optional[str]] = ContextVar("test_name", default=None)


# ---------------------------------------------------------------------
# Context management
# ---------------------------------------------------------------------


def set_test_context(framework: Any, group_name: str, test_name: str) -> None:
    """
    Sets the global test context.
    :param framework: The test framework instance.
    :param group_name: The name of the test group.
    :param test_name: The name of the test.
    """
    _current_framework.set(framework)
    _current_group_name.set(group_name)
    _current_test_name.set(test_name)


def clear_test_context() -> None:
    """
    Clears the global test context.
    """
    _current_framework.set(None)
    _current_group_name.set(None)
    _current_test_name.set(None)


def _get_context(context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Retrieve the active context, either from a provided dict or the ContextVars.
    """
    if context:
        return context
    return {
        "framework": _current_framework.get(),
        "group_name": _current_group_name.get(),
        "test_name": _current_test_name.get(),
    }


# ---------------------------------------------------------------------
# Internal reporting helpers
# ---------------------------------------------------------------------


def _report_result(ctx: Dict[str, Any], passed: bool, message: Optional[str] = None) -> bool:
    ctx["framework"].report_test_result(ctx["group_name"], ctx["test_name"], passed, message)
    return passed


def _report_info(ctx: Dict[str, Any], message: str) -> None:
    ctx["framework"].report_test_info(ctx["group_name"], ctx["test_name"], message)


# ---------------------------------------------------------------------
# Assertion helpers
# ---------------------------------------------------------------------


def TEST_FAIL_MESSAGE(
    message: str, context: Optional[Dict[str, Any]] = None
) -> Optional[Tuple[str, str]]:
    """
    Reports a test failure with the given message.
    If the framework context exists, logs via framework; otherwise returns a symbolic tuple.
    """
    ctx = _get_context(context)
    if ctx["framework"]:
        _report_result(ctx, False, message)
        return None
    return ("TEST_FAIL_MESSAGE", message)


def TEST_INFO_MESSAGE(
    message: str, context: Optional[Dict[str, Any]] = None
) -> Optional[Tuple[str, str]]:
    """
    Logs an informational message.
    If the framework context exists, logs via framework; otherwise returns a symbolic tuple.
    """
    ctx = _get_context(context)
    if ctx["framework"]:
        _report_info(ctx, message)
        return None
    return ("TEST_INFO_MESSAGE", message)


def TEST_ASSERT_EQUAL(
    expected: Any, actual: Any, context: Optional[Dict[str, Any]] = None
) -> Optional[Tuple[str, Any, Any]]:
    """
    Asserts that expected == actual.
    Reports via framework if context is active, otherwise returns a symbolic representation.
    """
    ctx = _get_context(context)
    if ctx["framework"]:
        try:
            if expected != actual:
                _report_result(
                    ctx, False, f"Assertion failed! Expected = {expected}, actual = {actual}"
                )
            else:
                _report_result(ctx, True)
        except Exception as e:
            _report_result(ctx, False, f"Comparison error: {e}")
        return None
    return ("TEST_ASSERT_EQUAL", actual, expected)


def TEST_ASSERT_TRUE(
    condition: Any, context: Optional[Dict[str, Any]] = None
) -> Optional[Tuple[str, Any]]:
    """
    Asserts that condition is True.
    Reports via framework if context is active, otherwise returns a symbolic representation.
    """
    ctx = _get_context(context)
    if ctx["framework"]:
        passed = bool(condition)
        if not passed:
            _report_result(ctx, False, "Assertion failed: condition is not true")
        else:
            _report_result(ctx, True)
        return None
    return ("TEST_ASSERT_TRUE", condition)


def TEST_ASSERT_IN(
    item: Any, collection: Any, context: Optional[Dict[str, Any]] = None
) -> Optional[Tuple[str, Any, Any]]:
    """
    Asserts that an item is present in the collection.
    Reports via framework if context is active, otherwise returns a symbolic representation.
    """
    ctx = _get_context(context)
    if ctx["framework"]:
        try:
            if item not in collection:
                _report_result(ctx, False, f"Assertion failed: {item} not in {collection}")
            else:
                _report_result(ctx, True)
        except Exception as e:
            _report_result(ctx, False, f"Membership check failed: {e}")
        return None
    return ("TEST_ASSERT_IN", item, collection)
