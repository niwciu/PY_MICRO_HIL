import pytest
from py_micro_hil import assertions


class MockFramework:
    def __init__(self):
        self.results = []
        self.infos = []

    def report_test_result(self, group, test, passed, message=None):
        self.results.append(
            {
                "group": group,
                "test": test,
                "passed": passed,
                "message": message,
            }
        )

    def report_test_info(self, group, test, message):
        self.infos.append(
            {
                "group": group,
                "test": test,
                "message": message,
            }
        )


@pytest.fixture
def context():
    framework = MockFramework()
    assertions.set_test_context(framework, "GroupA", "Test1")
    yield framework
    assertions.clear_test_context()


# ---------------------------------------------------------------------
# Basic assertions with active context
# ---------------------------------------------------------------------


def test_test_assert_equal_pass(context):
    result = assertions.TEST_ASSERT_EQUAL(5, 5)
    assert result is None
    assert context.results[-1]["passed"] is True


def test_test_assert_equal_fail(context):
    assertions.TEST_ASSERT_EQUAL(5, 7)
    result = context.results[-1]
    assert result["passed"] is False
    assert "Expected = 5, actual = 7" in result["message"]


def test_test_assert_true_pass(context):
    result = assertions.TEST_ASSERT_TRUE(True)
    assert result is None
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
    result = assertions.TEST_INFO_MESSAGE("This is info")
    assert result is None
    info = context.infos[-1]
    assert info["message"] == "This is info"


def test_test_fail_message(context):
    result = assertions.TEST_FAIL_MESSAGE("Custom failure")
    assert result is None
    result_data = context.results[-1]
    assert result_data["passed"] is False
    assert result_data["message"] == "Custom failure"


# ---------------------------------------------------------------------
# Edge cases: exceptions inside assertions
# ---------------------------------------------------------------------


def test_assert_equal_raises_comparison_error(context):
    class Bad:
        def __eq__(self, other):
            raise RuntimeError("boom")

    assertions.TEST_ASSERT_EQUAL(Bad(), Bad())
    result = context.results[-1]
    assert result["passed"] is False
    assert "Comparison error" in result["message"]


def test_assert_in_raises_type_error(context):
    # Collection is not iterable
    assertions.TEST_ASSERT_IN("x", None)
    result = context.results[-1]
    assert result["passed"] is False
    assert "Membership check failed" in result["message"]


# ---------------------------------------------------------------------
# Behavior without framework context
# ---------------------------------------------------------------------


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


# ---------------------------------------------------------------------
# Context management
# ---------------------------------------------------------------------


def test_set_and_clear_context():
    fw = MockFramework()
    assertions.set_test_context(fw, "GroupX", "TestY")
    ctx = assertions._get_context()
    assert ctx["framework"] is fw
    assert ctx["group_name"] == "GroupX"
    assert ctx["test_name"] == "TestY"

    assertions.clear_test_context()
    cleared = assertions._get_context()
    assert cleared["framework"] is None
    assert cleared["group_name"] is None
    assert cleared["test_name"] is None


def test_get_context_from_dict():
    manual = {"framework": "F", "group_name": "G", "test_name": "T"}
    ctx = assertions._get_context(manual)
    assert ctx == manual
