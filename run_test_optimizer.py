import pandas as pd
import models
import operations
import data_extraction
import os.path
import numpy
import copy
import uuid
import datetime
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

    def update_components_dictionary(self,post_prob_test_run_dict,perfom_normilize=True):
        for c in post_prob_test_run_dict:
            #print(self._components_dictionary[c].get_name(),': ',self._components_dictionary[c].get_failure_probability(),' , ',post_prob_test_run_dict[c] )
            self._components_dictionary[c].set_failure_probability(post_prob_test_run_dict[c])

        if perfom_normilize==True:
            self.normilize()

    def calculate_general_entropy(self,perfom_normilize=True):
        '''
        calculate the general entropy of all components.
        :return: general entropy
        '''
        probs = []
        for component in self._components_dictionary.values():
            #probs.append(component.get_success_probability())
            probs.append(component.get_failure_probability())
        if perfom_normilize==True:
            return entropy(list(operations.normilize(probs)))
        else:
            return entropy(list(probs))

    def calculate_test_base_general_entropy(self,perfom_normilize=True):
        '''
        calculate the general entropy of all components.
        :return: general entropy
        '''
        probs = []
        for test in self._tests_dictionary.values():
            probs.append(test.get_failure_probability())
        if perfom_normilize==True:
            return entropy(list(operations.normilize(probs)))
        else:
            return entropy(list(probs))


    def calculate_test_entropy(self, test, performed_tests, diagnoser_client):
        '''
        calculate a specific test entropy as defined in the test 'calculate_test_entropy' method.
        :param test:
        :return: test entropy
        '''
        return operations.calculate_test_entropy(test, performed_tests, self._test_true_outcomes_dictionary, self._bugged_components_dict,
                                                 diagnoser_client, self._components_dictionary)

    def test_base_calculate_test_entropy(self, test, performed_tests, diagnoser_client):
        '''
        calculate a specific test entropy as defined in the test 'calculate_test_entropy' method.
        :param test:
        :return: test entropy
        '''
        return operations.test_base_calculate_test_entropy(test, performed_tests, self._test_true_outcomes_dictionary,
                                                 self._bugged_components_dict,
                                                 diagnoser_client, self._components_dictionary)

    def find_best_tests(self,report_file_path,test_run,test_run_date):
        '''
        main algorithm of the optimizer to find the best sub set that will yield the max bug count.
        :return: void
        '''
        failed_tests_till_now = 0
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
            round_run_date = datetime.datetime.now()
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
            if selected_key!='':
                print('\nRound #: ' + str(round) + ' Selected Test: ' + str(selected_key) + ' outcome: ' + str(self._test_true_outcomes_dictionary[selected_key]))

                # print(selected_key, current_best_test.get_components_failure_probability())

                fail_found |= not self._test_true_outcomes_dictionary[selected_key]


                t_outcome = 0 if self._test_true_outcomes_dictionary[selected_key] else 1
                if t_outcome == 1:
                    failed_tests_till_now = failed_tests_till_now + 1
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
                general_entropy_org = general_entropy
                general_entropy = self.calculate_general_entropy()
                failed_comp_prob_list = '['
                for failed_comp in self._bugged_components_dict:
                    failed_comp_prob_list = failed_comp_prob_list + failed_comp + ':' + str(self._components_dictionary[failed_comp].get_failure_probability()) + '#'
                failed_comp_prob_list = failed_comp_prob_list+']'
                test_result = str(test_run) + ',' + str(test_run_date) + ',' + str(round_run_date) + ',' + str(round) + ',' + str(
                    t_outcome) + ',' + str(general_entropy_org) + ',' + 'DiagnoserInformationGain' + ',' + str(
                    failed_tests_till_now) + ',' + str(selected_key) + ',' + str(general_entropy)+ ',' + failed_comp_prob_list

                data_extraction.write_test_result_data(report_file_path, test_result, '', False, False)

    def analytic_find_best_tests(self,B,report_file_path,test_run,test_run_date):
        '''
        main algorithm of the optimizer to find the best sub set that will yield the max bug count.
        :return: void
        '''
        failed_tests_till_now =0
        fail_found = False
        debug = 0
        #diagnoser_client = DiagnoserClient()
        tests_buffer = {}

        advance_log = 0
        if advance_log == 1:
            comp_prior_log ={}
            round_updated_comp = {}
            for key in self._components_dictionary.keys():
                prior_log ={}
                prior_log[0] = self._components_dictionary[key].get_failure_probability()
                comp_prior_log[key] = prior_log


        rounds = min(len(self._tests_dictionary), self._max_tests_amount)

        for key in self._tests_dictionary.keys():
            tests_buffer[key] = self._tests_dictionary[key]
        tests_by_information_gain = []
        tests_IG = []
        general_entropy = self.calculate_general_entropy(True)

        for round in range(1, rounds + 1):
            round_run_date = datetime.datetime.now()
            current_best_information_gain = 100000
            current_best_test = 0
            selected_key = ''
            for key in tests_buffer.keys():
                test = tests_buffer[key]
                #calculate_test_entropy = test.calculate_test_entropy(B)
                calculate_test_entropy = operations.calculate_test_analytic_entropy(key,self._tests_dictionary,self._components_dictionary,B)
                test_Ptf = test.calculate_test_failure_probability(B)
                if debug==1:
                    print('Test: ', key,' Ent:' ,calculate_test_entropy)

                current_information_gain = general_entropy - calculate_test_entropy
                #current_information_gain = calculate_test_entropy
                if debug == 1:
                    print('Test: ',key,' general_entropy: ',general_entropy,' information_gain: ',current_information_gain)
                if current_information_gain < current_best_information_gain:
                    current_best_information_gain = current_information_gain
                    current_best_test = test
                    selected_key = key
                    current_best_test_Ptf = test_Ptf


            #Actual run of the selected test with real test state outcome
            if selected_key != '':
                print('\nRound #: ' + str(round) + ' Selected Test: ' + str(selected_key) + ' outcome: ' + str(self._test_true_outcomes_dictionary[selected_key]))

                # print(selected_key, current_best_test.get_components_failure_probability())

                fail_found |= not self._test_true_outcomes_dictionary[selected_key]

                t_outcome = 0 if self._test_true_outcomes_dictionary[selected_key] else 1

                if t_outcome == 1:
                    failed_tests_till_now = failed_tests_till_now + 1
                #post_prob_test_run_dict = []

                #if fail_found:
                #if t_outcome == 1:
                post_prob_test_run_dict =  operations.get_analytic_updates_priors(current_best_test, t_outcome,self._tests_dictionary, self._components_dictionary,B,current_best_test_Ptf)


                if advance_log == 1:
                    round_updated_comp[round] = post_prob_test_run_dict

                tests_by_information_gain.append(current_best_test)
                tests_IG.append(selected_key)


                print(' -- General Entropy: ' + str(general_entropy))
                print(' -- Best IG: ' + str(current_best_information_gain))
                print(' -- Till now fail found: '+str(fail_found))
                #print(' ---failed comp prob: ' + str(self._components_dictionary['org.apache.commons.math3.dfp.Dfp:multiply'].get_failure_probability()))
                # print(selected_key, post_prob_test_run_dict)
                perform_test_norm = 0
                #if fail_found:
                if perform_test_norm ==1:
                    keys = []
                    priors = []
                    for key in post_prob_test_run_dict:
                        keys.append(key)
                        priors.append(post_prob_test_run_dict[key])

                    priors_norms = operations.normilize(priors)
                    for index in range(0, len(priors_norms)):
                        post_prob_test_run_dict[keys[index]]=priors_norms[index]

                self.update_components_dictionary(post_prob_test_run_dict,True)
                if advance_log == 1:
                    for key in self._components_dictionary.keys():
                        prior_log[round] = self._components_dictionary[key].get_failure_probability()
                        comp_prior_log[key][round] = prior_log[round]

                tests_buffer.pop(selected_key)
                print(" -- Selected tests till now: " + str(tests_IG))
                #print(' ---failed comp prob: ' + str(
                #    self._components_dictionary['org.apache.commons.math3.dfp.Dfp:multiply'].get_failure_probability()))
                general_entropy_org = general_entropy
                general_entropy = self.calculate_general_entropy(True)
                failed_comp_prob_list ='['
                for failed_comp in self._bugged_components_dict:
                    failed_comp_prob_list = failed_comp_prob_list +  failed_comp + ':'+ str(self._components_dictionary[failed_comp].get_failure_probability())+'#'
                failed_comp_prob_list = failed_comp_prob_list + ']'
                test_result = str(test_run) + ',' + str(test_run_date) + ',' + str(round_run_date) + ',' + str(round) + ',' + str(
                    t_outcome) + ',' + str(general_entropy_org) + ',' + 'AnalyticInformationGain' + ',' + str(
                    failed_tests_till_now) + ',' + str(selected_key) + ','+ str(general_entropy) + ',' + failed_comp_prob_list

                data_extraction.write_test_result_data(report_file_path, test_result, '', False, debug)

        if advance_log == 1:
            log_file = report_file_path.replace('_result.txt','_comp_log.txt')
            log_file = log_file.replace('generated_test_results', 'result_logs')
            data_extraction.write_advance_log_result_data(log_file,comp_prior_log,1,debug)
            log_file =log_file.replace('_comp_log.txt','_round_comp_log.txt')
            data_extraction.write_advance_log_result_data(log_file, round_updated_comp, 2, debug)

    def AnalyticMaxFailureProbability_find_best_tests(self,B,report_file_path,test_run,test_run_date):
        '''
        main algorithm of the optimizer to find the best sub set that will yield the max bug count.
        :return: void
        '''
        failed_tests_till_now =0
        fail_found = False
        debug = 0
        #diagnoser_client = DiagnoserClient()
        tests_buffer = {}
        rounds = min(len(self._tests_dictionary), self._max_tests_amount)

        ignore_tests = []
        failed_tests_till_now = 0
        for round in range(1, rounds + 1):
            round_run_date = datetime.datetime.now()
            test_tup = operations.get_test_with_max_failure_probability(self._tests_dictionary, ignore_tests,self._test_true_outcomes_dictionary)
            ignore_tests.append(test_tup[0])
            test_Ptf = self._tests_dictionary[test_tup[0]].calculate_test_failure_probability(B)
            if test_tup[0] in self._test_true_outcomes_dictionary:
                print('Round:', round, ' Test:', test_tup[0], test_tup[1], self._test_true_outcomes_dictionary[test_tup[0]])
                t_outcome = 0
                if self._test_true_outcomes_dictionary[test_tup[0]] == 0:
                    failed_tests_till_now = failed_tests_till_now + 1
                    t_outcome = 1
                    fail_found = True
                post_prob_test_run_dict = []
                if fail_found:
                    post_prob_test_run_dict =  operations.get_analytic_updates_priors(self._tests_dictionary[test_tup[0]], t_outcome,self._tests_dictionary, self._components_dictionary,B,test_Ptf)
                    self.update_components_dictionary(post_prob_test_run_dict,True)
                test_result = str(test_run) + ',' + str(test_run_date) + ',' + str(round_run_date) + ',' + str(round) + ',' + str(
                    t_outcome) + ',' + '-' + ',' + 'MaxFailureProbabilityAnalyticGain' + ',' + str(
                    failed_tests_till_now) + ',' + test_tup[0] + ',' + '-' + ',' + '-'
                data_extraction.write_test_result_data(report_file_path, test_result, '', False, False)

    def DiagnoserMaxFailureProbability_find_best_tests(self,report_file_path,test_run,test_run_date):
        '''
        main algorithm of the optimizer to find the best sub set that will yield the max bug count.
        :return: void
        '''
        failed_tests_till_now =0
        fail_found = False
        debug = 0
        diagnoser_client = DiagnoserClient()
        tests_buffer = {}
        rounds = min(len(self._tests_dictionary), self._max_tests_amount)
        ignore_tests = []
        tests_run_till_now = []
        failed_tests_till_now = 0
        for round in range(1, rounds + 1):
            round_run_date = datetime.datetime.now()
            test_tup = operations.get_test_with_max_failure_probability(self._tests_dictionary, ignore_tests,self._test_true_outcomes_dictionary)
            ignore_tests.append(test_tup[0])
            if test_tup[0] in self._test_true_outcomes_dictionary:
                print('Round:', round, ' Test:', test_tup[0], test_tup[1], self._test_true_outcomes_dictionary[test_tup[0]])
                t_outcome = 0
                if self._test_true_outcomes_dictionary[test_tup[0]] == 0:
                    failed_tests_till_now = failed_tests_till_now + 1
                    t_outcome = 1
                    fail_found = True
                post_prob_test_run_dict = []
                if fail_found:
                    post_prob_test_run_dict = diagnoser_client.get_updates_priors(self._tests_dictionary[test_tup[0]], t_outcome,
                                                                                  tests_run_till_now,
                                                                                  self._test_true_outcomes_dictionary,
                                                                                  self._bugged_components_dict,
                                                                                  self._components_dictionary)

                    self.update_components_dictionary(post_prob_test_run_dict,True)
                    tests_run_till_now.append(self._tests_dictionary[test_tup[0]])

                test_result =  str(test_run) + ',' + str(test_run_date) + ',' + str(round_run_date) + ',' + str(round) + ',' + str(
                    t_outcome) + ',' + '-' + ',' + 'MaxFailureProbabilityDiagnoserGain' + ',' + str(
                    failed_tests_till_now) + ',' + test_tup[0] + ',' + '-' + ',' + '-'
                data_extraction.write_test_result_data(report_file_path, test_result, '', False, False)

    def analytic_test_base_find_best_tests(self,B,report_file_path,test_run,test_run_date):
        '''
        main algorithm of the optimizer to find the best sub set that will yield the max bug count.
        :return: void
        '''
        failed_tests_till_now =0
        fail_found = False
        debug = 0
        #diagnoser_client = DiagnoserClient()
        tests_buffer = {}

        advance_log = 0
        if advance_log == 1:
            comp_prior_log ={}
            round_updated_comp = {}
            for key in self._components_dictionary.keys():
                prior_log ={}
                prior_log[0] = self._components_dictionary[key].get_failure_probability()
                comp_prior_log[key] = prior_log


        rounds = min(len(self._tests_dictionary), self._max_tests_amount)

        for key in self._tests_dictionary.keys():
            tests_buffer[key] = self._tests_dictionary[key]
        tests_by_information_gain = []
        tests_IG = []
        general_entropy = self.calculate_test_base_general_entropy(True)

        for round in range(1, rounds + 1):
            round_run_date = datetime.datetime.now()
            current_best_information_gain = 100000
            current_best_test = 0
            selected_key = ''
            for key in tests_buffer.keys():
                test = tests_buffer[key]
                #calculate_test_entropy = test.calculate_test_entropy(B)
                calculate_test_entropy = operations.calculate_test_base_analytic_entropy(key,self._tests_dictionary,self._components_dictionary,B)
                test_Ptf = test.calculate_test_failure_probability(B)
                if debug==1:
                    print('Test: ', key,' Ent:' ,calculate_test_entropy)

                current_information_gain = general_entropy - calculate_test_entropy
                #current_information_gain = calculate_test_entropy
                if debug == 1:
                    print('Test: ',key,' general_entropy: ',general_entropy,' information_gain: ',current_information_gain)
                if current_information_gain < current_best_information_gain:
                    current_best_information_gain = current_information_gain
                    current_best_test = test
                    selected_key = key
                    current_best_test_Ptf = test_Ptf


            #Actual run of the selected test with real test state outcome
            if selected_key != '':
                print('\nRound #: ' + str(round) + ' Selected Test: ' + str(selected_key) + ' outcome: ' + str(self._test_true_outcomes_dictionary[selected_key]))

                # print(selected_key, current_best_test.get_components_failure_probability())

                fail_found |= not self._test_true_outcomes_dictionary[selected_key]

                t_outcome = 0 if self._test_true_outcomes_dictionary[selected_key] else 1

                if t_outcome == 1:
                    failed_tests_till_now = failed_tests_till_now + 1
                #post_prob_test_run_dict = []

                #if fail_found:
                #if t_outcome == 1:
                post_prob_test_run_dict =  operations.get_analytic_updates_priors(current_best_test, t_outcome,self._tests_dictionary, self._components_dictionary,B,current_best_test_Ptf)


                if advance_log == 1:
                    round_updated_comp[round] = post_prob_test_run_dict

                tests_by_information_gain.append(current_best_test)
                tests_IG.append(selected_key)


                print(' -- General Entropy: ' + str(general_entropy))
                print(' -- Best IG: ' + str(current_best_information_gain))
                print(' -- Till now fail found: '+str(fail_found))
                #print(' ---failed comp prob: ' + str(self._components_dictionary['org.apache.commons.math3.dfp.Dfp:multiply'].get_failure_probability()))
                # print(selected_key, post_prob_test_run_dict)
                perform_test_norm = 0
                #if fail_found:
                if perform_test_norm ==1:
                    keys = []
                    priors = []
                    for key in post_prob_test_run_dict:
                        keys.append(key)
                        priors.append(post_prob_test_run_dict[key])

                    priors_norms = operations.normilize(priors)
                    for index in range(0, len(priors_norms)):
                        post_prob_test_run_dict[keys[index]]=priors_norms[index]

                self.update_components_dictionary(post_prob_test_run_dict,True)
                if advance_log == 1:
                    for key in self._components_dictionary.keys():
                        prior_log[round] = self._components_dictionary[key].get_failure_probability()
                        comp_prior_log[key][round] = prior_log[round]

                tests_buffer.pop(selected_key)
                print(" -- Selected tests till now: " + str(tests_IG))
                #print(' ---failed comp prob: ' + str(
                #    self._components_dictionary['org.apache.commons.math3.dfp.Dfp:multiply'].get_failure_probability()))
                general_entropy_org = general_entropy
                general_entropy = self.calculate_test_base_general_entropy(True)
                failed_comp_prob_list ='['
                for failed_comp in self._bugged_components_dict:
                    failed_comp_prob_list = failed_comp_prob_list +  failed_comp + ':'+ str(self._components_dictionary[failed_comp].get_failure_probability())+'#'
                failed_comp_prob_list = failed_comp_prob_list + ']'
                test_result = str(test_run) + ',' + str(test_run_date) + ',' + str(round_run_date) + ',' + str(round) + ',' + str(
                    t_outcome) + ',' + str(general_entropy_org) + ',' + 'TestBaseAnalyticInformationGain' + ',' + str(
                    failed_tests_till_now) + ',' + str(selected_key) + ','+ str(general_entropy) + ',' + failed_comp_prob_list

                data_extraction.write_test_result_data(report_file_path, test_result, '', False, debug)

        if advance_log == 1:
            log_file = report_file_path.replace('_result.txt','_comp_log.txt')
            log_file = log_file.replace('generated_test_results', 'result_logs')
            data_extraction.write_advance_log_result_data(log_file,comp_prior_log,1,debug)
            log_file =log_file.replace('_comp_log.txt','_round_comp_log.txt')
            data_extraction.write_advance_log_result_data(log_file, round_updated_comp, 2, debug)

    def test_base_find_best_tests(self,report_file_path,test_run,test_run_date):

        '''
        main algorithm of the optimizer to find the best sub set that will yield the max bug count.
        :return: void
        '''
        failed_tests_till_now = 0
        fail_found = False
        diagnoser_client = DiagnoserClient()
        tests_buffer = {}
        rounds = min(len(self._tests_dictionary), self._max_tests_amount)

        for key in self._tests_dictionary.keys():
            tests_buffer[key] = self._tests_dictionary[key]

        tests_by_information_gain = []
        tests_IG = []
        general_entropy = self.calculate_test_base_general_entropy()

        for round in range(1, rounds + 1):
            round_run_date = datetime.datetime.now()
            current_best_information_gain = 0
            current_best_test = 0
            selected_key = ''
            for key in tests_buffer.keys():
                test = tests_buffer[key]
                current_information_gain = general_entropy - operations.calculate_test_base_diagnoser_entropy(test,self._tests_dictionary,self._components_dictionary,
                                                                     tests_by_information_gain,self._test_true_outcomes_dictionary,
                                                                     self._bugged_components_dict,
                                                                     diagnoser_client)
                #print('Test: ',key,' general_entropy: ',general_entropy,' information_gain: ',current_information_gain)
                if current_information_gain > current_best_information_gain:
                    current_best_information_gain = current_information_gain
                    current_best_test = test
                    selected_key = key


            #Actual run of the selected test with real test state outcome
            if selected_key!='':
                print('\nRound #: ' + str(round) + ' Selected Test: ' + str(selected_key) + ' outcome: ' + str(self._test_true_outcomes_dictionary[selected_key]))

                # print(selected_key, current_best_test.get_components_failure_probability())

                fail_found |= not self._test_true_outcomes_dictionary[selected_key]


                t_outcome = 0 if self._test_true_outcomes_dictionary[selected_key] else 1
                if t_outcome == 1:
                    failed_tests_till_now = failed_tests_till_now + 1
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
                general_entropy_org = general_entropy
                general_entropy = self.calculate_test_base_general_entropy()
                failed_comp_prob_list = '['
                for failed_comp in self._bugged_components_dict:
                    failed_comp_prob_list = failed_comp_prob_list + failed_comp + ':' + str(self._components_dictionary[failed_comp].get_failure_probability()) + '#'
                failed_comp_prob_list = failed_comp_prob_list+']'
                test_result =  str(test_run) + ',' + str(test_run_date) + ','+str(round_run_date) +',' + str(round) + ',' + str(
                    t_outcome) + ',' + str(general_entropy_org) + ',' + 'TestBaseDiagnoserInformationGain' + ',' + str(
                    failed_tests_till_now) + ',' + str(selected_key) + ',' + str(general_entropy)+ ',' + failed_comp_prob_list

                data_extraction.write_test_result_data(report_file_path, test_result, '', False, False)

def main():
    '''data_extraction.generate_data_set_input_files('D:\ST\Thesis\LATEST\DataSet\Math_21.txt',
                                                  'D:\ST\Thesis\LATEST\DataSet\probs.csv' ,
                                                  'D:\ST\Thesis\LATEST\DataSet\DS7' )
    return
  '''
    #data_extraction.remove_empty_lines('D:/ST/Thesis/LATEST/DataSet/Results/DS2/generated_test_set#3_result.txt','D:/ST/Thesis/LATEST/DataSet/Results/DS2/generated_test_set#3_result.csv')
    #return
    component_probabilities_df = pd.read_csv('data/DS5/ComponentProbabilities.csv')
    test_components_df = pd.read_csv('data/DS5/TestComponents.csv')
    test_outcomes_df = pd.read_csv('data/DS5/TestOutcomes.csv')
    bugged_components_df = pd.read_csv('data/DS5/BuggedFiles.csv')
    comp_dict = {}
    test_comp_dict = {}
    test_dict = {}
    test_outcomes_dict = {}
    bugged_components_dict = {}
    include_faild_comp_prob = True

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
            if  row['ComponentName'] in comp_dict:
                test_comp_dict[row['TestName']].append(comp_dict[row['ComponentName']])
        else:
            test_comp_dict[row['TestName']] = []
            if row['ComponentName'] in comp_dict:
                test_comp_dict[row['TestName']].append(comp_dict[row['ComponentName']])

    for test in test_comp_dict:
            if str(test)=='nan' or test not in test_outcomes_dict:
                pass
            else:
                test_dict[test] = models.Test(test, test_comp_dict[test])
        # print(test,test_dict[test].get_failure_probability(),operations.calculate_failure_probability(test_dict[test]))
    #selection_algorithm =['Coverage','MaxFailureProbability','AnalyticInformationGain','DiagnoserInformationGain','MaxFailureProbabilityAnalyticGain','MaxFailureProbabilityDiagnoserGain']
    selection_algorithm = ['MaxFailureProbability','MaxFailureProbabilityAnalyticGain','MaxFailureProbabilityDiagnoserGain','TestBaseAnalyticInformationGain','TestBaseDiagnoserInformationGain']
    data_folder = "generated_data_sets"
    result_folder ="generated_test_results"
    data_set_count = 5
    data_set_size = 40
    #TODO:Remove comment
    #for i in xrange(0, data_set_count):
    #    data_extraction.generate_test_data_set(test_dict, bugged_components_dict, test_outcomes_dict, data_set_size, 1, i, False,10000)

    #return

    test_result_header = 'test_run_id,test_run_date,round_run_date,round, failed_test_by_definition, base_entropy_apriory, algorithm, failed_till_now, chosen_test,round_entropy'
    if include_faild_comp_prob==True:
        test_result_header = test_result_header +',failed_comp_probability'

    for filename in os.listdir('generated_data_sets'):
        file_to_open = os.path.join(data_folder, filename)
        result_file = os.path.splitext(filename)[0] + '_result.txt'
        test_run = uuid.uuid4()
        test_run_date = datetime.datetime.now()
        file_to_write = os.path.join(result_folder, result_file)
        data_extraction.write_test_result_data(file_to_write, '', test_result_header, True, False)


        for algo_run in selection_algorithm:
            component_probabilities_df = pd.read_csv('data/DS5/ComponentProbabilities.csv')
            test_components_df = pd.read_csv('data/DS5/TestComponents.csv')
            test_outcomes_df = pd.read_csv('data/DS5/TestOutcomes.csv')
            bugged_components_df = pd.read_csv('data/DS5/BuggedFiles.csv')
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
                    # print(index,row['ComponentName'], row['FaultProbability'])
                    comp_dict[row['ComponentName']] = models.Component(index, row['ComponentName'], row['FaultProbability'])

            for index, row in test_components_df.iterrows():
                # print(row['TestName'], row['ComponentName'])
                if row['TestName'] in test_comp_dict.keys():
                    if row['ComponentName'] in comp_dict:
                        test_comp_dict[row['TestName']].append(comp_dict[row['ComponentName']])
                else:
                    test_comp_dict[row['TestName']] = []
                    if row['ComponentName'] in comp_dict:
                        test_comp_dict[row['TestName']].append(comp_dict[row['ComponentName']])

            for test in test_comp_dict:
                if str(test) == 'nan' or test not in test_outcomes_dict:
                    pass
                else:
                    test_dict[test] = models.Test(test, test_comp_dict[test])


            test_run_info = data_extraction.read_test_data_set(file_to_open, False)
            print('algo: ',algo_run ,' data_sets: ',filename)
            bugged_components_dict_filtered = {}
            test_dict_filtered = {}
            test_outcomes_dict_filtered = {}
            comp_dict_filtered = {}
            for b in test_run_info[0]:
                bugged_components_dict_filtered[b] = bugged_components_dict[b]
            for t in test_run_info[1]:
                test_dict_filtered[t] = test_dict[t]
                for c in test_dict[t].get_components_list():
                    comp_dict_filtered[c] = comp_dict[c]
                if t in test_outcomes_dict:
                    if len(list(set(bugged_components_dict_filtered).intersection(set(test_dict_filtered[t].get_components_list()))))>0:
                        test_outcomes_dict_filtered[t] = test_outcomes_dict[t]
                    else:
                        test_outcomes_dict_filtered[t]= True
                else:
                    test_outcomes_dict_filtered[t]=True

            max_tests_amount = 40
            if algo_run=='Coverage':
                failed_tests_till_now=0
                covering_tests = operations.get_tests_for_max_covering(test_dict_filtered, max_tests_amount)
                for round in range(1, len(covering_tests) + 1):
                    round_run_date = datetime.datetime.now()
                    if covering_tests[round - 1] in test_outcomes_dict:
                        print('Round:', round, ' Test:', covering_tests[round - 1], test_outcomes_dict[covering_tests[round - 1]])
                        t_outcome = 0
                        if test_outcomes_dict[covering_tests[round - 1]]==0:
                            failed_tests_till_now=failed_tests_till_now+1
                            t_outcome = 1
                        test_result = str(test_run) + ',' + str(test_run_date) + ','+str(round_run_date) +',' +str(round) + ',' + str(
                            t_outcome) + ',' + '-' + ',' + 'Coverage' + ',' + str(
                            failed_tests_till_now) + ',' + str(covering_tests[round - 1]) + ',' + '-'+ ',' + '-'
                        data_extraction.write_test_result_data(file_to_write, test_result, '', False, False)

            if algo_run=='MaxFailureProbability':
                ignore_tests = []
                failed_tests_till_now = 0
                for round in range(1, max_tests_amount + 1):
                    round_run_date = datetime.datetime.now()
                    test_tup = operations.get_test_with_max_failure_probability(test_dict_filtered, ignore_tests, test_outcomes_dict_filtered)
                    ignore_tests.append(test_tup[0])
                    if test_tup[0] in test_outcomes_dict_filtered:
                        print('Round:', round, ' Test:', test_tup[0], test_tup[1], test_outcomes_dict[test_tup[0]])
                        t_outcome = 0
                        if test_outcomes_dict_filtered[test_tup[0]] == 0:
                            failed_tests_till_now = failed_tests_till_now + 1
                            t_outcome = 1
                        test_result =  str(test_run) + ',' + str(test_run_date) + ','+str(round_run_date) +',' +str(round) + ',' + str(
                            t_outcome) + ',' + '-' + ',' + 'MaxFailureProbability' + ',' + str(
                            failed_tests_till_now) + ',' + test_tup[0] + ',' + '-'+ ',' + '-'
                        data_extraction.write_test_result_data(file_to_write, test_result, '', False, False)

            if algo_run =='DiagnoserInformationGain':
                optimizer = Optimizer(comp_dict_filtered, test_outcomes_dict_filtered, test_dict_filtered, bugged_components_dict_filtered, max_tests_amount)
                optimizer.find_best_tests(file_to_write,test_run,test_run_date)
            if algo_run=='AnalyticInformationGain':
                B = 0.1
                optimizer = Optimizer(comp_dict_filtered, test_outcomes_dict_filtered, test_dict_filtered, bugged_components_dict_filtered, max_tests_amount)
                optimizer.analytic_find_best_tests(B,file_to_write,test_run,test_run_date)
            if algo_run == 'MaxFailureProbabilityAnalyticGain':
                B = 0.1
                optimizer = Optimizer(comp_dict_filtered, test_outcomes_dict_filtered, test_dict_filtered,
                                      bugged_components_dict_filtered, max_tests_amount)

                optimizer.AnalyticMaxFailureProbability_find_best_tests(B, file_to_write, test_run, test_run_date)
            if algo_run =='MaxFailureProbabilityDiagnoserGain':
                optimizer = Optimizer(comp_dict_filtered, test_outcomes_dict_filtered, test_dict_filtered, bugged_components_dict_filtered, max_tests_amount)
                optimizer.DiagnoserMaxFailureProbability_find_best_tests(file_to_write,test_run,test_run_date)

            if algo_run == 'TestBaseAnalyticInformationGain':
                B = 0.1
                optimizer = Optimizer(comp_dict_filtered, test_outcomes_dict_filtered, test_dict_filtered,
                                      bugged_components_dict_filtered, max_tests_amount)
                optimizer.analytic_test_base_find_best_tests(B, file_to_write, test_run, test_run_date)

            if algo_run == 'TestBaseDiagnoserInformationGain':
                optimizer = Optimizer(comp_dict_filtered, test_outcomes_dict_filtered, test_dict_filtered,
                                      bugged_components_dict_filtered, max_tests_amount)
                optimizer.test_base_find_best_tests(file_to_write, test_run, test_run_date)

        dest_file_path = file_to_write.replace('.txt', '.csv')
        data_extraction.remove_empty_lines(file_to_write, dest_file_path)


if __name__ == "__main__":
    main()



