import os
import inspect
from core.test_framework import TestGroup, Test
from core.assertions import set_test_context, clear_test_context

def create_test_group_from_module(module):
    """
    Tworzy obiekt TestGroup na podstawie modułu testowego.

    :param module: Załadowany moduł testowy.
    :return: Obiekt TestGroup z dodanymi testami.
    """
    group_name = module.__name__.split('.')[-1]
    test_file = os.path.abspath(inspect.getsourcefile(module))

    group = TestGroup(group_name, test_file)

    # Ustawienie funkcji setup_group, jeśli istnieje
    setup_func = getattr(module, 'setup_group', None)
    if setup_func:
        def wrapped_setup(framework):
            set_test_context(framework, group_name, "Global Setup")
            try:
                setup_func()
            finally:
                clear_test_context()
        group.set_setup(wrapped_setup)

    # Ustawienie funkcji teardown_group, jeśli istnieje
    teardown_func = getattr(module, 'teardown_group', None)
    if teardown_func:
        def wrapped_teardown(framework):
            set_test_context(framework, group_name, "Global Teardown")
            try:
                teardown_func()
            finally:
                clear_test_context()
        group.set_teardown(wrapped_teardown)

    # Dodanie testów do grupy
    for attr_name in dir(module):
        if attr_name.startswith('test_'):
            test_func = getattr(module, attr_name)
            if callable(test_func):
                def wrapped_test(framework, group_name=group_name, test_name=attr_name, test_func=test_func):
                    set_test_context(framework, group_name, test_name)
                    try:
                        test_func(framework, group_name, test_name)
                    finally:
                        clear_test_context()
                group.add_test(Test(attr_name, wrapped_test, test_func))

    return group
