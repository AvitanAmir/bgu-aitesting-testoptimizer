import pandas as pd
import models
import operations
from scipy.stats import entropy

class DiagnoserClient(object):
    def __init__(self):
        pass

    def write_analyzer_input_file(self, tests, components_array, test_true_outcomes_dictionary):
        '''
        Output to file an input for the diagnoser from the given data.
        :param tests:
        :param components_array:
        :param test_true_outcomes_dictionary:
        :return:
        '''
        components_rev = {}

        index=0

        for component in components_array:
            components_rev[component.get_name()] = index
            index+=1

        file = open('diagnose_input', 'w')

        file.write('[Description]\n')
        file.write('some description\n')
        file.write('[Components names]\n')
        line=''
        for index in range(len(components_array)):
            line+='('+str(index)+',\''+str(components_array[index].get_name())+'\'),'

        line = line[:-1]
        file.write('['+line+']\n')

        #TODO what is this
        file.write('[Bugs]\n')
        file.write('[0]\n')

        file.write('[InitialTests]\n')

        line=''
        for index in range(len(tests)):
            line+='\'T'+str(index)+'\','

        line = line[:-1]
        file.write('['+line+']\n')

        file.write('[TestDetails]\n')
        for index in range(len(tests)):
            test = tests[index]
            line = ''
            line+='\'T'+str(index)+'\';['
            test_components = test.get_components()
            for index2 in range(len(test_components)):
                line += str(components_rev[test_components[index2].get_name()])+','
            line = line[:-1]
            test_name = test.get_name()
            # seems to be missing actual outcomes in the data, default to pass (1)
            if test_name in test_true_outcomes_dictionary:
                line+='];'+('1' if test_true_outcomes_dictionary[test_name] else '0')
            else:
                line+='];1'
            file.write(line+'\n')

        file.close()


class Optimizer(object):
    '''
        Optimizer class responsible of finding best sub group of tests that will yield the most bug count.
    '''

    def __init__(self, components_dictionary,  test_true_outcomes_dictionary, tests_dictionary, max_tests_amount = 5):
        self._test_true_outcomes_dictionary = test_true_outcomes_dictionary
        self._tests_dictionary = tests_dictionary
        self._max_tests_amount = max_tests_amount
        self._components_dictionary = components_dictionary

    def calculate_general_entropy(self):
        '''
        calculate the general entropy of all components.
        :return: general entropy
        '''
        #TODO is it the claculation?
        probs = []
        for component in self._components_dictionary.values():
            probs.append(component.get_success_probability())
        return entropy(probs)

    def calculate_test_entropy(self, test):
        '''
        calculate a specific test entropy as defined in the test 'calculate_test_entropy' method.
        :param test:
        :return: test entropy
        '''
        return operations.calculate_test_entropy(test)

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

        for round in range(1, rounds+1):
            current_best_information_gain = 0
            current_best_test = 0
            selected_key = ''
            for key in tests_buffer.keys():
                test = tests_buffer[key]
                current_information_gain = general_entropy - self.calculate_test_entropy(test)
                if current_information_gain > current_best_information_gain:
                    current_best_information_gain = current_information_gain
                    current_best_test = test
                    selected_key = key

            tests_by_information_gain.append(current_best_test)
            tests_buffer.pop(selected_key)
            # TODO need to "perform" the test and set it result in the next calls to analyzer.

        print(tests_by_information_gain)

        diagnoser_client.write_analyzer_input_file(list(self._tests_dictionary.values()), list(self._components_dictionary.values()), self._test_true_outcomes_dictionary)



def main():
    component_probabilities_df = pd.read_csv('data/ComponentProbabilities.csv')
    test_components_df = pd.read_csv('data/TestComponents.csv')
    test_outcomes_df = pd.read_csv('data/TestOutcomes.csv')
    comp_dict = {}
    test_comp_dict = {}
    test_dict = {}
    test_outcomes_dict = {}

    for index, row in component_probabilities_df.iterrows():
        # print(row['ComponentName'], row['FaultProbability'])
        if row['ComponentName'] in comp_dict.keys():
            pass
        else:
            comp_dict[row['ComponentName']] = models.Component(row['ComponentName'], row['FaultProbability'])


    for index, row in test_components_df.iterrows():
        # print(row['TestName'], row['ComponentName'])
        if row['TestName'] in test_comp_dict.keys():
            test_comp_dict[row['TestName']].append (comp_dict[row['ComponentName']])
        else:
            test_comp_dict[row['TestName']] = []
            test_comp_dict[row['TestName']].append(comp_dict[row['ComponentName']])

    for test in test_comp_dict:
        test_dict[test] = models.Test(test, test_comp_dict[test])
        #print(test,test_dict[test].get_failure_probability(),operations.calculate_failure_probability(test_dict[test]))

    for index, row in test_outcomes_df.iterrows():
        #print(row['TestName'], row['TestOutcome'])
        test_outcomes_dict[row['TestName']] = row['TestOutcome'] == 1

    optimizer = Optimizer(comp_dict, test_outcomes_dict, test_dict)

    optimizer.find_best_tests()

    print('All done')


if __name__ == "__main__":
    main()

