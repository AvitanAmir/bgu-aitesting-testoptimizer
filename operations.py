import numpy
import scipy
from scipy.stats import entropy

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

def calculate_success_entropy(test, performed_tests, tests_true_outcomes_dictionary,performed_tests_bugged_components_dictionary, diagnoser_client):

    new_priors_dictionary = diagnoser_client.get_updates_priors(test, 1, performed_tests, tests_true_outcomes_dictionary,performed_tests_bugged_components_dictionary)

    return entropy(list(new_priors_dictionary.values()))

def get_fail_entropy(test, performed_tests, tests_true_outcomes_dictionary,performed_tests_bugged_components_dictionary, diagnoser_client):

    new_priors_dictionary = diagnoser_client.get_updates_priors(test, 0, performed_tests, tests_true_outcomes_dictionary,performed_tests_bugged_components_dictionary)

    return entropy(list(new_priors_dictionary.values()))

def calculate_test_entropy(test, performed_tests, tests_true_outcomes_dictionary,performed_tests_bugged_components_dictionary, diagnoser_client):
    '''
    Given a test, diagnoser client and so far performed test data, calculate to test entropy
    :param test:
    :param performed_tests:
    :param tests_true_outcomes_dictionary:
    :param diagnoser_client:
    :return:
    '''
    return calculate_success_probability(test) * calculate_success_entropy(test, performed_tests, tests_true_outcomes_dictionary,performed_tests_bugged_components_dictionary, diagnoser_client) + calculate_failure_probability(test) * get_fail_entropy(test, performed_tests, tests_true_outcomes_dictionary,performed_tests_bugged_components_dictionary,diagnoser_client)

