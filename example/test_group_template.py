from py_micro_hil.assertions import *
from py_micro_hil.framework_API import *

def setup_group():
    TEST_INFO_MESSAGE("Setting up {test_group_name}")

def teardown_group():
    TEST_INFO_MESSAGE("Tearing down {test_group_name}")

def test_template_test():
    TEST_ASSERT_EQUAL(0,0)
