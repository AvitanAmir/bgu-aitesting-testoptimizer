def calculate_success_probability(test):
    return test.get_success_probability()

def calculate_failure_probability(test):
    return test.get_failure_probability()

def calculate_success_entropy(test):
    pass

def calculate_failure_entropy(test):
    pass

def calculate_test_entropy(test):
    return calculate_success_probability(test) * calculate_success_entropy(test) + calculate_failure_probability(test) * calculate_failure_entropy(test)

