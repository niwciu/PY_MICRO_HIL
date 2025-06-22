from contextvars import ContextVar

# Create context variables
_current_framework = ContextVar("framework", default=None)
_current_group_name = ContextVar("group_name", default=None)
_current_test_name = ContextVar("test_name", default=None)


def set_test_context(framework, group_name, test_name):
    """
    Sets the global test context.
    :param framework: The test framework instance.
    :param group_name: The name of the test group.
    :param test_name: The name of the test.
    """
    _current_framework.set(framework)
    _current_group_name.set(group_name)
    _current_test_name.set(test_name)


def clear_test_context():
    """
    Clears the global test context.
    """
    _current_framework.set(None)
    _current_group_name.set(None)
    _current_test_name.set(None)


def _get_context(context=None):
    return {
        "framework": context.get("framework") if context else _current_framework.get(),
        "group_name": context.get("group_name") if context else _current_group_name.get(),
        "test_name": context.get("test_name") if context else _current_test_name.get(),
    }


def _report_result(ctx, passed, message=None):
    ctx["framework"].report_test_result(
        ctx["group_name"],
        ctx["test_name"],
        passed,
        message
    )


def _report_info(ctx, message):
    ctx["framework"].report_test_info(
        ctx["group_name"],
        ctx["test_name"],
        message
    )


def TEST_FAIL_MESSAGE(message, context=None):
    """
    Assertion that reports test failure with a given message.
    If the context is available, it reports via the framework.
    Otherwise, it returns a symbolic representation for deferred execution.
    """
    ctx = _get_context(context)
    if ctx["framework"]:
        _report_result(ctx, False, message)
    else:
        return ("TEST_FAIL_MESSAGE", message)


def TEST_INFO_MESSAGE(message, context=None):
    """
    Logs an informational message.
    If the context is available, it logs via the framework.
    Otherwise, it returns a symbolic representation for deferred execution.
    """
    ctx = _get_context(context)
    if ctx["framework"]:
        _report_info(ctx, message)
    else:
        return ("TEST_INFO_MESSAGE", message)


def TEST_ASSERT_EQUAL(expected, actual, context=None):
    """
    Symbolic assertion that checks equality.
    :param expected: The expected value.
    :param actual: The actual value.
    :param context: (Optional) A dict containing the framework, group and test name.
    """
    ctx = _get_context(context)
    if ctx["framework"]:
        if expected != actual:
            _report_result(ctx, False, f"Assertion failed! Expected = {expected}, actual = {actual}")
        else:
            _report_result(ctx, True)
    else:
        return ("TEST_ASSERT_EQUAL", actual, expected)


def TEST_ASSERT_TRUE(condition, context=None):
    """
    Symbolic assertion that checks if a condition is true.
    :param condition: The condition to evaluate.
    :param context: (Optional) A dict containing the framework, group and test name.
    """
    ctx = _get_context(context)
    if ctx["framework"]:
        if not condition:
            _report_result(ctx, False, "Assertion failed: condition is not true")
        else:
            _report_result(ctx, True)
    else:
        return ("TEST_ASSERT_TRUE", condition)


def TEST_ASSERT_IN(item, collection, context=None):
    """
    Symbolic assertion that checks if an item is in a collection.
    :param item: The item to look for.
    :param collection: The collection to search.
    :param context: (Optional) A dict containing the framework, group and test name.
    """
    ctx = _get_context(context)
    if ctx["framework"]:
        if item not in collection:
            _report_result(ctx, False, f"Assertion failed: {item} not in {collection}")
        else:
            _report_result(ctx, True)
    else:
        return ("TEST_ASSERT_IN", item, collection)
