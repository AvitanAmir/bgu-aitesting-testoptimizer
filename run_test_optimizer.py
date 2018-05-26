import pandas as pd
import numpy as np
import models
import operations

def main():
    component_probabilities_df = pd.read_csv('data/ComponentProbabilities.csv')
    test_components_df = pd.read_csv('data/TestComponents.csv')
    test_outcomes_df = pd.read_csv('data/TestOutcomes.csv')
    comp_dict = {}
    test_comp_dict = {}
    test_comp = []
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
        test_dict[test] = models.Test(test_comp_dict[test])
        #print(test,test_dict[test].get_failure_probability(),operations.calculate_failure_probability(test_dict[test]))

    for index, row in test_outcomes_df.iterrows():
        #print(row['TestName'], row['TestOutcome'])
        if row['TestName'] in test_outcomes_dict.keys():
           pass
        else:
            test_outcomes_dict[row['TestName']] = row['TestOutcome']

    #t = operations.get_test_with_max_failure_probability(test_dict)
    #print(t)

if __name__ == "__main__":
    main()