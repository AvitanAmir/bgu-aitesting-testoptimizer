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
                if test_true_outcomes_dictionary[test_name]==1:
                    t_real_outcome = 1
                else:
                    t_real_outcome = 0
                line += '];' + str(t_real_outcome)
            else:
                line += '];0'
            file.write(line)
            file.write('\n')

        file.close()

    def get_updates_priors(self, test, state, tests, test_true_outcomes_dictionary, tests_bugged_components_dictionary, comp_dict):
        new_priors_dictionary = {}
        comp_prob_dict = {}
        union_tests = {}
        union_components = {}
        union_bugged_components = {}
        union_test_true_outcomes = {}

        for t in tests:
            union_tests[t.get_name()] = t
            union_test_true_outcomes[t.get_name()] = 0 if test_true_outcomes_dictionary[t.get_name()] else 1
            for comp in t.get_components():
                union_components[comp.get_name()] = comp

        union_tests[test.get_name()] = test
        union_test_true_outcomes[test.get_name()] = state
        for comp in test.get_components():
            union_components[comp.get_name()] = comp

        for comp in union_components:
            if comp in tests_bugged_components_dictionary:
                union_bugged_components[comp] = comp

        self.write_analyzer_input_file(union_tests.values(), comp_dict.values(), union_test_true_outcomes, union_bugged_components)

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





    def get_analytic_updates_priors(self, test, state, tests, test_true_outcomes_dictionary, tests_bugged_components_dictionary, comp_dict,B):
        new_priors_dictionary = {}
        comp_prob_dict = {}
        union_tests = {}
        union_components = {}
        union_bugged_components = {}
        union_test_true_outcomes = {}

        for t in tests:
            union_tests[t.get_name()] = t
            union_test_true_outcomes[t.get_name()] = 0 if test_true_outcomes_dictionary[t.get_name()] else 1
            for comp in t.get_components():
                union_components[comp.get_name()] = comp

        union_tests[test.get_name()] = test
        union_test_true_outcomes[test.get_name()] = state
        for comp in test.get_components():
            union_components[comp.get_name()] = comp

        for comp in union_components:
            if comp in tests_bugged_components_dictionary:
                union_bugged_components[comp] = comp

        new_comp_prior = 0.0
        fail_prob = 0.0
        for c in test.get_components():
            if state == 0:
                new_comp_prior = test.calculate_component_failure_probability_given_test(c.get_name(),B)
                fail_prob = new_comp_prior
                new_priors_dictionary[c.get_name()] = fail_prob
            else:
                new_comp_prior = test.calculate_component_pass_probability_given_test(c.get_name(),B)
                fail_prob = 1 - new_comp_prior
                fail_prob = new_comp_prior
                new_priors_dictionary[c.get_name()]= fail_prob

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
        self.normilize()

    def normilize(self):

        keys = []
        priors = []
        for key in self._components_dictionary:
            keys.append(key)
            priors.append(self._components_dictionary[key].get_failure_probability())

        priors_norms = operations.normilize(priors)

        for index in range(0, len(priors_norms)):
            self._components_dictionary[keys[index]].set_failure_probability(priors_norms[index])

    def update_components_dictionary(self,post_prob_test_run_dict):
        for c in post_prob_test_run_dict:
            #print(self._components_dictionary[c].get_name(),': ',self._components_dictionary[c].get_failure_probability(),' , ',post_prob_test_run_dict[c] )
            self._components_dictionary[c].set_failure_probability(post_prob_test_run_dict[c])
        self.normilize()

    def calculate_general_entropy(self):
        '''
        calculate the general entropy of all components.
        :return: general entropy
        '''
        # TODO is it the claculation?
        probs = []
        for component in self._components_dictionary.values():
            #probs.append(component.get_success_probability())
            probs.append(component.get_failure_probability())
        return entropy(probs)

    def calculate_test_entropy(self, test, performed_tests, diagnoser_client):
        '''
        calculate a specific test entropy as defined in the test 'calculate_test_entropy' method.
        :param test:
        :return: test entropy
        '''
        return operations.calculate_test_entropy(test, performed_tests, self._test_true_outcomes_dictionary, self._bugged_components_dict,
                                                 diagnoser_client, self._components_dictionary)

    def find_best_tests(self):
        '''
        main algorithm of the optimizer to find the best sub set that will yield the max bug count.
        :return: void
        '''
        fail_found = False
        diagnoser_client = DiagnoserClient()
        tests_buffer = {}
        rounds = min(len(self._tests_dictionary), self._max_tests_amount)

        for key in self._tests_dictionary.keys():
            tests_buffer[key] = self._tests_dictionary[key]

        tests_by_information_gain = []
        tests_IG = []
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

            print('\nRound #: ' + str(round) + ' Selected Test: ' + str(selected_key) + ' outcome: ' + str(self._test_true_outcomes_dictionary[selected_key]))

            # print(selected_key, current_best_test.get_components_failure_probability())

            fail_found |= not self._test_true_outcomes_dictionary[selected_key]

            #TODO: unmark this statement
            t_outcome = 0 if self._test_true_outcomes_dictionary[selected_key] else 1

            #t_outcome = 1

            post_prob_test_run_dict = []

            if fail_found:
                post_prob_test_run_dict =  diagnoser_client.get_updates_priors(current_best_test, t_outcome, tests_by_information_gain, self._test_true_outcomes_dictionary,
                                                    self._bugged_components_dict, self._components_dictionary)
            tests_by_information_gain.append(current_best_test)
            tests_IG.append(selected_key)

            print(' -- General Entropy: ' + str(general_entropy))
            print(' -- Best IG: ' + str(current_best_information_gain))
            print(' -- Till now fail found: '+str(fail_found))
            # print(selected_key, post_prob_test_run_dict)
            if fail_found:
                self.update_components_dictionary(post_prob_test_run_dict)

            tests_buffer.pop(selected_key)
            print(" -- Selected tests till now: " + str(tests_IG))
            general_entropy = self.calculate_general_entropy()

    def analytic_find_best_tests(self,B):
        '''
        main algorithm of the optimizer to find the best sub set that will yield the max bug count.
        :return: void
        '''
        fail_found = False
        debug = 0
        diagnoser_client = DiagnoserClient()
        tests_buffer = {}
        rounds = min(len(self._tests_dictionary), self._max_tests_amount)

        for key in self._tests_dictionary.keys():
            #TODO: Remove
            if len(self._tests_dictionary[key].get_components())>1 and len(self._tests_dictionary[key].get_components())<20:
                tests_buffer[key] = self._tests_dictionary[key]

        tests_by_information_gain = []
        tests_IG = []
        general_entropy = self.calculate_general_entropy()

        for round in range(1, rounds + 1):
            current_best_information_gain = 0
            current_best_test = 0
            selected_key = ''
            for key in tests_buffer.keys():
                test = tests_buffer[key]
                if debug==1:
                    print('Test: ', key,' Ent:' ,test.calculate_test_entropy(B))
                current_information_gain = general_entropy - test.calculate_test_entropy(B)
                if debug == 1:
                    print('Test: ',key,' general_entropy: ',general_entropy,' information_gain: ',current_information_gain)
                if current_information_gain > current_best_information_gain:
                    current_best_information_gain = current_information_gain
                    current_best_test = test
                    selected_key = key


            #Actual run of the selected test with real test state outcome

            print('\nRound #: ' + str(round) + ' Selected Test: ' + str(selected_key) + ' outcome: ' + str(self._test_true_outcomes_dictionary[selected_key]))

            # print(selected_key, current_best_test.get_components_failure_probability())

            fail_found |= not self._test_true_outcomes_dictionary[selected_key]

            #TODO: unmark this statement
            t_outcome = 0 if self._test_true_outcomes_dictionary[selected_key] else 1

            #t_outcome = 1

            post_prob_test_run_dict = []


            if fail_found:
            #   post_prob_test_run_dict =  diagnoser_client.get_updates_priors(current_best_test, t_outcome, tests_by_information_gain, self._test_true_outcomes_dictionary,
            #                                   self._bugged_components_dict, self._components_dictionary)
                post_prob_test_run_dict =  diagnoser_client.get_analytic_updates_priors(current_best_test, t_outcome, tests_by_information_gain, self._test_true_outcomes_dictionary,
                                                self._bugged_components_dict, self._components_dictionary,B)

            tests_by_information_gain.append(current_best_test)
            tests_IG.append(selected_key)

            print(' -- General Entropy: ' + str(general_entropy))
            print(' -- Best IG: ' + str(current_best_information_gain))
            print(' -- Till now fail found: '+str(fail_found))
            # print(selected_key, post_prob_test_run_dict)
            if fail_found:
                self.update_components_dictionary(post_prob_test_run_dict)

            tests_buffer.pop(selected_key)
            print(" -- Selected tests till now: " + str(tests_IG))
            general_entropy = self.calculate_general_entropy()
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

    for index, row in test_outcomes_df.iterrows():
        # print(row['TestName'], row['TestOutcome'])
        test_outcomes_dict[row['TestName']] = row['TestOutcome'] == 1

    for index, row in bugged_components_df.iterrows():
        bugged_components_dict[row['name']] = 1

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
            if str(test)=='nan' or test not in test_outcomes_dict:
                pass
            else:
                test_dict[test] = models.Test(test, test_comp_dict[test])
        # print(test,test_dict[test].get_failure_probability(),operations.calculate_failure_probability(test_dict[test]))

    '''    for test in test_dict:
        if str(test) == 'nan' or test not in test_outcomes_dict or len(test_dict[test].get_components_list())>5:
            pass
        else:
            B=0.5
            print('test: ',test)
            print('FailureProb:',test_dict[test].calculate_test_failure_probability(B))
            print('PassProb:', test_dict[test].calculate_test_pass_probability(B))
            ent = test_dict[test].calculate_test_entropy( B)
            print('Test Entropy: ',ent)
            for c in test_dict[test].get_components():
                is_faulty = 0

                print('-------component: ',c.get_name())
                if c.get_name() in bugged_components_dict:
                    is_faulty = 1
                failure_probability_given_component = test_dict[test].calculate_test_failure_probability_given_component(c.get_name(),is_faulty,B)
                #if failure_probability_given_component == 1:
                #    print('-------failure_probability_given_component: ',test_dict[test].calculate_test_failure_probability_given_component(c.get_name(),is_faulty))
                component_pass_probability_given_test = test_dict[test].calculate_component_failure_probability_given_test(c.get_name(),B)
                #print('-------_____component_pass_probability_given_test: ', component_pass_probability_given_test) '''
    max_tests_amount = 30
    ignore_tests = []
    for round in range(1, max_tests_amount + 1):
        test_tup = operations.get_test_with_max_failure_probability(test_dict, ignore_tests, test_outcomes_dict)
        ignore_tests.append(test_tup[0])
        if test_tup[0] in test_outcomes_dict:
            print('round:',round,' Test:',test_tup[0], test_tup[1], test_outcomes_dict[test_tup[0]])

    B= 0.1
    optimizer = Optimizer(comp_dict, test_outcomes_dict, test_dict,bugged_components_dict,max_tests_amount)
    #optimizer.find_best_tests()
    optimizer.analytic_find_best_tests(B)



    #print('Tests failure probability:')
    #operations.get_tests_failure_probability(test_dict,test_outcomes_dict)

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
