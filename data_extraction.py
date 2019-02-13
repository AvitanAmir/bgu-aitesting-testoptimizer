import pandas as pd
import models
import operations
import random
import os.path

def generate_data_set_input_files(execution_result_file,component_probabilities_file,target_directory_result):
    test_info = []
    component_probabilities=[]
    components_dict = {}
    test_outcome_dict = {}
    with open(execution_result_file, 'r') as f:
        test_info = [l.strip() for l in f.readlines()]
    f.close()
    # print(test_info)
    with open(component_probabilities_file, 'r') as fp:
        component_probabilities = [l.strip() for l in fp.readlines()]
    fp.close()

    file_to_open = os.path.join(target_directory_result,'ComponentProbabilities.csv')

    with open(file_to_open, 'w+') as f:
        f.write("%s\n" % 'ComponentName,FaultProbability')
        for c in component_probabilities:
            if c.find(':')>-1:
                init_val = c[c.find(':')+1:c.find(',')]
                function_val = '.'+c[c.find(':')+1:c.find(',')]+':'
                replace_val = ':'+init_val+','
                if  c.find(function_val)>-1:
                    f.write("%s\n" % c.replace(replace_val,':<init>,'))
                else:
                    f.write("%s\n" % c)
            else:
                f.write("%s\n" % c)
    f.close()


    components_index = test_info.index('[Components names]')
    bugs_index = test_info.index('[Bugs]')
    priors_index = test_info.index('[Priors]')
    initial_test_index = test_info.index('[InitialTests]')
    tests_index = test_info.index('[TestDetails]')

    components_list = test_info[components_index + 1:priors_index]
    bugs_list = test_info[bugs_index + 1:initial_test_index]
    test_list = test_info[tests_index + 1:]

    components_arr = components_list[0][1:-1].split('),')
    bugged_components_arr = bugs_list[0][1:-1].split(',')

    for c in components_arr:
        comp = c.replace(')','').strip()[1:-1].split(',')
        components_dict[int(comp[0])] = comp[1].strip()[1:]

    file_to_open = os.path.join(target_directory_result, 'BuggedFiles.csv')

    with open(file_to_open, 'w+') as f:
        f.write("%s\n" % 'fileID,name')
        for bugged_comp in bugged_components_arr:
            c = bugged_comp+','+components_dict[int(bugged_comp)]
            f.write("%s\n" % c)
    f.close()

    file_to_open = os.path.join(target_directory_result, 'TestComponents.csv')
    with open(file_to_open, 'w+') as f:
        f.write("%s\n" % 'TestName,ComponentName')

        for t in test_list:
            test_components_info = t.split(';')
            test_name = test_components_info[0]
            test_components = test_components_info[1][1:-1].split(',')
            test_outcome = test_components_info[2]

            for c in test_components:
                test_comp = test_name+','+components_dict[int(c)]
                f.write("%s\n" % test_comp)
                test_outcome_dict[test_name] = int(test_outcome)
        #print(test_name,test_components,test_outcome)
    f.close()

    file_to_open = os.path.join(target_directory_result, 'TestOutcomes.csv')

    with open(file_to_open, 'w+') as f:
        f.write("%s\n" % 'TestName,TestOutcomeName,TestOutcome')
        for t in test_outcome_dict:
            if test_outcome_dict[t]==1:
                outcome = t+',failure,0'
                f.write("%s\n" % outcome)
            else:
                outcome = t + ',pass,1'
                f.write("%s\n" % outcome)

    f.close()
    #print(components_list)
    #print(bugs_list)
    #print(test_list)


def generate_test_data_set(test_dict,bugged_components_dict,test_outcomes_dict,data_set_size,bugged_components_count,data_set_num,debug=False,max_test_components=10000):
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
        if len(list(set(chosen_comp).intersection(set(test_dict[tst].get_components_list()))))>0 and len(test_dict[tst].get_components_list())<max_test_components:
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

def write_test_result_data(file_path,test_result,test_result_header,init_required,debug=False):
    if init_required==True:
        with open(file_path, 'w') as f:
            f.write(test_result_header + os.linesep)
        f.close()
    else:
        with open(file_path, 'a') as f:
            f.write(test_result + os.linesep)
        f.close()