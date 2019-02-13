from scipy.stats import entropy
import itertools
import random
from math import pow,log
import numpy as np

def normilize(arr):
    arr_sum = sum(arr)
    return [float(p) / arr_sum for p in arr]

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

def is_fail_exist(performed_tests, tests_true_outcomes_dictionary):
    for test in performed_tests:
        if not tests_true_outcomes_dictionary[test.get_name()]:
            return True
    return False

def calculate_success_entropy(test, performed_tests, tests_true_outcomes_dictionary,performed_tests_bugged_components_dictionary, diagnoser_client,comp_dict):
    comp_prob = []

    # TODO see if the performed test there is at least one failure.
    if not is_fail_exist(performed_tests, tests_true_outcomes_dictionary):
        for c in comp_dict:
            comp_prob.append(comp_dict[c].get_failure_probability())

    else:
        new_priors_dictionary = diagnoser_client.get_updates_priors(test, 0, performed_tests, tests_true_outcomes_dictionary, performed_tests_bugged_components_dictionary, comp_dict)

        for c in comp_dict:
            if c in new_priors_dictionary:
                comp_prob.append(new_priors_dictionary[c])
            else:
                comp_prob.append(comp_dict[c].get_failure_probability())

    return entropy(list(normilize(comp_prob)))

def get_fail_entropy(test, performed_tests, tests_true_outcomes_dictionary,performed_tests_bugged_components_dictionary, diagnoser_client,comp_dict):

    new_priors_dictionary = diagnoser_client.get_updates_priors(test, 1, performed_tests, tests_true_outcomes_dictionary, performed_tests_bugged_components_dictionary, comp_dict)

    comp_prob =[]
    for c in comp_dict:
        if c in new_priors_dictionary:
            comp_prob.append(new_priors_dictionary[c])
        else:
            comp_prob.append(comp_dict[c].get_failure_probability())

    return entropy(list(normilize(comp_prob)))

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

'''Greedy algorithm'''
def get_tests_for_max_covering(test_dict,max_tests_amount):
    component_count = 0
    test_name = random.choice(test_dict.keys())
    component_list =[]
    test_list = []
    chosen_test = ''
    for round in range(1, max_tests_amount + 1):
        for tst in test_dict:
            if tst not in test_list:
                component_count = len(list(set(component_list).union(set(test_dict[tst].get_components_list()))))
                if component_count> len(list(set(list(set(component_list).union(set(test_dict[test_name].get_components_list())))))):
                    test_name = tst
        test_list.append(test_name)
        component_list.extend(list(set(test_dict[test_name].get_components_list())))
        #complist = list(set(component_list))
        #print(test_list)
        #print("covered components: ",len(complist))
    return test_list


'''Analytic algorithm'''
'''E(t=P)=-cC Sum(log(P(c|t=P))P(c|t=P))'''
def calculate_test_analytic_pass_entropy(test,test_dict,comp_dict,B,Ptf):
    entropy_omega_pass = 0
    test_comp_pass_probs =[]
    for comp in comp_dict:
        #if comp in test_dict[test].get_components_list():
            test_comp_pass_probs.append(calculate_component_pass_probability_given_test(test,comp,test_dict,comp_dict,B,Ptf))
        #else:
        #    test_comp_pass_probs.append(comp_dict[comp].get_success_probability())

    entropy_omega_pass = entropy(list(normilize(test_comp_pass_probs)))

    return entropy_omega_pass

'''E(t=F)=-cC Sum(log(P(c|t=F))P(c|t=F))'''
def calculate_test_analytic_failure_entropy(test,test_dict,comp_dict,B,Ptf):
    entropy_omega_failure = 0
    test_comp_fail_probs = []
    for comp in comp_dict:
        #if comp in test_dict[test].get_components_list():
            test_comp_fail_probs.append(
                calculate_component_failure_probability_given_test(test, comp, test_dict, comp_dict, B, Ptf))
        #else:
        #    test_comp_fail_probs.append(comp_dict[comp].get_failure_probability())

    entropy_omega_failure = entropy(list(normilize(test_comp_fail_probs)))

    return entropy_omega_failure

'''E(Omega| t) = -(P(t=P)*E(t=P) + P(t=F)*E(t=F)).'''
def calculate_test_analytic_entropy(test,test_dict,comp_dict, B):
    print(test_dict[test].get_name())
    Ptf = test_dict[test].calculate_test_failure_probability(B)
    test_dict[test]._Ptf = Ptf
    pEnt = calculate_test_analytic_pass_entropy(test,test_dict,comp_dict,B,Ptf)
    fEnt = calculate_test_analytic_failure_entropy(test,test_dict,comp_dict,B,Ptf)
    #ORG
    #test_entropy =  -1*((1- Ptf)*pEnt+ Ptf*fEnt)
    test_entropy = ((1 - Ptf) * pEnt + Ptf * fEnt)
    print('Ptf: ',Ptf,' pEnt: ',pEnt,' fEnt: ',fEnt,' test_entropy: ',test_entropy)
    return test_entropy

''''P(c|t) = (P(t=p|c) *  P(c))/P(t)'''
def calculate_component_failure_probability_given_test(test,comp,test_dict,comp_dict,B,Ptf):
    test_failure_probability_given_component=test_dict[test].calculate_test_failure_probability_given_component(comp,1,B)*comp_dict[comp].get_failure_probability()
    test_failure_probability=Ptf
    if test_failure_probability==0.0:
        pct = 0
    else:
        pct = (test_failure_probability_given_component/(test_failure_probability))

    #print('Pct:',pct)
    return pct

''''P(c|t) = (P(t=p|c) *  P(c))/P(t)'''
def calculate_component_pass_probability_given_test(test,comp,test_dict,comp_dict,B,Ptf):
    test_pass_probability_given_component = test_dict[test].calculate_test_failure_probability_given_component(comp, 0, B) * (1 - comp_dict[comp].get_failure_probability())
    #test_pass_probability = (1 - self.calculate_test_failure_probability(B))
    test_pass_probability = (1 - Ptf)
    if test_pass_probability == 0.0:
        pct = 0
    else:
        pct = (test_pass_probability_given_component / (test_pass_probability))

    #print('Pct:', pct)
    return pct