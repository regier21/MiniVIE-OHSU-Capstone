import csv
import datetime as dt
import logging
import os
import threading
import time
from shutil import copyfile

import h5py

from utilities.user_config import get_user_config_var


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