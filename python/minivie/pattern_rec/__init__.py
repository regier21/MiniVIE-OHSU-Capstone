# -*- coding: utf-8 -*-
import os
import os.path
from shutil import copyfile
import h5py
import datetime as dt
import time
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
import csv
import logging
import threading
import numpy as np
from utilities.user_config import get_user_config_var


class FeatureExtract(object):
    """
    Class for setting feature extract parameters and calling the feature extract process

    @author: R. Armiger

    Input:
     data buffer to compute features
     data_buffer = numpy.zeros((numSamples, numChannels))
     E.g. numpy.zeros((50, 8))

    Optional:
    Thresholds for computing zero crossing and slope sign change features

    Output: feature vector should be [1,nChan*nFeat]
    data ordering is as follows
    [ch1f1, ch1f2, ch1f3, ch1f4, ch2f1, ch2f2, ch2f3, ch2f4, ... chNf4]

    Revisions;
        17NOV2016 Armiger: Created

    """
    def __init__(self):
        self.input_source = 0
        self.normalized_orientation = None
        self.attached_features = []

    def get_features(self, data_input):
        """
        perform feature extraction

        this method supports numpy ndarray types in which features are computed directly and SignalSource objects in
        which the source's get data method is called, then features are extracted

        """
        self.input_source = 0
        if data_input is None:
            # Can't get features
            return None, None, None, None
        elif isinstance(data_input, np.ndarray):
            # Extract features from the data provided
            f = self.feature_extract(data_input)
            imu = None
            rot_mat = None
        else:
            # input is a data source so call it's get_data method

            # Get features from emg data
            data = np.concatenate([s.get_data() for s in data_input], axis=1)
            f = self.feature_extract(data * 0.01)

            imu = np.array([])
            for s in data_input:
                if hasattr(s, 'get_imu'):
                    result = s.get_imu()
                    imu = np.append(imu, result['quat'])
                    imu = np.append(imu, result['accel'])
                    imu = np.append(imu, result['gyro'])
                    # add imu to features
                    # f = np.append(f, imu)
                else:
                    imu = float('nan')

            rot_mat = []
            for s in data_input:
                if hasattr(s, 'get_rotationMatrix'):
                    result = s.get_rotationMatrix()
                    rot_mat.append(result)
                else:
                    rot_mat = None

        feature_list = f.tolist()

        # format the data in a way that sklearn wants it
        f = np.squeeze(f)
        feature_learn = f.reshape(1, -1)

        return feature_list, feature_learn, imu, rot_mat

    def normalize_orientation(self, orientation):
        self.normalized_orientation = orientation

    def attach_feature(self, instance):

        # attaches feature class instance to attached_features list
        if instance in self.attached_features:
            return self.attached_features
        else:
            return self.attached_features.append(instance)

    def get_featurenames(self):
        # return an list with the names of all features being used
        names = []
        for instance in self.attached_features:
            featurename = instance.get_name()
            # if name is a list, append each element individually
            if type(featurename) is list:
                for i in featurename:
                    names.append(i)
            else:
                names.append(featurename)
        return names

    def clear_features(self):
        del self.attached_features[:]

    def feature_extract(self, y):
        """
        Created on Mon Jan 25 16:25:14 2016
        Updated on Sat Apr 15 12:48:00 2018

        Perform feature extraction, vectorized

        @author: R. Armiger
        # compute features
        #
        # Input:
        # data buffer to compute features
        # y = numpy.zeros((numSamples, numChannels))
        # E.g. numpy.zeros((50, 8))
        #
        # Optional:
        # Thresholds for computing zero crossing and slope sign change features
        #
        # Output: feature vector should be [1,nChan*nFeat]
        # data ordering is as follows
        # [ch1f1, ch1f2, ch1f3, ch1f4, ch2f1, ch2f2, ch2f3, ch2f4, ... chNf4]
        """

        # normalize features
        if self.normalized_orientation is not None:
            # normalize incoming data according to myo
            y = np.roll(y, self.normalized_orientation[self.input_source])

        # update input source (ex. myo)
        self.input_source += 1

        features_array = []

        # loops through instances and extracts features
        for feature in self.attached_features:
            new_feature = feature.extract_features(y)
            features_array.append(new_feature)

        if len(features_array) > 0:
            vstack_features_array = np.vstack(features_array)

            # determines total number of elements in array
            size = 1
            for dim in np.shape(vstack_features_array):
                size *= dim

            return vstack_features_array.T.reshape(1, size)
        else:
            return None


def test_feature_extract():
    # Offline test code
    # test with: python3 -c "from pattern_rec import *; test_feature_extract()"
    import matplotlib.pyplot as plt
    import math
    import timeit
    from pattern_rec import features

    print('Testing Feature extraction')
    print([cls.__name__ for cls in features.EMGFeatures.__subclasses__()])

    sample_rate = 200
    window_slide_s = .2
    window_slide_samples = math.floor(sample_rate * window_slide_s)
    slides_per_window = 10
    num_samples = math.floor(window_slide_samples * slides_per_window)
    num_channels = 8
    emg_buffer = np.zeros((num_samples, num_channels))
    t = np.linspace(0, window_slide_s * slides_per_window, num=num_samples)

    # add various sine wave shapes
    for i in range(num_channels):
        amplitude = i+1
        frequency = 10*(i+1)
        phase = i
        offset = 0
        emg_buffer[:, i] = amplitude * np.sin(2 * math.pi * frequency * (t + phase)) + offset
    incremental_buffer = emg_buffer[:(2*window_slide_samples)]

    fe = FeatureExtract()

    for cls in features.EMGFeatures.__subclasses__():
        fe = FeatureExtract()
        feature = cls()
        fe.attach_feature(feature)
        py_time = timeit.timeit(lambda: fe.feature_extract(emg_buffer), number=1000)

        print('*************')
        print(f'Feature Class: {cls.__name__}  Feature Name: {feature.get_name()}  Time to complete: {py_time:.5f})')
        print(fe.feature_extract(emg_buffer))

        try:
            fe = FeatureExtract()
            feature = cls(incremental=True, window_size=num_samples, window_slide=window_slide_samples, channels=num_channels)
            fe.attach_feature(feature)
            py_time = timeit.timeit(lambda: fe.feature_extract(incremental_buffer), number=1000)

            print('*************')
            print(f'Feature Class: {cls.__name__}Inc  Feature Name: {feature.get_name()}  Time to complete: {py_time:.5f})')
            feature.inc_feature.clear()
            for i in range(slides_per_window):
                feature_val = fe.feature_extract(emg_buffer[-((i + 1) * window_slide_samples):])
            print(feature_val)

        except TypeError:
            pass

    # separate the signals for visual reference  and save plot
    for i in range(num_channels):
        offset = i*num_channels
        emg_buffer[:, i] += offset

    # for signal in
    plt.plot(t, emg_buffer)
    plt.savefig('emg_profile.png')


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


class TrainingData:
    """Python Class for managing machine learning and Myo training operations."""
    def __init__(self):
        self.filename = 'TRAINING_DATA'
        self.file_ext = '.hdf5'

        # # Store class names
        # self.motion_names = 'No Movement'
        # TODO: Eliminate separate list for motion names
        # Names of potentially trained classes
        self.motion_names = (
            'No Movement',
            'Shoulder Flexion', 'Shoulder Extension',
            'Shoulder Adduction', 'Shoulder Abduction',
            'Humeral Internal Rotation', 'Humeral External Rotation',
            'Elbow Flexion', 'Elbow Extension',
            'Wrist Rotate In', 'Wrist Rotate Out',
            'Wrist Adduction', 'Wrist Abduction',
            'Wrist Flex In', 'Wrist Extend Out',
            'Hand Open',
            'Spherical Grasp',
            'Tip Grasp',
            'Three Finger Pinch Grasp',
            'Lateral Grasp',
            'Cylindrical Grasp',
            'Power Grasp',
            'Point Grasp',
            'Index',
            'Middle',
            'Ring',
            'Little',
            'Thumb',
            'Ring-Middle',
            'The Bird',
            'Hang Loose',
            'Thumbs Up',
            'Peace',
        )

        # Create lock to control write access to training data
        self.__lock = threading.Lock()

        self.num_channels = 0
        # TODO: For now this was missing a split on comma.  Future should get features based on what is enabled
        # self.features = get_user_config_var("features", "Mav,Curve_Len,Zc,Ssc").split()
        self.features = get_user_config_var("features", "Mav,Curve_Len,Zc,Ssc").split(',')

        self.data = []  # List of all feature extracted samples
        self.id = []  # List of class indices that each sample belongs to
        self.name = []  # Name of each class
        self.time_stamp = []
        self.imu = []
        self.num_samples = 0

        self.reset()

    def reset(self):
        # Clear all data and reset the data store

        with self.__lock:
            self.data = []  # List of all feature extracted samples
            self.id = []  # List of class indices that each sample belongs to
            self.imu = []  # IMU data as applicable to data source
            self.name = []  # Name of each class
            self.time_stamp = []
            self.num_samples = 0

    def clear(self, motion_id):
        # Remove the class data for the matching index
        # Example:
        #     self.clear(0)
        #
        # Note to clear all data use the reset() method
        indices = [i for i, x in enumerate(self.id) if x == motion_id]

        with self.__lock:
            for rev in indices[::-1]:
                del(self.time_stamp[rev])
                del(self.name[rev])
                del(self.id[rev])
                del(self.imu[rev])
                del(self.data[rev])
                self.num_samples -= 1

        if self.num_samples == 0:
            self.reset()

    def add_class(self, new_class):
        if new_class not in self.motion_names:
            self.motion_names = tuple(list(self.motion_names) + [new_class])
            return True
        else:
            logging.info('Error, "' + new_class + '" already contained in class list.')
            return False
        
    def add_data(self, data_, id_, name_, imu_=-1):
        # New Data marked with:
        # time_stamp, name, id, data
        # optionally add IMU data
        with self.__lock:
            self.time_stamp.append(time.time())
            self.name.append(name_)
            self.id.append(id_)
            self.data.append(data_)
            self.imu.append(imu_)
            self.num_samples += 1

    def get_totals(self, motion_id=None):
        # Return a list of the total sample counts for each class
        # Example:
        #     a.get_totals(10)
        #     a.get_totals()
        num_motions = len(self.motion_names)

        if motion_id is None:
            total = [0] * num_motions
            for c_ in range(num_motions):
                total[c_] = self.id.count(c_)
                logging.debug('{} [{}]'.format(self.motion_names[c_],total[c_]))
        else:
            total = self.id.count(motion_id)

        return total

    def load(self):
        # Data loaded with:
        # time_stamp, name, id, data, imu

        if not os.path.isfile(self.filename + self.file_ext):
            logging.info('File Not Found: ' + self.filename + self.file_ext)
            return

        if not os.access(self.filename + self.file_ext, os.R_OK):
            logging.info('File Not Readable: ' + self.filename + self.file_ext)
            return

        try:
            h5 = h5py.File(self.filename + self.file_ext, 'r')
        except IOError:
            logging.info('Error Loading file: ' + self.filename + self.file_ext)
            return

        # Extract info from hdf5, but don't update object until we verify it's OK data

        id = h5['/data/id'][:].tolist()
        motion_name = h5['/data/name'][:].tolist()
        for idx_, val_ in enumerate(motion_name):
            motion_name[idx_] = val_.decode('utf-8')
        data = h5['/data/data'][:].tolist()
        imu = h5['/data/imu'][:].tolist()
        time_stamp = h5['/data/time_stamp'][:].tolist()
        num_samples = len(id)
        # Done with file
        h5.close()

        # check values.  most common issue would be if labels don't match data
        if num_samples == len(data) and num_samples == len(motion_name) and num_samples == len(time_stamp):
            with self.__lock:
                self.id = id
                self.name = motion_name
                self.data = data
                self.time_stamp = time_stamp
                self.imu = imu
                self.num_samples = num_samples

                # self.motion_names = motion_name
        else:
            logging.error('Invalid training data with mismatched data lengths')

    def file_saved(self):
        if not os.path.isfile(self.filename + self.file_ext):
            logging.info('File Not Found: ' + self.filename + self.file_ext)
            return False

        if not os.access(self.filename + self.file_ext, os.R_OK):
            logging.info('File Not Readable: ' + self.filename + self.file_ext)
            return False
            
        return True
        
    def save(self):
        t = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        h5 = h5py.File(self.filename + self.file_ext, 'w')
        group = h5.create_group('data')
        group.attrs['description'] = t + 'Myo Armband Raw EMG Data'
        group.attrs['num_channels'] = self.num_channels
        group.attrs['num_features'] = len(self.features)
        group.attrs['num_samples'] = self.num_samples
        group.attrs['feature_names'] = [a.encode('utf8') for a in self.features]
        group.create_dataset('time_stamp', data=self.time_stamp)
        group.create_dataset('id', data=self.id)
        encoded = [a.encode('utf8') for a in self.name]
        group.create_dataset('name', data=encoded)
        group.create_dataset('data', data=self.data)
        group.create_dataset('imu', data=self.imu)
        group.create_dataset('motion_names', data=[a.encode('utf8') for a in self.motion_names])  # utf-8
        h5.close()
        logging.info('Saved ' + self.filename)

    def copy(self):
        # if a training file exists, copy it to a datestamped name

        if not os.path.isfile(self.filename + self.file_ext):
            logging.info('File Not Found: ' + self.filename + self.file_ext)
            return

        if not os.access(self.filename + self.file_ext, os.R_OK):
            logging.info('File Not Readable: ' + self.filename + self.file_ext)
            return

        t = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        src_ = self.filename + self.file_ext
        dst_ = self.filename + '_' + t + self.file_ext
        try:
            copyfile(src_, dst_)
        except IOError:
            logging.info('Failed to create file backup')

    def delete(self):
        # if a training file exists, delete it

        f = self.filename + self.file_ext
        if not os.path.isfile(f):
            logging.info('File Not Found: ' + f)
            return

        if not os.access(f, os.R_OK):
            logging.info('File Not Readable: ' + f)
            return

        try:
            os.remove(f)
            logging.info('Deleted ' + self.filename)
        except IOError:
            logging.info('Failed to delete file: ' + f)

    def get_motion_image(self, motion_name):
        # Method to return motion image filename relative to www/mplHome directory

        # Ensure class name exists
        try:
            self.motion_names.index(motion_name)
        except ValueError:
            logging.info('Motion name ' + motion_name + ' does not exist')
            return None

        # Parse motion name - image map file
        map_path = os.path.join(os.path.dirname(__file__), '..', '..', 'www', 'mplHome', 'motion_name_image_map.csv')
        mapped_motion_names = []
        mapped_image_names = []
        with open(map_path, 'rt', encoding='ascii') as csvfile:
            # RSA: Updated to allow comments in motion_name_image_map file
            rows = csv.reader(filter(lambda row: row[0] != '#', csvfile), delimiter=',')
            for this_row in rows:
                mapped_motion_names.append(this_row[0])
                mapped_image_names.append(this_row[1])

        # Check if queried motion name is in map file
        if motion_name not in mapped_motion_names:
            logging.info('Motion name ' + motion_name + ' does not have associated image file')
            return None

        # Pull mapped image name corresponding to motion name
        image_name = mapped_image_names[mapped_motion_names.index(motion_name)]
        return image_name
