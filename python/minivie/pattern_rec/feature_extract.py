import numpy as np


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
            f = np.squeeze(self.feature_extract(data * 0.01))

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