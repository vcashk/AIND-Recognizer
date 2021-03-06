import math
import statistics
import warnings

import numpy as np
from hmmlearn.hmm import GaussianHMM
from sklearn.model_selection import KFold
from asl_utils import combine_sequences


class ModelSelector(object):
    '''
    base class for model selection (strategy design pattern)
    '''

    def __init__(self, all_word_sequences: dict, all_word_Xlengths: dict, this_word: str,
                 n_constant=3,
                 min_n_components=2, max_n_components=10,
                 random_state=14, verbose=False):
        self.words = all_word_sequences
        self.hwords = all_word_Xlengths
        self.sequences = all_word_sequences[this_word]
        self.X, self.lengths = all_word_Xlengths[this_word]
        self.this_word = this_word
        self.n_constant = n_constant
        self.min_n_components = min_n_components
        self.max_n_components = max_n_components
        self.random_state = random_state
        self.verbose = verbose

    def select(self):
        raise NotImplementedError

    def base_model(self, num_states):
        # with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        # warnings.filterwarnings("ignore", category=RuntimeWarning)
        try:
            hmm_model = GaussianHMM(n_components=num_states, covariance_type="diag", n_iter=1000,
                                    random_state=self.random_state, verbose=False).fit(self.X, self.lengths)
            if self.verbose:
                print("model created for {} with {} states".format(self.this_word, num_states))
            return hmm_model
        except:
            if self.verbose:
                print("failure on {} with {} states".format(self.this_word, num_states))
            return None


class SelectorConstant(ModelSelector):
    """ select the model with value self.n_constant

    """

    def select(self):
        """ select based on n_constant value

        :return: GaussianHMM object
        """
        best_num_components = self.n_constant
        return self.base_model(best_num_components)


class SelectorBIC(ModelSelector):
    """ select the model with the lowest Baysian Information Criterion(BIC) score

    http://www2.imm.dtu.dk/courses/02433/doc/ch6_slides.pdf
    Bayesian information criteria: BIC = -2 * logL + p * logN
    """

    def select(self):
        """ select the best model for self.this_word based on
        BIC score for n between self.min_n_components and self.max_n_components

        :return: GaussianHMM object
        """
        warnings.filterwarnings("ignore", category=DeprecationWarning)

        # TODO implement model selection based on BIC scores
        '''
        like_prop = likelyhood propability
        '''
        like_prop = {}

        for num_components in range(self.min_n_components, self.max_n_components+1, 1):

            n = num_components
            d = len(self.X[0])

            """
            p is free parameters in BIC
            ie. number of probabilities in transition matrix + number of Gaussian variance
            """
            p = np.power(n,2) + 2*d*n -1


            try:
                like_prop[num_components] = -2 * self.base_model(num_components).score(self.X, self.lengths) + p * np.log(len(self.X))
            except:
                continue

        if  like_prop:
            return self.base_model(min(like_prop, key=like_prop.get))
        else:
            return  None

        raise NotImplementedError


class SelectorDIC(ModelSelector):
    ''' select best model based on Discriminative Information Criterion

    Biem, Alain. "A model selection criterion for classification: Application to hmm topology optimization."
    Document Analysis and Recognition, 2003. Proceedings. Seventh International Conference on. IEEE, 2003.
    http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.58.6208&rep=rep1&type=pdf
    DIC = log(P(X(i)) - 1/(M-1)SUM(log(P(X(all but i))
    '''

    def select(self):
        warnings.filterwarnings("ignore", category=DeprecationWarning)

        # TODO implement model selection based on DIC scores
        
        reference_dictionary_anti_propabilities = [{}]
        try:
            reference_dictionary_anti_propabilities = np.load('./reference_dictionary_anti_propabilities.npy')


        except:
            for num_components in range(self.min_n_components, self.max_n_components + 1, 1):
                for word in self.words:
                    str_ = '{}_{}'.format(num_components, word)
                    try:
                        X, lengths = self.hwords[word]
                        reference_dictionary_anti_propabilities[0][str_] = self.base_model(num_components).score(X,lengths)
                    except:
                        reference_dictionary_anti_propabilities[0][str_] = 0
            np.save('./reference_dictionary_anti_propabilities.npy', reference_dictionary_anti_propabilities )




        dic_scores = {}
        for num_components in range(self.min_n_components,self.max_n_components+1,1):
            try:
                like_prop = self.base_model(num_components).score(self.X, self.lengths)
                avg_like_prop = 0
                for word in self.words:
                    if word is not self.this_word:
                        X,lengths = self.hwords[word]
                        try:
                            avg_like_prop += reference_dictionary_anti_propabilities[0]['{}_{}'.format(num_components, word )]
                        except:
                            continue
            except:
                continue


            dic_scores[num_components] = like_prop - ((1 / (len(self.words) - 1)) * avg_like_prop)

        if  dic_scores:
            return self.base_model(max(dic_scores, key=dic_scores.get))
        else:
            return  None


        raise NotImplementedError


class SelectorCV(ModelSelector):
    ''' select best model based on average log Likelihood of cross-validation folds

    '''

    def select(self):
        warnings.filterwarnings("ignore", category=DeprecationWarning)

        # TODO implement model selection using CV

        split_method = KFold(2)
        lp = {}
        for num_components in range(self.min_n_components,self.max_n_components+1,1):
            lp_n_components =[]
            try:
                for cv_train_idx, cv_test_idx in split_method.split(self.sequences):
                    X, lengths = combine_sequences(cv_test_idx, self.sequences)
                    try:
                        lp_n_components.append(self.base_model(num_components).score(X, lengths))
                    except:
                        continue
            except:
                try:
                    lp_n_components.append(self.base_model(3).score(self.X, self.lengths))
                except:
                    continue

            if lp_n_components:
                lp[num_components] = np.sum(lp_n_components) / len(lp_n_components)

        if  lp:
            return self.base_model(max(lp, key=lp.get))
        else:
            return  None
        raise NotImplementedError
