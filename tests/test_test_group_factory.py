import types
import inspect
from unittest.mock import Mock
import pytest

from py_micro_hil.tests_framework import TestGroup
from py_micro_hil.tests_group_factory import (
    wrap_group_function,
    make_wrapped_test,
    add_tests_from_module,
    create_test_group_from_module,
)


# =============================================================================
# WRAPPERS
# =============================================================================


def test_wrap_group_function_sets_context(monkeypatch):
    """Testuje poprawne wywołanie set/clear kontekstu przy setup/teardown grupy."""
    call_log = []

    def mock_set_test_context(framework, group_name, label):
        call_log.append(("set", group_name, label))

    def mock_clear_test_context():
        call_log.append("clear")

    monkeypatch.setattr("py_micro_hil.tests_group_factory.set_test_context", mock_set_test_context)
    monkeypatch.setattr(
        "py_micro_hil.tests_group_factory.clear_test_context", mock_clear_test_context
    )

    def dummy_setup():
        call_log.append("setup-ran")

    wrapped = wrap_group_function(dummy_setup, "MyGroup", "Setup")
    wrapped(Mock())

    assert call_log == [("set", "MyGroup", "Setup"), "setup-ran", "clear"]


def test_wrap_group_function_clears_context_on_exception(monkeypatch):
    """Nawet gdy setup rzuca wyjątek, clear_test_context musi być wywołany."""
    call_log = []

    def mock_set(fr, g, L):
        call_log.append("set")

    def mock_clear():
        call_log.append("clear")

    monkeypatch.setattr("py_micro_hil.tests_group_factory.set_test_context", mock_set)
    monkeypatch.setattr("py_micro_hil.tests_group_factory.clear_test_context", mock_clear)

    def bad_setup():
        raise RuntimeError("boom")

    wrapped = wrap_group_function(bad_setup, "G", "Setup")

    with pytest.raises(RuntimeError):
        wrapped(Mock())

    assert call_log == ["set", "clear"]


def test_make_wrapped_test_calls_without_args(monkeypatch):
    """Test bez parametrów wywoływany bez przekazywania framework."""
    call_log = []

    def mock_set(framework, group_name, label):
        call_log.append(("set", group_name, label))

    def mock_clear_test_context():
        call_log.append("clear")

        def mock_set(fr, g, label):
            call_log.append("set")

    monkeypatch.setattr("py_micro_hil.tests_group_factory.set_test_context", mock_set)
    monkeypatch.setattr(
        "py_micro_hil.tests_group_factory.clear_test_context", mock_clear_test_context
    )

    def dummy_test():
        call_log.append("test-called")

    wrapped = make_wrapped_test(dummy_test, "test_dummy", "GroupX")
    wrapped(Mock())
    assert call_log == [("set", "GroupX", "test_dummy"), "test-called", "clear"]


def test_make_wrapped_test_calls_with_args(monkeypatch):
    """Test z parametrem framework jest wywoływany z argumentem."""
    call_log = []

    def mock_set(framework, group_name, label):
        call_log.append(("set", group_name, label))

    def mock_clear_test_context():
        call_log.append("clear")

    monkeypatch.setattr("py_micro_hil.tests_group_factory.set_test_context", mock_set)
    monkeypatch.setattr(
        "py_micro_hil.tests_group_factory.clear_test_context", mock_clear_test_context
    )

    def dummy_test(framework):
        call_log.append("called-with-fw")

    wrapped = make_wrapped_test(dummy_test, "test_with_arg", "GroupY")
    wrapped(Mock())
    assert call_log == [("set", "GroupY", "test_with_arg"), "called-with-fw", "clear"]


def test_make_wrapped_test_raises_still_clears(monkeypatch):
    """Nawet jeśli test rzuci wyjątek, clear_test_context musi się wykonać."""
    log = []
    monkeypatch.setattr(
        "py_micro_hil.tests_group_factory.set_test_context", lambda f, g, L: log.append("set")
    )
    monkeypatch.setattr(
        "py_micro_hil.tests_group_factory.clear_test_context", lambda: log.append("clear")
    )

    def failing_test():
        raise RuntimeError("boom")

    wrapped = make_wrapped_test(failing_test, "test_fail", "G")
    with pytest.raises(RuntimeError):
        wrapped(Mock())
    assert log == ["set", "clear"]


# =============================================================================
# MODULE PARSING
# =============================================================================


def test_add_tests_from_module_discovers_functions():
    """Funkcje test_* są wykrywane i dodawane do grupy."""
    module = types.SimpleNamespace()
    called = []

    def test_abc():
        called.append("abc")

    module.test_abc = test_abc

    group = TestGroup("example", "/tmp/file")
    add_tests_from_module(group, module, "example")

    assert len(group.tests) == 1
    assert group.tests[0].name == "test_abc"

    # Uruchomienie testu
    group.tests[0].run(Mock(), "example")
    assert called == ["abc"]


def test_add_tests_from_module_ignores_non_callable():
    """Elementy niebędące funkcjami nie są dodawane do grupy."""
    module = types.SimpleNamespace()
    module.test_value = 123
    module.test_lambda = lambda: None  # zostanie dodany

    group = TestGroup("mixed", "f")
    add_tests_from_module(group, module, "mixed")
    assert len(group.tests) == 1
    assert group.tests[0].name == "test_lambda"


# =============================================================================
# GROUP CREATION
# =============================================================================


def test_create_test_group_from_module_integration(tmp_path):
    """Pełna integracja: setup, teardown i test funkcja."""

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
    assert group.test_file.endswith("fake_module.py")

    group.setup(Mock())
    group.tests[0].run(Mock(), group.name)
    group.teardown(Mock())
    assert module.tracker == ["setup", "test", "teardown"]


def test_create_group_without_setup_teardown(tmp_path):
    """Moduł bez setup/teardown – tylko test_*."""
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


def test_create_group_with_no_tests(tmp_path):
    """Moduł nie zawierający żadnych testów zwraca pustą grupę."""
    code = """
def helper(): pass
x = 42
"""
    path = tmp_path / "empty_mod.py"
    path.write_text(code)
    import importlib.util

    spec = importlib.util.spec_from_file_location("empty_mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    group = create_test_group_from_module(mod)
    assert group.tests == []


def test_create_group_with_unknown_source(monkeypatch):
    """Jeśli getsourcefile zwróci None, ustawiany jest (unknown source)."""
    fake_module = types.SimpleNamespace(__name__="dummy.module")

    monkeypatch.setattr(inspect, "getsourcefile", lambda _: None)
    group = create_test_group_from_module(fake_module)

    assert group.test_file == "(unknown source)"
    assert group.name == "module"
    assert isinstance(group, TestGroup)


def test_tests_keep_definition_order(tmp_path):
    """Testy powinny być rejestrowane w kolejności definicji w module."""

    code = """
def test_first():
    pass


def test_second():
    pass


def test_third():
    pass
"""
    path = tmp_path / "ordered_mod.py"
    path.write_text(code)

    import importlib.util

    spec = importlib.util.spec_from_file_location("ordered_mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    group = create_test_group_from_module(mod)

    assert [t.name for t in group.tests] == ["test_first", "test_second", "test_third"]
