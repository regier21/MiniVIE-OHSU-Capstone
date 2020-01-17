import logging

import numpy as np
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis


class Classifier:
    def __init__(self, training_data=None):
        self.TrainingData = training_data
        self.classifier = None
        pass

    def fit(self):
        """
        Fit data currently stored in self.TrainingData and self.TrainingClass to LDA or QDA model

        """

        if self.TrainingData.num_samples == 0:
            logging.info('No Data')
            self.classifier = None
            return
            # raise ValueError('Training Data or Class array(s) is empty. Did you forget to save training data?')

        f_ = np.array(self.TrainingData.data)
        logging.info(f_)
        y = np.array(self.TrainingData.id)
        logging.info('Training data Numpy arrays')
        logging.info('shape of X: ' + str(f_.shape))
        logging.info('shape of y: ' + str(y.shape))

        # self.classifier = QuadraticDiscriminantAnalysis()
        self.classifier = LinearDiscriminantAnalysis()
        self.classifier.fit(f_, y)

    def predict(self, features):
        """

        Call the classifier prediction method with error checking

        returns class decision and status message

        """
        import logging

        if self.classifier is None or features is None:
            # Classifier is untrained
            status_msg = 'UNTRAINED'
            decision_id = None
            return decision_id, status_msg

        if not features.any():
            # all zero values
            status_msg = 'NO_DATA'
            decision_id = None
            return decision_id, status_msg

        try:
            # run sklearn prediction, returns array, but with one sample in we just want the first value
            prediction = self.classifier.predict(features)
            status_msg = 'RUNNING'
            decision_id = prediction[0]

        except ValueError as e:
            logging.warning('Unable to classify. Error was: ' + str(e))
            status_msg = 'ERROR'
            decision_id = None

        return decision_id, status_msg