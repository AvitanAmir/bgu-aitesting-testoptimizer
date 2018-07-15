import pandas as pd
import models
import operations
import numpy
import copy
from scipy.stats import entropy
from sfl_diagnoser.Diagnoser.diagnoserUtils import readPlanningFile
from sfl_diagnoser.Diagnoser.Diagnosis_Results import Diagnosis_Results
import sfl_diagnoser.Diagnoser.ExperimentInstance

class DiagnoserClient(object):
    '''
    A client API to perform actions with the diagnoser.
    '''

    def __init__(self):
        pass

    def write_analyzer_input_file(self, tests, components_array, test_true_outcomes_dictionary, bugged_test_dict,
                                  file_name='diagnoser_input'):
        '''
        Output to file an input for the diagnoser from the given data.
        :param tests:
        :param components_array:
        :param test_true_outcomes_dictionary:
        :return:
        '''
        components_rev = {}

        index = 0

        for component in components_array:
            components_rev[component.get_name()] = index
            index += 1

        file = open(file_name, 'w')

        file.write('[Description]\n')
        file.write('some description\n')
        file.write('[Components names]\n')
        line = ''
        bugs = ''
        priors = ''
        for index in range(len(components_array)):
            line += '(' + str(index) + ',\'' + str(components_array[index].get_name()) + '\'),'
            priors += str(components_array[index].get_failure_probability()) + ','
            if str(components_array[index].get_name()) in bugged_test_dict:
                bugs += str(index) + ','

        line = line[:-1]
        file.write('[' + line + ']\n')

        file.write('[Priors]\n')
        priors = priors[:-1]
        file.write('[' + priors + ']\n')

        file.write('[Bugs]\n')
        bugs = bugs[:-1]
        file.write('[' + bugs + ']\n')

        file.write('[InitialTests]\n')

        line = ''
        for index in range(len(tests)):
            line += '\'T' + str(index) + '\','

        line = line[:-1]
        file.write('[' + line + ']\n')

        file.write('[TestDetails]\n')
        for index in range(len(tests)):
            test = tests[index]
            line = ''
            line += 'T' + str(index) + ';['
            test_components = test.get_components()
            for components_index in range(len(test_components)):
                line += str(components_rev[test_components[components_index].get_name()]) + ','
            line = line[:-1]
            test_name = test.get_name()
            # seems to be missing actual outcomes in the data, default to pass (1)
            if test_name in test_true_outcomes_dictionary:
                line += '];' + str(test_true_outcomes_dictionary[test_name])
            else:
                line += '];1'
            file.write(line)
            file.write('\n')

        file.close()

    def get_updates_priors(self, test, state, tests, test_true_outcomes_dictionary, tests_bugged_components_dictionary):
        new_priors_dictionary = {}
        comp_prob_dict = {}
        union_tests = {}
        union_components = {}
        union_bugged_components = {}
        union_test_true_outcomes = {}

        union_tests[test.get_name()] = test
        union_test_true_outcomes[test.get_name()] = state
        for comp in test.get_components():
            union_components[comp.get_name()] = comp

        for t in tests:
            union_tests[t.get_name()] = t
            union_test_true_outcomes[t.get_name()] = 1 if test_true_outcomes_dictionary[t.get_name()] else 0
            for comp in t.get_components():
                union_components[comp.get_name()] = comp

        for comp in union_components:
            if comp in tests_bugged_components_dictionary:
                union_bugged_components[comp] = comp

        self.write_analyzer_input_file(union_tests.values(), union_components.values(), union_test_true_outcomes, union_bugged_components)

        # Use diagestor to get new priors given a state of the current test and previous tests.
        inst = readPlanningFile(r"diagnoser_input")
        inst.diagnose()
        results = Diagnosis_Results(inst.diagnoses, inst.initial_tests, inst.error)
        comp_prob = results.get_components_probabilities()

        file = open("diagnoser_input", "r")
        comp_new_priors = file.readlines()[3]
        comp_new_priors_tup_arr = comp_new_priors[1:-2].replace("),",")),").split("),")
        comp_new_priors_dict = {}
        for tup in comp_new_priors_tup_arr:
            t= tup[1:-1].split(",")
            comp_new_priors_dict[t[1][1:-1]] = int(t[0])

        for p in comp_prob:
            comp_prob_dict[p[0]] = p[1]

        for component in test.get_components():
            if component.get_name() in comp_new_priors_dict:
                comp = comp_new_priors_dict[component.get_name()]
                if comp in comp_prob_dict:
                    new_priors_dictionary[component.get_name()] = comp_prob_dict[comp]

        return new_priors_dictionary


class Optimizer(object):
    '''
        Optimizer class responsible of finding best sub group of tests that will yield the most bug count.
    '''

    def __init__(self, components_dictionary, test_true_outcomes_dictionary, tests_dictionary,bugged_components_dict, max_tests_amount=5):
        self._test_true_outcomes_dictionary = test_true_outcomes_dictionary
        self._tests_dictionary = tests_dictionary
        self._max_tests_amount = max_tests_amount
        self._components_dictionary = components_dictionary
        self._bugged_components_dict = bugged_components_dict

    def update_components_dictionary(self,post_prob_test_run_dict):
        for c in self._components_dictionary:
            if c in post_prob_test_run_dict:
                self._components_dictionary[c].set_failure_probability(post_prob_test_run_dict[c])

    def calculate_general_entropy(self):
        '''
        calculate the general entropy of all components.
        :return: general entropy
        '''
        # TODO is it the claculation?
        probs = []
        for component in self._components_dictionary.values():
            probs.append(component.get_success_probability())
            #probs.append(component.get_failure_probability())
        return entropy(probs)

    def calculate_test_entropy(self, test, performed_tests, diagnoser_client):
        '''
        calculate a specific test entropy as defined in the test 'calculate_test_entropy' method.
        :param test:
        :return: test entropy
        '''

        performed_tests_true_outcomes_dictionary = {}
        performed_tests_bugged_components_dictionary = {}

        for t in performed_tests:
            test_name = t.get_name()
            if test_name in self._test_true_outcomes_dictionary:
                performed_tests_true_outcomes_dictionary[test_name] = self._test_true_outcomes_dictionary[test_name]
            for comp in t.get_components():
                if comp.get_name() in self._bugged_components_dict:
                    performed_tests_bugged_components_dictionary[comp.get_name()] = self._bugged_components_dict[comp.get_name()]

        for comp in test.get_components():
            if comp.get_name() in self._bugged_components_dict:
                performed_tests_bugged_components_dictionary[comp.get_name()] = self._bugged_components_dict[comp.get_name()]

        return operations.calculate_test_entropy(test, performed_tests, performed_tests_true_outcomes_dictionary,performed_tests_bugged_components_dictionary,
                                                 diagnoser_client)

    def find_best_tests(self):
        '''
        main algorithm of the optimizer to find the best sub set that will yield the max bug count.
        :return: void
        '''
        diagnoser_client = DiagnoserClient()
        tests_buffer = {}
        rounds = min(len(self._tests_dictionary), self._max_tests_amount)

        for key in self._tests_dictionary.keys():
            tests_buffer[key] = self._tests_dictionary[key]

        tests_by_information_gain = []

        general_entropy = self.calculate_general_entropy()

        for round in range(1, rounds + 1):
            current_best_information_gain = 0
            current_best_test = 0
            selected_key = ''
            for key in tests_buffer.keys():
                test = tests_buffer[key]
                current_information_gain = general_entropy - self.calculate_test_entropy(test,
                                                                                         tests_by_information_gain,
                                                                                         diagnoser_client)
                #print('Test: ',key,' general_entropy: ',general_entropy,' information_gain: ',current_information_gain)
                if current_information_gain > current_best_information_gain:
                    current_best_information_gain = current_information_gain
                    current_best_test = test
                    selected_key = key


            #Actual run of the selected test with real test state outcome

            print('Round #:', round, ' Test: ', selected_key, ' true outcome: ', self._test_true_outcomes_dictionary[selected_key])

            print(selected_key, current_best_test.get_components_failure_probability())


            # post_prob_test_run_dict =  diagnoser_client.get_updates_priors(tests_buffer[selected_key], -1, {}, self._test_true_outcomes_dictionary,
            #                                     self._bugged_components_dict)
            # print(selected_key, post_prob_test_run_dict)
            # self.update_components_dictionary(post_prob_test_run_dict)

            t_outcome = 1 if self._test_true_outcomes_dictionary[selected_key] else 0

            post_prob_test_run_dict =  diagnoser_client.get_updates_priors(current_best_test, t_outcome, tests_by_information_gain, self._test_true_outcomes_dictionary,
                                                self._bugged_components_dict)
            tests_by_information_gain.append(current_best_test)
            print(selected_key, post_prob_test_run_dict)
            self.update_components_dictionary(post_prob_test_run_dict)

            tests_buffer.pop(selected_key)


        # TODO remove this call, debug for now only.
        #diagnoser_client.write_analyzer_input_file(list(self._tests_dictionary.values()),
        #                                           list(self._components_dictionary.values()),
        #                                           self._test_true_outcomes_dictionary,
        #                                           self._bugged_test_dict)


def main():
    component_probabilities_df = pd.read_csv('data/ComponentProbabilities.csv')
    test_components_df = pd.read_csv('data/TestComponents.csv')
    test_outcomes_df = pd.read_csv('data/TestOutcomes.csv')
    bugged_components_df = pd.read_csv('data/BuggedFiles.csv')
    comp_dict = {}
    test_comp_dict = {}
    test_dict = {}
    test_outcomes_dict = {}
    bugged_components_dict = {}

    for index, row in component_probabilities_df.iterrows():
        if row['ComponentName'] in comp_dict.keys():
            pass
        else:
            #print(index,row['ComponentName'], row['FaultProbability'])
            comp_dict[row['ComponentName']] = models.Component(index,row['ComponentName'], row['FaultProbability'])

    for index, row in test_components_df.iterrows():
        # print(row['TestName'], row['ComponentName'])
        if row['TestName'] in test_comp_dict.keys():
            test_comp_dict[row['TestName']].append(comp_dict[row['ComponentName']])
        else:
            test_comp_dict[row['TestName']] = []
            test_comp_dict[row['TestName']].append(comp_dict[row['ComponentName']])

    for test in test_comp_dict:
            if str(test)=='nan':
                pass
            else:
                test_dict[test] = models.Test(test, test_comp_dict[test])
        # print(test,test_dict[test].get_failure_probability(),operations.calculate_failure_probability(test_dict[test]))

    for index, row in test_outcomes_df.iterrows():
        # print(row['TestName'], row['TestOutcome'])
        test_outcomes_dict[row['TestName']] = row['TestOutcome'] == 1

    for index, row in bugged_components_df.iterrows():
        bugged_components_dict[row['name']] = 1



    '''inst = readPlanningFile(r"diagnoser_input")
    inst.diagnose()
    result = Diagnosis_Results(inst.diagnoses, inst.initial_tests, inst.error)
    result.get_metrics_names()
    result.get_metrics_values()
    ei = sfl_diagnoser.Diagnoser.ExperimentInstance.addTests(inst, inst.hp_next())'''
    optimizer = Optimizer(comp_dict, test_outcomes_dict, test_dict,bugged_components_dict)

    optimizer.find_best_tests()

    print('All done')


if __name__ == "__main__":
    main()





#
#
# def get_updates_priors_old(self, test, state, tests, test_true_outcomes_dictionary, tests_bugged_components_dictionary):
#     new_priors_dictionary = {}
#     comp_prob_dict = {}
#     union_tests = {}
#     union_components = {}
#     union_bugged_components = {}
#     union_test_true_outcomes ={}
#
#     #Test True outcome
#     if state ==-1 and test_true_outcomes_dictionary[test.get_name()]==1:
#         state = 1
#     elif state == -1 and test_true_outcomes_dictionary[test.get_name()]==0:
#         state = 0
#
#     for t in tests:
#         if t.get_name() in union_tests:
#             pass
#         else:
#             union_tests[t.get_name()] = t
#             if t.get_name() in test_true_outcomes_dictionary:
#                 union_test_true_outcomes[t.get_name()] = test_true_outcomes_dictionary[t.get_name()]
#             for comp in t.get_components():
#                 if comp.get_name() in union_components:
#                     pass
#                 else:
#                     union_components[comp.get_name()] = comp
#
#     if test.get_name() in union_components:
#         pass
#     else:
#         union_tests[ test.get_name()] = test
#         if test.get_name() in test_true_outcomes_dictionary:
#             union_test_true_outcomes[test.get_name()] = state
#         for c in test.get_components():
#             if c.get_name() in union_components:
#                 pass
#             else:
#                 union_components[c.get_name()] = c
#
#
#     for comp in union_components:
#         if comp in tests_bugged_components_dictionary:
#             if comp in  union_bugged_components:
#                 pass
#             else:
#                 union_bugged_components[comp] = comp
#
#
#
#     self.write_analyzer_input_file(union_tests.values(), union_components.values(), union_test_true_outcomes,union_bugged_components)
#
#
#     # Use diagestor to get new priors given a state of the current test and previous tests.
#     inst = readPlanningFile(r"diagnoser_input")
#     inst.diagnose()
#     results = Diagnosis_Results(inst.diagnoses, inst.initial_tests, inst.error)
#     comp_prob = results.get_components_probabilities()
#
#     file = open("diagnoser_input", "r")
#     comp_new_priors = file.readlines()[3]
#     comp_new_priors_tup_arr = comp_new_priors[1:-2].replace("),",")),").split("),")
#     comp_new_priors_dict = {}
#     for tup in comp_new_priors_tup_arr:
#         t= tup[1:-1].split(",")
#         comp_new_priors_dict[t[1][1:-1]] = int(t[0])
#
#
#     for p in comp_prob:
#         comp_prob_dict[p[0]]=p[1]
#
#     for component in test.get_components():
#         if component.get_name() in comp_new_priors_dict:
#             i = comp_new_priors_dict[component.get_name()]
#             if i in comp_prob_dict:
#                 new_priors_dictionary[component.get_name()] = comp_prob_dict[i]
#
#     #print(new_priors_dictionary)
#
#     return new_priors_dictionary
