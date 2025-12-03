import pytest

from py_micro_hil.tests_framework import TestFramework, TestGroup, Test, Peripheral
from py_micro_hil.assertions import TEST_ASSERT_EQUAL


# ---------------------------------------------------------------------
# Dummy helpers
# ---------------------------------------------------------------------


class FakePeripheralManager:
    def __init__(self):
        self.initialized = False
        self.released = False

    def initialize_all(self):
        self.initialized = True

    def release_all(self):
        self.released = True


class IncompleteManager:
    pass


class FakeLogger:
    def __init__(self):
        self.entries = []
        self.log_file = False
        self.html_file = False
        self.log_entries = []

    def log(self, message, to_console=False, to_log_file=False):
        self.entries.append((message, to_console, to_log_file))


@pytest.fixture
def fake_logger():
    return FakeLogger()


@pytest.fixture
def peripheral_manager():
    return FakePeripheralManager()


@pytest.fixture
def framework(peripheral_manager, fake_logger):
    return TestFramework(peripheral_manager, fake_logger)


# ---------------------------------------------------------------------
# Peripheral ABC
# ---------------------------------------------------------------------


def test_peripheral_is_abstract():
    """Sprawdza, że Peripheral można odziedziczyć i poprawnie zaimplementować."""

    class Impl(Peripheral):
        def initialize(self):
            pass

        def release(self):
            pass

    p = Impl()
    assert isinstance(p, Peripheral)


def test_peripheral_abstract_enforces_methods():
    """Sprawdza, że klasa bez implementacji metod abstrakcyjnych nie może być zainicjalizowana."""
    with pytest.raises(TypeError):

        class BadPeripheral(Peripheral):
            pass

        BadPeripheral()


def test_peripheral_not_implemented_raises():
    """Sprawdza, że domyślne metody Peripheral rzucają NotImplementedError."""

    class Impl(Peripheral):
        def initialize(self):
            raise NotImplementedError

        def release(self):
            raise NotImplementedError

    p = Impl()
    with pytest.raises(NotImplementedError):
        p.initialize()
    with pytest.raises(NotImplementedError):
        p.release()


# ---------------------------------------------------------------------
# Initialization / Cleanup phases
# ---------------------------------------------------------------------


def test_missing_initialize_all_method(fake_logger):
    mgr = IncompleteManager()
    fx = TestFramework(mgr, fake_logger)
    result = fx.run_all_tests()
    assert result == 1
    assert any("missing 'initialize_all'" in msg[0] for msg in fake_logger.entries)


def test_initialize_all_exception(fake_logger):
    class Mgr:
        def initialize_all(self):
            raise RuntimeError("initfail")

    mgr = Mgr()
    fx = TestFramework(mgr, fake_logger)
    result = fx.run_all_tests()
    assert result == 1
    assert any("initfail" in msg[0] for msg in fake_logger.entries)


def test_missing_release_all_method(fake_logger):
    class Mgr:
        def initialize_all(self):
            pass

    mgr = Mgr()
    fx = TestFramework(mgr, fake_logger)
    fx.add_test_group(TestGroup("g"))
    result = fx.run_all_tests()
    assert result == 0
    assert any("RESOURCE CLEANUP" in m[0] for m in fake_logger.entries)
    assert any("missing 'release_all'" in m[0] for m in fake_logger.entries)


def test_cleanup_raises_exception(fake_logger):
    class Mgr:
        def initialize_all(self):
            pass

        def release_all(self):
            raise RuntimeError("boom")

    mgr = Mgr()
    fx = TestFramework(mgr, fake_logger)
    fx.add_test_group(TestGroup("g"))
    result = fx.run_all_tests()
    assert result == 0
    assert any("During peripherals cleanup" in m[0] for m in fake_logger.entries)


def test_run_all_tests_success(peripheral_manager, fake_logger):
    fx = TestFramework(peripheral_manager, fake_logger)
    grp = TestGroup("G")
    grp.add_test(Test("T", lambda fr: None))
    fx.add_test_group(grp)
    result = fx.run_all_tests()
    assert result == 0
    assert peripheral_manager.initialized
    assert peripheral_manager.released
    assert any("TEST SUMMARY" in m[0] for m in fake_logger.entries)


def test_run_all_tests_with_no_groups_logs_warning(peripheral_manager, fake_logger):
    """Sprawdza zachowanie, gdy framework nie ma żadnych grup testowych."""
    fx = TestFramework(peripheral_manager, fake_logger)
    fx.run_all_tests()
    assert any("TEST EXECUTION" in m[0] for m in fake_logger.entries)
    assert "TEST SUMMARY" in fake_logger.entries[-1][0]


def test_report_generation_failure(fake_logger, peripheral_manager, monkeypatch):
    fake_logger.html_file = "file.html"
    fx = TestFramework(peripheral_manager, fake_logger)
    grp = TestGroup("G")
    fx.add_test_group(grp)
    monkeypatch.setattr(
        fx.report_generator, "generate", lambda _: (_ for _ in ()).throw(RuntimeError("repfail"))
    )
    fx.run_all_tests()
    assert any("Report generation failed" in m[0] for m in fake_logger.entries)


# ---------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------


def test_report_test_result_and_summary(framework, fake_logger):
    framework.report_test_result("G", "t1", True)
    framework.report_test_result("G", "t2", False, "err")
    assert framework.total_tests == 2
    assert framework.pass_count == 1
    assert framework.fail_count == 1
    framework.print_summary()
    summary = fake_logger.entries[-1][0]
    assert "Total Tests Run" in summary
    assert "Failed" in summary


def test_report_test_result_with_html(fake_logger, peripheral_manager):
    fake_logger.html_file = "report.html"
    fx = TestFramework(peripheral_manager, fake_logger)
    fx.report_test_result("G", "T", True, "ok")
    fx.report_test_result("G", "T2", False, "oops")
    assert len(fake_logger.log_entries) == 2
    assert fake_logger.log_entries[1]["level"] == "FAIL"


def test_report_test_info(framework, fake_logger):
    framework.report_test_info("G", "T", "informacja")
    assert any("informacja" in e[0] for e in fake_logger.entries)


def test_print_summary_logs_to_file(fake_logger, peripheral_manager):
    fake_logger.log_file = True
    fx = TestFramework(peripheral_manager, fake_logger)
    fx.total_tests = 3
    fx.pass_count = 2
    fx.fail_count = 1
    fx.print_summary()
    assert any("Total Tests Run" in e[0] for e in fake_logger.entries)


def test_print_summary_with_zero_tests(fake_logger, peripheral_manager):
    """Sprawdza poprawne zachowanie, gdy nie wykonano żadnych testów."""
    fx = TestFramework(peripheral_manager, fake_logger)
    fx.print_summary()
    assert any("Total Tests Run" in e[0] for e in fake_logger.entries)


# ---------------------------------------------------------------------
# TestGroup behaviour
# ---------------------------------------------------------------------


def test_testgroup_setup_teardown_and_run(framework, fake_logger):
    order = []

    def setup(fr):
        order.append("setup")

    def teardown(fr):
        order.append("teardown")

    def test_func(fr):
        order.append("test")

    grp = TestGroup("G")
    grp.set_setup(setup)
    grp.set_teardown(teardown)
    grp.add_test(Test("t1", test_func))
    grp.run_tests(framework)
    assert order == ["setup", "test", "teardown"]
    assert any("Finished test group" in e[0] for e in fake_logger.entries)


def test_testgroup_with_no_tests_warns_in_log(framework, fake_logger):
    """Grupa bez testów powinna wyświetlać ostrzeżenie."""
    grp = TestGroup("EmptyGroup")
    grp.run_tests(framework)
    assert any("No tests found" in e[0] for e in fake_logger.entries)


def test_testgroup_setup_exception_logged(framework, fake_logger):
    def setup(fr):
        raise RuntimeError("boom")

    called = {"test": False}

    def test_func(fr):
        called["test"] = True

    grp = TestGroup("G")
    grp.set_setup(setup)
    grp.add_test(Test("t1", test_func))
    grp.run_tests(framework)
    assert any("Setup for group" in e[0] for e in fake_logger.entries)
    assert any("Skipping tests for group" in e[0] for e in fake_logger.entries)
    assert framework.fail_count == 1
    assert framework.total_tests == 1
    assert not called["test"]


def test_testgroup_teardown_exception_logged(framework, fake_logger):
    def teardown(fr):
        raise RuntimeError("boom")

    grp = TestGroup("G")
    grp.set_teardown(teardown)
    grp.run_tests(framework)
    assert any("Teardown for group" in e[0] for e in fake_logger.entries)
    assert framework.fail_count == 1
    assert framework.total_tests == 1
    assert fake_logger.log_entries[-1]["test_name"] == "teardown"


def test_duplicate_group_names(framework):
    """Sprawdza, że dodanie dwóch grup o tej samej nazwie jest dozwolone, ale nie powoduje błędów."""
    g1 = TestGroup("Same")
    g2 = TestGroup("Same")
    framework.add_test_group(g1)
    framework.add_test_group(g2)
    assert len(framework.test_groups) == 2


# ---------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------


def test_test_run_pass_and_fail(framework, fake_logger):
    def ok(fr):
        pass

    def bad(fr):
        raise RuntimeError("xx")

    t1 = Test("ok", ok)
    t2 = Test("bad", bad)
    t1.run(framework, "G")
    t2.run(framework, "G")

    logs = [m[0] for m in fake_logger.entries]
    assert any("[PASS]" in line for line in logs)
    assert any("[FAIL]" in line for line in logs)


def test_single_result_when_using_assertions(framework, fake_logger):
    def test_body(fr):
        TEST_ASSERT_EQUAL(1, 1, {"framework": fr, "group_name": "G", "test_name": "t1"})

    test = Test("t1", test_body)
    group = TestGroup("G")
    group.add_test(test)

    group.run_tests(framework)

    pass_logs = [msg for msg, *_ in fake_logger.entries if "[PASS]" in msg]
    assert len(pass_logs) == 1
    assert framework.total_tests == 1


# ---------------------------------------------------------------------
# Edge: multiple groups, mixed results
# ---------------------------------------------------------------------


def test_multiple_groups(framework, fake_logger):
    g1 = TestGroup("A")
    g2 = TestGroup("B")
    g1.add_test(Test("t1", lambda fr: None))
    g2.add_test(Test("t2", lambda fr: (_ for _ in ()).throw(RuntimeError("err"))))
    framework.add_test_group(g1)
    framework.add_test_group(g2)
    result = framework.run_all_tests()
    assert result == 1
    assert framework.fail_count == 1
