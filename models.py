from scipy.stats import entropy
from math import pow,log
import itertools
import numpy as np
import operations

class Component(object):

    def __init__(self, comp_id,name, failure_prob):
        self._name = name
        self._failure_prob = failure_prob
        self.comp_id = comp_id

    def get_name(self):
        return self._name

    def get_failure_probability(self):
        return self._failure_prob

    def set_failure_probability(self,failure_prob):
        self._failure_prob = failure_prob

    def get_success_probability(self):
        return 1 - self.get_failure_probability()


class Test(object):

    def __init__(self, name, components):
        self._name = name
        self._components = components
        self._Ptf = 0

    def get_name(self):
        return self._name

    def get_components(self):
        return self._components

    def get_components_list(self):
        comp_list = []
        for c in self._components:
            comp_list.append(c.get_name())
        return comp_list

    def get_components_failure_probability(self):
        comp_dict = {}
        for component in self._components:
            comp_dict[component.get_name()] = component.get_failure_probability()
        return comp_dict

    def get_failure_probability(self):
        return 1 - self.get_success_probability()

    def get_success_probability(self):
        prob = 1

        for component in self._components:
            prob *= component.get_success_probability()

        return prob

    def get_success_entropy(self):
        probs = []
        for component in self._components:
            probs.append(component.get_success_probability())

        return entropy(probs)

    def get_fail_entropy(self):
        probs = []
        for component in self._components:
            probs.append(1 - component.get_success_probability())

        return entropy(probs)

    def get_test_Ptf(self):
        return self._Ptf

    ''' Analytics '''


    def calculate_test_failure_probability(self,B):
        probs = []
        i =0
        for component in self._components:
            i+=1
            #TODO: Remove this condition MEMORY ERROR when a lot of components
            #if i<20 and component.get_failure_probability()!=0.0:
            #    probs.append(component.get_failure_probability())
            probs.append(component.get_failure_probability())

        PtF = 0
        Bpower = 0
        prob_prod = 1
        prob_prod_sum = 0
        component_count = len(probs)
        #comp_id_list =range(1, component_count + 1)
        max_k = component_count
        #TODO:Consider max_k change it - Amir M suggestion?
        max_k=5
        for k in xrange(1, max_k+1):
            #TODO: is it pow((-1 * B), k-1) or pow((-1 * B), k)?
            Bpower = pow((-1 * B), k)
            #subsets = list(itertools.combinations(comp_id_list, k))
            #subset_probs = list(itertools.combinations(probs, k))
            prob_prod_sum = 0
            #for j in range(0, len(subset_probs)):
            #    prob_prod_sum += np.prod(np.array(subset_probs[j]))
            prob_prod_sum = reduce(np.add, itertools.imap(lambda subset_prob: np.prod(np.array(subset_prob)),
                                                          itertools.combinations(probs, k)), 0.0)
            PtF += Bpower * prob_prod_sum
            #print(k,PtF)

        PtF = -1 * PtF
        return PtF
    '''    
        for k in range(1,component_count+1):
            Bpower = pow((-1*B),k)
            subsets = list(itertools.combinations(range(1, component_count+1), k))
            prob_prod_sum=0
            for j in range (0,len(subsets)):
                prob_prod = 1
                for i in range (0,k):
                    prob_prod *= probs[subsets[j][i]-1]
                prob_prod_sum+=prob_prod
            PtF += Bpower*prob_prod_sum
        PtF = -1*PtF
    
        #print ('__PtF: ',PtF)
        return PtF
    '''
    def calculate_test_pass_probability(self,B):
        return (1- self.calculate_test_failure_probability(B))

    '''P(t | c)means the probability of t to pass given c is the faulty component. Therefore,
    P(t=F | c) = B if C t else 0.'''
    def calculate_test_failure_probability_given_component(self,comp,is_faulty,B):
        test_failure_probability = 0
        if is_faulty ==1:
            if comp in self.get_components_list():
                #TODO: it isn't B or 1?
                test_failure_probability = B
            else:
                test_failure_probability = 0
        else : #is_faulty ==0
            if comp in self.get_components_list():
                test_failure_probability = 1 - B
            else:
                test_failure_probability = 1
        return test_failure_probability

