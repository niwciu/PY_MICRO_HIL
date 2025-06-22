import types
import inspect
import os
from unittest.mock import Mock
import pytest
from py_micro_hil.test_framework import TestGroup
from py_micro_hil.test_group_factory import (
    wrap_group_function,
    make_wrapped_test,
    add_tests_from_module,
    create_test_group_from_module
)


def test_wrap_group_function_sets_context(monkeypatch):
    call_log = []

    def mock_set_test_context(framework, group_name, label):
        call_log.append(("set", group_name, label))

    def mock_clear_test_context():
        call_log.append("clear")

    monkeypatch.setattr("py_micro_hil.test_group_factory.set_test_context", mock_set_test_context)
    monkeypatch.setattr("py_micro_hil.test_group_factory.clear_test_context", mock_clear_test_context)

    def dummy_setup():
        call_log.append("setup-ran")

    wrapped = wrap_group_function(dummy_setup, "MyGroup", "Setup")
    wrapped(Mock())

    assert call_log == [
        ("set", "MyGroup", "Setup"),
        "setup-ran",
        "clear"
    ]


def test_make_wrapped_test_calls_without_args(monkeypatch):
    call_log = []

    def mock_set_test_context(framework, group_name, label):
        call_log.append(("set", group_name, label))

    def mock_clear_test_context():
        call_log.append("clear")

    monkeypatch.setattr("py_micro_hil.test_group_factory.set_test_context", mock_set_test_context)
    monkeypatch.setattr("py_micro_hil.test_group_factory.clear_test_context", mock_clear_test_context)

    def dummy_test():
        call_log.append("test-called")

    wrapped = make_wrapped_test(dummy_test, "test_dummy", "GroupX")
    wrapped(Mock())
    assert call_log == [
        ("set", "GroupX", "test_dummy"),
        "test-called",
        "clear"
    ]


def test_make_wrapped_test_calls_with_args(monkeypatch):
    call_log = []

    def mock_set_test_context(framework, group_name, label):
        call_log.append(("set", group_name, label))

    def mock_clear_test_context():
        call_log.append("clear")

    monkeypatch.setattr("py_micro_hil.test_group_factory.set_test_context", mock_set_test_context)
    monkeypatch.setattr("py_micro_hil.test_group_factory.clear_test_context", mock_clear_test_context)

    def dummy_test(framework):
        call_log.append("called-with-fw")

    wrapped = make_wrapped_test(dummy_test, "test_with_arg", "GroupY")
    wrapped(Mock())
    assert call_log == [
        ("set", "GroupY", "test_with_arg"),
        "called-with-fw",
        "clear"
    ]


def test_add_tests_from_module_discovers_functions():
    module = types.SimpleNamespace()
    called = []

    def test_abc():
        called.append("abc")

    module.test_abc = test_abc

    group = TestGroup("example", "/tmp/file")
    add_tests_from_module(group, module, "example")

    assert len(group.tests) == 1
    assert group.tests[0].name == "test_abc"

    # Symuluje uruchomienie testu
    group.tests[0].run(Mock(), "example")
    assert called == ["abc"]


def test_create_test_group_from_module_integration(tmp_path):
    tracker = []

    def setup_group():
        tracker.append("setup")

    def teardown_group():
        tracker.append("teardown")

    def test_example():
        tracker.append("test")

    # Tworzenie tymczasowego modułu z __file__
    test_code = """
tracker = []
def setup_group():
    tracker.append("setup")
def teardown_group():
    tracker.append("teardown")
def test_example():
    tracker.append("test")
"""

    module_path = tmp_path / "fake_module.py"
    module_path.write_text(test_code)

    import importlib.util
    spec = importlib.util.spec_from_file_location("py_micro_hil.fake_module", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    group = create_test_group_from_module(module)
    assert group.name == "fake_module"
    assert group.setup is not None
    assert group.teardown is not None
    assert len(group.tests) == 1
    group.setup(Mock())
    group.tests[0].run(Mock(), group.name)
    group.teardown(Mock())
    assert module.tracker == ["setup", "test", "teardown"]


def test_create_group_without_setup_teardown(tmp_path):
    test_code = """
tracker = []
def test_only():
    tracker.append("ran")
"""
    file = tmp_path / "mod2.py"
    file.write_text(test_code)

    import importlib.util
    spec = importlib.util.spec_from_file_location("py_micro_hil.mod2", file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    group = create_test_group_from_module(mod)
    assert group.setup is None
    assert group.teardown is None
    assert len(group.tests) == 1
    group.tests[0].run(Mock(), group.name)
    assert "ran" in mod.tracker
