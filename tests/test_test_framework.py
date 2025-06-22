import sys
import pytest
from abc import ABC, abstractmethod

from py_micro_hil.test_framework import TestFramework, TestGroup, Test, Peripheral


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


def test_missing_initialize_all_method(fake_logger):
    mgr = IncompleteManager()
    fx = TestFramework(mgr, fake_logger)
    with pytest.raises(SystemExit) as exp:
        fx.run_all_tests()
    assert exp.value.code == 1
    assert any("missing 'initialize_all'" in msg[0] for msg in fake_logger.entries)


def test_missing_release_all_logs_warning(fake_logger):
    # Create manager with initialize but no release_all
    class Manager2:
        def initialize_all(self): pass
    mgr = Manager2()
    fx = TestFramework(mgr, fake_logger)
    # Add an empty group to avoid early exit on no tests
    fx.add_test_group(TestGroup("g1"))
    # Should not raise and should keep the same manager
    fx.run_all_tests()
    assert fx.peripheral_manager == mgr  # ensure the custom manager is still used
def test_report_test_result_and_summary(framework, fake_logger):
    # Test both pass and fail
    framework.report_test_result('grp', 't1', True)
    framework.report_test_result('grp', 't2', False, 'error')
    assert framework.total_tests == 2
    assert framework.pass_count == 1
    assert framework.fail_count == 1
    # Summary contains PASS and FAIL
    framework.print_summary()
    summary = fake_logger.entries[-1][0]
    assert 'Total Tests Run:     2' in summary
    assert 'Passed:              1' in summary
    assert 'Failed:              1' in summary


def test_report_test_info(framework, fake_logger):
    framework.report_test_info('grp', 't1', 'info message')
    assert any('INFO' in entry[0] and 'info message' in entry[0] for entry in fake_logger.entries)


def test_Test_run_pass_and_fail(framework, fake_logger):
    # Create test funcs
    def ok_test(fr): pass
    def fail_test(fr): raise RuntimeError('fail')
    t_ok = Test('ok', ok_test)
    t_fail = Test('fail', fail_test)
    # Run
    t_ok.run(framework, 'g')
    t_fail.run(framework, 'g')
    # Check results logged
    msgs = [e[0] for e in fake_logger.entries]
    assert any('[PASS] g -> ok' in m for m in msgs)
    assert any('[FAIL] g -> fail: fail' in m for m in msgs)


def test_TestGroup_setup_teardown_and_run(framework, fake_logger):
    calls = []
    def setup(fr): calls.append('setup')
    def teardown(fr): calls.append('teardown')
    def test_fn(fr): calls.append('test')
    grp = TestGroup('grp')
    grp.set_setup(setup)
    grp.set_teardown(teardown)
    grp.add_test(Test('t1', test_fn))
    grp.run_tests(framework)
    # Order: header, setup, test, teardown
    assert calls[0] == 'setup'
    assert calls[1] == 'test'
    assert calls[2] == 'teardown'


def test_run_all_tests_success(peripheral_manager, fake_logger):
    fx = TestFramework(peripheral_manager, fake_logger)
    # Add one passing test group
    grp = TestGroup('g')
    grp.add_test(Test('t', lambda fr: None))
    fx.add_test_group(grp)
    # Should not exit
    fx.run_all_tests()
    assert peripheral_manager.initialized is True
    assert peripheral_manager.released is True


def test_run_all_tests_failure(peripheral_manager, fake_logger):
    fx = TestFramework(peripheral_manager, fake_logger)
    grp = TestGroup('g')
    grp.add_test(Test('t', lambda fr: (_ for _ in ()).throw(RuntimeError('oops'))))
    fx.add_test_group(grp)
    with pytest.raises(SystemExit) as se:
        fx.run_all_tests()
    assert se.value.code == 1
    assert peripheral_manager.initialized is True
    assert peripheral_manager.released is True
