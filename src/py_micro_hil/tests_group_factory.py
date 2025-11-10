import os
import inspect
from py_micro_hil.tests_framework import TestGroup, Test
from py_micro_hil.assertions import set_test_context, clear_test_context


def wrap_group_function(func, group_name: str, label: str):
    """Wraps a group-level setup or teardown function with context handling."""
    def wrapper(framework):
        set_test_context(framework, group_name, label)
        try:
            func()
        finally:
            clear_test_context()
    return wrapper


def make_wrapped_test(test_func, test_name: str, group_name: str):
    """Wraps an individual test function with context management and signature handling."""
    def wrapped_test(framework, test_func=test_func, test_name=test_name):
        set_test_context(framework, group_name, test_name)
        try:
            sig = inspect.signature(test_func)
            if len(sig.parameters) == 0:
                test_func()
            else:
                test_func(framework)
        finally:
            clear_test_context()
    return wrapped_test


def add_tests_from_module(group: TestGroup, module: object, group_name: str):
    """Discovers and adds test functions from the given module to the test group."""
    for attr_name in dir(module):
        if attr_name.startswith('test_'):
            test_func = getattr(module, attr_name)
            if callable(test_func):
                wrapped = make_wrapped_test(test_func, attr_name, group_name)
                group.add_test(Test(attr_name, wrapped, test_func))


def create_test_group_from_module(module: object) -> TestGroup:
    """
    Dynamically creates a TestGroup from a module by registering setup, teardown,
    and test functions.
    """
    group_name = module.__name__.split('.')[-1]
    test_file = os.path.abspath(inspect.getsourcefile(module))
    group = TestGroup(group_name, test_file)

    # Setup
    setup_func = getattr(module, 'setup_group', None)
    if setup_func:
        group.set_setup(wrap_group_function(setup_func, group_name, "Global Setup"))

    # Teardown
    teardown_func = getattr(module, 'teardown_group', None)
    if teardown_func:
        group.set_teardown(wrap_group_function(teardown_func, group_name, "Global Teardown"))

    # Test discovery and registration
    add_tests_from_module(group, module, group_name)

    return group
