import struct
import time

import numpy as np
from transforms3d.euler import quat2euler
from transforms3d.quaternions import quat2mat

from utilities import udp_comms, get_address
from inputs.myo import MYOHW_ORIENTATION_SCALE, MYOHW_ACCELEROMETER_SCALE, MYOHW_GYROSCOPE_SCALE
from inputs.signal_input import SignalInput
import logging

logger = logging.getLogger(__name__)


class MyoUdp(SignalInput):
    """

        Class for receiving Myo Armband data via UDP

        Handles streaming data from MyoUdp.Exe OR streaming data from unix based streaming

        Note the use of __private variable and threading / locks to ensure data is read safely

    """

    def __init__(self, local_addr_str='//0.0.0.0:15001', remote_addr_str='//127.0.0.1:16001', num_samples=50):

        # Initialize superclass
        super(MyoUdp, self).__init__()

        # logger
        self.log_handlers = None

        # 8 channel max for myo armband
        self.num_channels = 8
        self.num_samples = num_samples

        # Default kinematic values
        self.__quat = (1.0, 0.0, 0.0, 0.0)
        self.__accel = (0.0, 0.0, 0.0)
        self.__gyro = (0.0, 0.0, 0.0)

        # Default data buffer [nSamples by nChannels]
        # Treat as private.  use get_data to access since it is thread-safe
        self.__dataEMG = np.zeros((num_samples, 8))

        # Internal values
        self.__battery_level = -1  # initial value is unknown
        self.__rate_emg = 0.0
        self.__count_emg = 0  # reset counter
        self.__time_emg = 0.0
        self.emg_rate_update_interval = 1.5

        self.transport = udp_comms.Udp()
        self.transport.name = 'MyoUdpRcv'
        self.transport.local_addr = get_address(local_addr_str)
        self.transport.remote_addr = get_address(remote_addr_str)
        self.transport.add_message_handler(self.parse_messages)

    def connect(self):
        """
            Connect to the udp server and receive Myo Packets
        """
        self.transport.connect()

    def parse_messages(self, data):
        """ Convert incoming bytes to emg, quaternion, accel, and ang rate """

        num_emg_samples = 0
        if len(data) == 48:  # NOTE: This is the packet size for MyoUdp.exe
            # -------------------------------
            # Handles data from MyoUdp.exe
            # -------------------------------
            # unpack formatted data bytes
            # Note: these have been scaled in MyoUdp from the raw hardware values
            output = struct.unpack("8b 4f 3f 3f", data)

            if self.log_handlers is not None:
                self.log_handlers(output[0:8])

            # Populate EMG Data Buffer (newest on top)
            self.__dataEMG = np.roll(self.__dataEMG, 1, axis=0)
            self.__dataEMG[:1, :] = output[:8]  # insert in first buffer entry
            num_emg_samples = 1

            # IMU Data Update
            self.__quat = output[8:12]
            self.__accel = output[12:15]
            self.__gyro = output[15:18]

        elif len(data) == 16:  # EMG data only
            #    Myo UNIX  Data packet information:
            #        <case> 16
            #            # EMG Samples (8 channels 2 samples per packet)

            output = struct.unpack('16b', data)

            # Populate EMG Data Buffer (newest on top)
            self.__dataEMG = np.roll(self.__dataEMG, 1, axis=0)
            self.__dataEMG[:1, :] = output[0:8]  # insert in first buffer entry
            self.__dataEMG = np.roll(self.__dataEMG, 1, axis=0)
            self.__dataEMG[:1, :] = output[8:16]  # insert in first buffer entry
            num_emg_samples = 2

        elif len(data) == 20:  # IMU data only
            #    Myo UNIX  Data packet information:
            #        <case> 20
            #            # IMU sample
            #            dataInt16 = double(typecast(bytes,'int16'))
            #            orientation = dataInt16(1:4) ./ MYOHW_ORIENTATION_SCALE
            #            accelerometer = dataInt16(5:7) ./ MYOHW_ACCELEROMETER_SCALE
            #            gyroscope = dataInt16(8:10) ./ MYOHW_GYROSCOPE_SCALE
            # create array of 10 int16
            output = struct.unpack('10h', data)
            unscaled = np.array(output, dtype=np.int16)

            self.__quat = np.array(unscaled[0:4], np.float) / MYOHW_ORIENTATION_SCALE
            self.__accel = np.array(unscaled[4:7], np.float) / MYOHW_ACCELEROMETER_SCALE
            self.__gyro = np.array(unscaled[7:10], np.float) / MYOHW_GYROSCOPE_SCALE

        elif len(data) == 1:  # BATT Value
            self.__battery_level = ord(data)
            msg = f'Socket {self.transport.local_addr} Battery Level: {self.__battery_level}'
            logger.info(msg)

        else:
            # incoming data is not of length = 8, 20, 40, or 48
            logger.warning(f'MyoUdp: Unexpected packet size. len=({len(data)})')

        if num_emg_samples == 0:
            return
        else:
            self.__count_emg += num_emg_samples

    def get_data(self):
        """ Return data buffer [nSamples][nChannels] """
        return self.__dataEMG

    def get_angles(self):
        """ Return Euler angles computed from Myo quaternion """
        # convert the stored quaternions to angles
        return quat2euler(self.__quat)

    def get_rotationMatrix(self):
        """ Return rotation matrix computed from Myo quaternion"""
        rot_mat = quat2mat(self.__quat)
        try:
            [U, s, V] = np.linalg.svd(rot_mat)
            return np.dot(U, V)
        except:
            return np.eye(3)

    def get_imu(self):
        """ Return IMU data as a dictionary
        result['quat'] = (qw qx qy qz)
        result['accel'] = (ax ay az)
        result['gyro'] = (rx ry rz)
        """
        return {'quat': self.__quat , 'accel': self.__accel, 'gyro': self.__gyro}

    def get_battery(self):
        # Return the battery value (0-100)
        battery = self.__battery_level
        return battery

    def get_data_rate_emg(self):
        # Data rate is just EMG rate, not IMU or packet rate and should be calculated accordingly
        # Return the emg data rate

        # compute data rate
        t_now = time.time()
        t_elapsed = t_now - self.__time_emg

        if t_elapsed > self.emg_rate_update_interval:

            # compute rate (every second)
            self.__rate_emg = self.__count_emg / t_elapsed
            self.__count_emg = 0  # reset counter
            # reset time
            self.__time_emg = time.time()

        return self.__rate_emg

    def get_status_msg(self):
        # return string formatted status message
        # with data rate and battery percentage
        # E.g. 200Hz 99%
        battery = self.get_battery()
        if battery < 0:
            battery = '--'
        return f'MYO: {self.get_data_rate_emg():.0f}Hz {battery}%'

    def close(self):
        self.transport.close()
