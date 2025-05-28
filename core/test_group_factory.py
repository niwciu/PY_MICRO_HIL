import os
import inspect
from core.test_framework import TestGroup, Test
from core.assertions import set_test_context, clear_test_context

def create_test_group_from_module(module):
    group_name = module.__name__.split('.')[-1]
    test_file = os.path.abspath(inspect.getsourcefile(module))

    group = TestGroup(group_name, test_file)

    # Setup
    setup_func = getattr(module, 'setup_group', None)
    if setup_func:
        def wrapped_setup(framework):
            set_test_context(framework, group_name, "Global Setup")
            try:
                setup_func()
            finally:
                clear_test_context()
        group.set_setup(wrapped_setup)

    # Teardown
    teardown_func = getattr(module, 'teardown_group', None)
    if teardown_func:
        def wrapped_teardown(framework):
            set_test_context(framework, group_name, "Global Teardown")
            try:
                teardown_func()
            finally:
                clear_test_context()
        group.set_teardown(wrapped_teardown)

    # Testy
    for attr_name in dir(module):
        if attr_name.startswith('test_'):
            test_func = getattr(module, attr_name)
            if callable(test_func):
                def make_wrapped_test(test_func, test_name):
                    def wrapped_test(framework):
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

                wrapped = make_wrapped_test(test_func, attr_name)
                group.add_test(Test(attr_name, wrapped, test_func))

    return group
