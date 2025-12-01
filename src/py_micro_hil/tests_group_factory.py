import os
import inspect
from types import ModuleType
from typing import Callable

from py_micro_hil.tests_framework import TestGroup, Test, TestFramework
from py_micro_hil.assertions import set_test_context, clear_test_context


# =============================================================================
# WRAPPERS
# =============================================================================


def wrap_group_function(
    func: Callable[[], None], group_name: str, label: str
) -> Callable[[TestFramework], None]:
    """
    Wraps a group-level setup or teardown function with context handling.

    :param func: The original setup/teardown function (no args expected).
    :param group_name: The name of the test group.
    :param label: Descriptive label for logging context ("Global Setup"/"Global Teardown").
    :return: Wrapped callable that can be executed by TestGroup.
    """

    def wrapper(framework: TestFramework) -> None:
        set_test_context(framework, group_name, label)
        try:
            func()
        finally:
            clear_test_context()

    return wrapper


def make_wrapped_test(
    test_func: Callable, test_name: str, group_name: str
) -> Callable[[TestFramework], None]:
    """
    Wraps an individual test function with context management and flexible signature support.

    :param test_func: The test function to be wrapped.
    :param test_name: The name of the test (usually its function name).
    :param group_name: The name of the test group this test belongs to.
    :return: Wrapped callable that handles context and parameter introspection.
    """

    def wrapped_test(framework: TestFramework, test_func=test_func, test_name=test_name) -> None:
        set_test_context(framework, group_name, test_name)
        try:
            sig = inspect.signature(test_func)
            # If test function accepts arguments, pass the framework instance
            if len(sig.parameters) == 0:
                test_func()
            else:
                test_func(framework)
        finally:
            clear_test_context()

    return wrapped_test


# =============================================================================
# MODULE PARSING
# =============================================================================


def add_tests_from_module(group: TestGroup, module: ModuleType, group_name: str) -> None:
    """
    Discovers and adds test functions from the given module to the specified TestGroup.

    :param group: The TestGroup instance to which tests will be added.
    :param module: The module to inspect for test functions.
    :param group_name: The logical name of the test group.
    """
    for attr_name, test_func in module.__dict__.items():
        if attr_name.startswith("test_") and callable(test_func):
            wrapped = make_wrapped_test(test_func, attr_name, group_name)
            group.add_test(Test(attr_name, wrapped, test_func))


def create_test_group_from_module(module: ModuleType) -> TestGroup:
    """
    Dynamically creates a TestGroup from a given module by registering setup, teardown,
    and all test functions found in the module.

    :param module: Python module containing test_* functions.
    :return: A fully configured TestGroup ready for execution.
    """
    group_name = module.__name__.split(".")[-1]
    src_file = inspect.getsourcefile(module)
    test_file = os.path.abspath(src_file) if src_file else "(unknown source)"

    group = TestGroup(group_name, test_file)

    # Optional setup and teardown
    setup_func = getattr(module, "setup_group", None)
    if callable(setup_func):
        group.set_setup(wrap_group_function(setup_func, group_name, "Global Setup"))

    teardown_func = getattr(module, "teardown_group", None)
    if callable(teardown_func):
        group.set_teardown(wrap_group_function(teardown_func, group_name, "Global Teardown"))

    # Discover and register tests
    add_tests_from_module(group, module, group_name)

    return group
