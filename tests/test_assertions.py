import pytest
from py_micro_hil import assertions


class MockFramework:
    def __init__(self):
        self.results = []
        self.infos = []

    def report_test_result(self, group, test, passed, message=None):
        self.results.append({
            "group": group,
            "test": test,
            "passed": passed,
            "message": message,
        })

    def report_test_info(self, group, test, message):
        self.infos.append({
            "group": group,
            "test": test,
            "message": message,
        })


@pytest.fixture
def context():
    framework = MockFramework()
    assertions.set_test_context(framework, "GroupA", "Test1")
    yield framework
    assertions.clear_test_context()


def test_test_assert_equal_pass(context):
    assertions.TEST_ASSERT_EQUAL(5, 5)
    assert context.results[-1]["passed"] is True


def test_test_assert_equal_fail(context):
    assertions.TEST_ASSERT_EQUAL(5, 7)
    result = context.results[-1]
    assert result["passed"] is False
    assert "Expected = 5, actual = 7" in result["message"]


def test_test_assert_true_pass(context):
    assertions.TEST_ASSERT_TRUE(True)
    assert context.results[-1]["passed"] is True


def test_test_assert_true_fail(context):
    assertions.TEST_ASSERT_TRUE(False)
    result = context.results[-1]
    assert result["passed"] is False
    assert "condition is not true" in result["message"]


def test_test_assert_in_pass(context):
    assertions.TEST_ASSERT_IN(2, [1, 2, 3])
    assert context.results[-1]["passed"] is True


def test_test_assert_in_fail(context):
    assertions.TEST_ASSERT_IN(99, [1, 2, 3])
    result = context.results[-1]
    assert result["passed"] is False
    assert "99 not in [1, 2, 3]" in result["message"]


def test_test_info_message(context):
    assertions.TEST_INFO_MESSAGE("This is info")
    info = context.infos[-1]
    assert info["message"] == "This is info"


def test_test_fail_message(context):
    assertions.TEST_FAIL_MESSAGE("Custom failure")
    result = context.results[-1]
    assert result["passed"] is False
    assert result["message"] == "Custom failure"


def test_assert_equal_without_context():
    result = assertions.TEST_ASSERT_EQUAL(1, 2, context={})
    assert result == ("TEST_ASSERT_EQUAL", 2, 1)


def test_assert_true_without_context():
    result = assertions.TEST_ASSERT_TRUE(False, context={})
    assert result == ("TEST_ASSERT_TRUE", False)


def test_assert_in_without_context():
    result = assertions.TEST_ASSERT_IN("x", "abc", context={})
    assert result == ("TEST_ASSERT_IN", "x", "abc")


def test_info_message_without_context():
    result = assertions.TEST_INFO_MESSAGE("no ctx", context={})
    assert result == ("TEST_INFO_MESSAGE", "no ctx")


def test_fail_message_without_context():
    result = assertions.TEST_FAIL_MESSAGE("fail ctx", context={})
    assert result == ("TEST_FAIL_MESSAGE", "fail ctx")
