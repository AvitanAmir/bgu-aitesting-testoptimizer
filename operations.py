import numpy
import scipy
def get_test_with_max_failure_probability(test_dict):
    test_name=""
    test_failure_probability = 0.0
    for tst in test_dict:
        if test_dict[tst].get_failure_probability()>test_failure_probability:
            test_name = tst
            test_failure_probability = test_dict[tst].get_failure_probability()

    #print(test_name,test_failure_probability)
    return (test_name,test_failure_probability)

def get_tests_count(test_dict):
    return len(test_dict.keys())

def calculate_success_probability(test):
    return test.get_success_probability()

def calculate_failure_probability(test):
    return test.get_failure_probability()

def calculate_success_entropy(test):
    # TODO make call to analyzer
    return test.get_success_entropy()

def get_fail_entropy(test):
    # TODO make call to analyzer
    return test.get_fail_entropy()

def calculate_test_entropy(test):
    return calculate_success_probability(test) * calculate_success_entropy(test) + calculate_failure_probability(test) * get_fail_entropy(test)

