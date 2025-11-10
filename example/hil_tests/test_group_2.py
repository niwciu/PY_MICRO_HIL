from py_micro_hil.assertions import *

def setup_group():
    TEST_INFO_MESSAGE("Setting up Group 2")

def teardown_group():
    TEST_INFO_MESSAGE("Tearing down Group 2")

def test_sample_1():
    # TEST_INFO_MESSAGE("Running Sample Test 1")
    TEST_ASSERT_EQUAL(2,3)

def test_sample_2():
    # TEST_INFO_MESSAGE("Running Sample Test 2")
    TEST_ASSERT_EQUAL ("abc".upper(), "ABC")

def test_sample_3():
    # TEST_INFO_MESSAGE("Running Sample Test 3")
    TEST_ASSERT_EQUAL(type(123), int)
