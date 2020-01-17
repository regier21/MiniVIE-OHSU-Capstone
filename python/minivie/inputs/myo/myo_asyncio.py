#!/usr/bin/env python3
"""

This module contains a myo client based on asynchronous UDP transport protocols

Note this module performs poorly with severe timing delays on the DART SOM board and should be avoided.

+--------------------------+
Start a myo armband receiver
+--------------------------+
In a python script:

from inputs import myo_asyncio as myo

m = myo.MyoUdp(source='//127.0.0.1:15001')
m.connect()
m.get_data()   # returns a numpy data buffer of size [nSamples][nChannels] of latest samples


Revisions:

1.0.0 RSA: Created based on myo receiver using threads

@author: R. Armiger
"""

import struct
import numpy as np
import logging
import time
from transforms3d.euler import quat2euler
from transforms3d.quaternions import quat2mat
from inputs.signal_input import SignalInput
import utilities
import asyncio

logger = logging.getLogger(__name__)

__version__ = "3.0.0"

# Scaling constants for MYO IMU Data
MYOHW_ORIENTATION_SCALE = 16384.0
MYOHW_ACCELEROMETER_SCALE = 2048.0
MYOHW_GYROSCOPE_SCALE = 16.0


class UdpProtocol(asyncio.DatagramProtocol):
    """ Extend the UDP Protocol for myo data communication

    """
    def __init__(self, parent):
        self.parent = parent
        # Mark the time when object created. Note this will get overwritten once data received
        self.parent.time_emg = time.time()

    def datagram_received(self, data, addr):

        if len(data) == 48:  # NOTE: This is the packet size for MyoUdp.exe
            # -------------------------------
            # Handles data from MyoUdp.exe
            # -------------------------------
            # unpack formatted data bytes
            # Note: these have been scaled in MyoUdp from the raw hardware values
            output = struct.unpack("8b4f3f3f", data)

            if self.parent.log_handlers is not None:
                self.parent.log_handlers(output[0:8])

            # Populate EMG Data Buffer (newest on top)
            self.parent.dataEMG = np.roll(self.parent.dataEMG, 1, axis=0)
            self.parent.dataEMG[:1, :] = output[:8]  # insert in first buffer entry

            # IMU Data Update
            self.parent.quat = output[8:12]
            self.parent.accel = output[12:15]
            self.parent.gyro = output[15:18]

            # count samples toward data rate
            self.parent.count_emg += 1  # 2 data points per packet

        elif len(data) == 16:  # EMG data only
            # -------------------------------------
            # Handles data from unix direct stream
            # -------------------------------------

            #    Myo UNIX  Data packet information:
            #    Data packet size either 16 or 20 bytes.
            #        <case> 16
            #            # EMG Samples (8 channels 2 samples per packet)
            #            d = double(typecast(bytes,'int8'))
            #            emgData = reshape(d,8,2)
            #        <case> 20
            #            # IMU sample
            #            MYOHW_ORIENTATION_SCALE = 16384.0
            #            MYOHW_ACCELEROMETER_SCALE = 2048.0
            #            MYOHW_GYROSCOPE_SCALE = 16.0
            #            dataInt16 = double(typecast(bytes,'int16'))
            #            orientation = dataInt16(1:4) ./ MYOHW_ORIENTATION_SCALE
            #            accelerometer = dataInt16(5:7) ./ MYOHW_ACCELEROMETER_SCALE
            #            gyroscope = dataInt16(8:10) ./ MYOHW_GYROSCOPE_SCALE

            output = struct.unpack('16b', data)
            # Populate EMG Data Buffer (newest on top)
            self.parent.dataEMG = np.roll(self.parent.dataEMG, 1, axis=0)
            self.parent.dataEMG[:1, :] = output[0:8]  # insert in first buffer entry
            self.parent.dataEMG = np.roll(self.parent.dataEMG, 1, axis=0)
            self.parent.dataEMG[:1, :] = output[8:16]  # insert in first buffer entry

            # count samples toward data data rate
            self.parent.count_emg += 2  # 2 data points per packet

        elif len(data) == 20:  # IMU data only

            # create array of 10 int16
            output = struct.unpack('10h', data)
            unscaled = np.array(output, dtype=np.int16)

            self.parent.quat = np.array(unscaled[0:4], np.float) / MYOHW_ORIENTATION_SCALE
            self.parent.accel = np.array(unscaled[4:7], np.float) / MYOHW_ACCELEROMETER_SCALE
            self.parent.gyro = np.array(unscaled[7:10], np.float) / MYOHW_GYROSCOPE_SCALE

        elif len(data) == 1:  # Battery Value
            self.parent.battery_level = ord(data)
            msg = 'Socket {} Battery Level: {}'.format(self.parent.addr, self.parent.battery_level)
            logger.info(msg)

        else:
            # incoming data is not of length = 8, 20, 40, or 48
            logger.warning('MyoUdp: Unexpected packet size. len=({})'.format(len(data)))


class MyoUdp(SignalInput):
    """

        Class for receiving Myo Armband data via UDP

        Handles streaming data from MyoUdp.Exe OR streaming data from unix based streaming

        Note the use of private variable and threading / locks to ensure data is read safely

    """

    def __init__(self, source='//127.0.0.1:10001', num_samples=50):

        # Initialize superclass
        super(MyoUdp, self).__init__()

        # logger
        self.log_handlers = None

        # 8 channel max for myo armband
        self.num_channels = 8
        self.num_samples = num_samples

        # Default kinematic values
        self.quat = (1.0, 0.0, 0.0, 0.0)
        self.accel = (0.0, 0.0, 0.0)
        self.gyro = (0.0, 0.0, 0.0)

        # Default data buffer [nSamples by nChannels]
        # Treat as private.  use get_data to access since it is thread-safe
        self.dataEMG = np.zeros((num_samples, 8))

        # UDP Port setup
        self.addr = utilities.get_address(source)

        # Internal values
        self.battery_level = -1  # initial value is unknown
        self.count_emg = 0
        self.time_emg = 0.0
        self.rate_emg = 0.0
        self.update_time = 1.0  # seconds

        # Initialize connection parameters
        self.loop = None
        self.transport = None
        self.protocol = None

        self.local_address = source

    def connect(self):
        """
            Connect to the udp server and receive Myo Packets

        """
        logger.info("Setting up MyoUdp socket {}".format(self.addr))
        self.loop = asyncio.get_event_loop()

        listen = self.loop.create_datagram_endpoint(
            lambda: UdpProtocol(parent=self), local_addr=self.addr)
        self.transport, self.protocol = self.loop.run_until_complete(listen)
        pass

    def get_data(self):
        """ Return data buffer [nSamples][nChannels] """
        return self.dataEMG

    def get_angles(self):
        """ Return Euler angles computed from Myo quaternion """
        # convert the stored quaternions to angles
        return quat2euler(self.quat)

    def get_rotationMatrix(self):
        """ Return rotation matrix computed from Myo quaternion"""
        rot_mat = quat2mat(self.quat)
        try:
            [U, s, V] = np.linalg.svd(rot_mat)
            return np.dot(U, V)
        except:
            return np.eye(3)

    def get_imu(self):
        """ Return IMU data as a dictionary
        result['quat'] = (qw qx qy qz) (quaternion)
        result['accel'] = (ax ay az)
        result['gyro'] = (rx ry rz)
        """
        return {'quat': self.quat, 'accel': self.accel, 'gyro': self.gyro}

    def get_battery(self):
        # Return the battery value (0-100)
        battery = self.battery_level
        return battery

    def get_data_rate_emg(self):
        # Return the emg data rate

        # get the number of new samples over the last n seconds

        # compute data rate
        t_now = time.time()
        t_elapsed = t_now - self.time_emg

        if t_elapsed > self.update_time:
            # compute rate (every few seconds second)
            self.rate_emg = self.count_emg / t_elapsed
            self.count_emg = 0  # reset counter
            self.time_emg = t_now

        return self.rate_emg

    def get_status_msg(self):
        # return string formatted status message
        # with data rate and battery percentage
        # E.g. 200Hz 99%
        battery = self.get_battery()
        if battery < 0:
            battery = '--'
        return 'MYO: {:.0f}Hz {}%'.format(self.get_data_rate_emg(), battery)

    def close(self):
        """ Cleanup socket """
        logger.info("\n\nClosing MyoUdp Socket @ {}".format(self.addr))
