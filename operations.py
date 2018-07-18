from scipy.stats import entropy

def get_test_with_max_failure_probability(test_dict,ignore_tests,test_outcomes_dict):
    test_name = ""
    test_failure_probability = 0.0
    for tst in test_dict:
        if tst in ignore_tests or tst not in test_outcomes_dict:
            pass
        else:
            if test_dict[tst].get_failure_probability()>test_failure_probability:
                test_name = tst
                test_failure_probability = test_dict[tst].get_failure_probability()

    return (test_name,test_failure_probability)

def get_tests_failure_probability(test_dict,test_outcomes_dict):
    for tst in test_dict:
        if tst not in test_outcomes_dict:
            pass
        else:
                test_name = tst
                test_failure_probability = test_dict[tst].get_failure_probability()
                print (test_name,test_failure_probability)

def get_tests_count(test_dict):
    return len(test_dict.keys())

def calculate_success_probability(test):
    return test.get_success_probability()

def calculate_failure_probability(test):
    return test.get_failure_probability()

def calculate_success_entropy(test, performed_tests, tests_true_outcomes_dictionary,performed_tests_bugged_components_dictionary, diagnoser_client,comp_dict):

    if len(performed_tests)==0:
        comp_prob = []
        for c in comp_dict:
            comp_prob.append(comp_dict[c].get_failure_probability())

        e = entropy(list(comp_prob))
    else:
        new_priors_dictionary = diagnoser_client.get_updates_priors(test, 0, performed_tests, tests_true_outcomes_dictionary, performed_tests_bugged_components_dictionary)

        comp_prob = []
        for c in comp_dict:
            if c in new_priors_dictionary:
                comp_prob.append(new_priors_dictionary[c])
            else:
                comp_prob.append(comp_dict[c].get_failure_probability())

        e = entropy(list(comp_prob))

    return e

def get_fail_entropy(test, performed_tests, tests_true_outcomes_dictionary,performed_tests_bugged_components_dictionary, diagnoser_client,comp_dict):

    try:
        new_priors_dictionary = diagnoser_client.get_updates_priors(test, 1, performed_tests, tests_true_outcomes_dictionary, performed_tests_bugged_components_dictionary)
    except:
        new_priors_dictionary = diagnoser_client.get_updates_priors(test, 0, performed_tests, tests_true_outcomes_dictionary, performed_tests_bugged_components_dictionary)

    comp_prob =[]
    for c in comp_dict:
        if c in new_priors_dictionary:
            comp_prob.append(new_priors_dictionary[c])
        else:
            comp_prob.append(comp_dict[c].get_failure_probability())


    e = entropy(list(comp_prob))

    return e

def calculate_test_entropy(test, performed_tests, tests_true_outcomes_dictionary,performed_tests_bugged_components_dictionary, diagnoser_client,comp_dict):
    '''
    Given a test, diagnoser client and so far performed test data, calculate to test entropy
    :param test:
    :param performed_tests:
    :param tests_true_outcomes_dictionary:
    :param diagnoser_client:
    :return:
    '''

    success_prob = calculate_success_probability(test)

    success_entropy = calculate_success_entropy(test, performed_tests, tests_true_outcomes_dictionary, performed_tests_bugged_components_dictionary, diagnoser_client,comp_dict)

    failure_prob = calculate_failure_probability(test)

    failure_entropy = get_fail_entropy(test, performed_tests, tests_true_outcomes_dictionary, performed_tests_bugged_components_dictionary, diagnoser_client,comp_dict)

    test_entropy = success_prob * success_entropy + failure_prob * failure_entropy

    return test_entropy

