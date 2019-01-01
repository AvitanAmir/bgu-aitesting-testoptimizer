import pandas as pd
import models
import operations
import random
import os.path


def generate_test_data_set(test_dict,bugged_components_dict,test_outcomes_dict,data_set_size,bugged_components_count,data_set_num,debug=False):
    chosen_comp = []
    failed_tests = []
    success_tests = []
    neutral_tests = []
    if len(bugged_components_dict.keys())<bugged_components_count:
        bugged_components_count = len(bugged_components_dict.keys())

    while len(chosen_comp)<bugged_components_count:
        c=random.choice(bugged_components_dict.keys())
        if c not in chosen_comp:
            chosen_comp.append(c)
    if debug==True:
        for i in range(0,len(chosen_comp)):
            print('Component #'+str(i+1)+': ',chosen_comp[i])

    failed_tests_percent = 0.25
    success_tests_percent = 0.25
    failed_tests_count = int(data_set_size*failed_tests_percent)
    success_tests_count = int(data_set_size*success_tests_percent)
    neutral_test_count = data_set_size - failed_tests_count - success_tests_count

    if debug == True:
        print('neutral_test_count: '+str(neutral_test_count),' failed_tests_count: '+str(failed_tests_count),' success_tests_count: '+str(success_tests_count))

    for tst in test_dict:
        if len(list(set(chosen_comp).intersection(set(test_dict[tst].get_components_list()))))>0:
            #if debug == True:
            #    print(tst)
            if test_outcomes_dict[tst]==0:
                failed_tests.append(tst)
            else:
                success_tests.append(tst)
        else:
            neutral_tests.append(tst)
    if debug == True:
        print('failed_tests: ',failed_tests)
        print('success_tests: ',success_tests)
        print('neutral_tests: ',neutral_tests)

    random.shuffle(failed_tests)
    random.shuffle(success_tests)
    random.shuffle(neutral_tests)

    if len(failed_tests)>failed_tests_count:
        selected_failed_tests = failed_tests[0:failed_tests_count]
    else:
        selected_failed_tests = failed_tests
        failed_tests_count = len(failed_tests)

    if len(success_tests) > success_tests_count:
        selected_success_tests = success_tests[0:success_tests_count]
    else:
        selected_success_tests = success_tests
        success_tests_count =len(success_tests)


    neutral_test_count = data_set_size - failed_tests_count - success_tests_count
    selected_neutral_tests = neutral_tests[0:neutral_test_count]

    if debug == True:
        print('selected_neutral_test_count: ' + str(neutral_test_count), ' selected_failed_tests_count: ' + str(failed_tests_count),
              ' selected_success_tests_count: ' + str(success_tests_count))
        print('selected_failed_tests: ', selected_failed_tests)
        print('selected_success_tests: ', selected_success_tests)
        print('selected_neutral_tests: ', selected_neutral_tests)

    data_folder = "generated_data_sets"
    file_to_open = os.path.join(data_folder, 'generated_test_set#'+str(data_set_num)+'.txt')

    with open(file_to_open, 'w') as f:
        f.write("%s\n" % '[failed_components]')
        for item in chosen_comp:
            f.write("%s\n" % item)

        f.write("%s\n" % '[selected_failed_tests]')
        for item in selected_failed_tests:
            f.write("%s\n" % item)

        f.write("%s\n" % '[selected_success_tests]')
        for item in selected_success_tests:
            f.write("%s\n" % item)

        f.write("%s\n" % '[selected_neutral_tests]')
        for item in selected_neutral_tests:
            f.write("%s\n" % item)


    f.close()

def read_test_data_set(file_path,debug=False):
    test_info = []
    with open(file_path, 'r') as f:
        test_info =[l.strip() for l in f.readlines()]
    f.close()
    #print(test_info)
    failed_components_index = test_info.index('[failed_components]')
    selected_failed_tests_index = test_info.index('[selected_failed_tests]')
    selected_success_tests_index = test_info.index('[selected_success_tests]')
    selected_neutral_tests_index = test_info.index('[selected_neutral_tests]')

    failed_components = test_info[failed_components_index+1:selected_failed_tests_index]
    selected_failed_tests = test_info[selected_failed_tests_index+1:selected_success_tests_index]
    selected_success_tests = test_info[selected_success_tests_index+1:selected_neutral_tests_index]
    selected_neutral_tests = test_info[selected_neutral_tests_index + 1:]

    tests_set = list(set().union(selected_failed_tests, selected_success_tests, selected_neutral_tests))
    if debug==True:
        print('File Reader--',file_path)
        print('failed_components: ', failed_components)
        print('selected_failed_tests: ', selected_failed_tests)
        print('selected_success_tests: ', selected_success_tests)
        print('selected_neutral_tests: ', selected_neutral_tests)
        print('tests_set: ', tests_set)

    return (failed_components,tests_set)

