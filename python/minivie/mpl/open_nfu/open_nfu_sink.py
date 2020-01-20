from collections import deque
from os import name as os_name
import logging
import numpy as np
import mpl
from mpl.data_sink import DataSink
from mpl import JointEnum as MplId, extract_percepts
from mpl.open_nfu import open_nfu_protocol as nfu
from utilities.user_config import get_user_config_var
from utilities import udp_comms, get_address


class NfuSink(DataSink):
    """
    Python Class for NFU Data Sink.  Also compatible with VulcanX (though no heartbeat messages used there)
    """

    def __init__(self, local_addr_str='//0.0.0.0:9029', remote_addr_str='//127.0.0.1:9027'):

        # Initialize superclass
        super(NfuSink, self).__init__()

        # mpl_status updated by heartbeat messages
        self.mpl_status = nfu.default_status_structure

        # battery samples will contain N most recent samples for averaging
        self.battery_samples = deque([], maxlen=15)

        self.reset_impedance = False

        # create a counter to delay how often CPU temperature is read and logged
        self.last_temperature = 0.0
        self.last_temperature_counter = 0

        self.stiffness_high = None
        self.stiffness_low = None
        self.joint_offset = None
        self.mpl_connection_check = None

        self.shutdown_voltage = None
        # RSA: moved this parameter out of the load function to not overwrite on reload from app
        # self.enable_impedance = None
        self.enable_impedance = get_user_config_var('MPL.enable_impedance', 0)
        self.impedance_level = 'high'  # Options are low | high
        self.percepts = None

        # self.transport = open_nfu_comms.AsyncUdp(local_addr_str, remote_addr_str)
        # self.transport.name = 'AsyncOpenNfu'
        # self.transport.add_message_handler(self.parse_messages)
        # self.transport.connect()

        self.transport = udp_comms.Udp()
        self.transport.name = 'OpenNfu'
        self.transport.local_addr = get_address(local_addr_str)
        self.transport.remote_addr = get_address(remote_addr_str)
        self.transport.add_message_handler(self.parse_messages)

        self.load_config_parameters()

    def load_config_parameters(self):
        # Load parameters from xml config file

        # initialize stiffness to global value (overwrite later if needed)
        s = get_user_config_var('GLOBAL_HAND_STIFFNESS_HIGH', 1.5)
        self.stiffness_high = [s] * MplId.NUM_JOINTS
        s = get_user_config_var('GLOBAL_HAND_STIFFNESS_LOW', 0.75)
        self.stiffness_low = [s] * MplId.NUM_JOINTS

        self.joint_offset = [0.0] * MplId.NUM_JOINTS

        # Upper Arm
        num_upper_arm_joints = 7
        for i in range(num_upper_arm_joints):
            self.stiffness_high[i] = get_user_config_var(MplId(i).name + '_STIFFNESS_HIGH', 40.0)
            self.stiffness_low[i] = get_user_config_var(MplId(i).name + '_STIFFNESS_LOW', 20.0)

        for i in range(MplId.NUM_JOINTS):
            self.joint_offset[i] = np.deg2rad(get_user_config_var(MplId(i).name + '_OFFSET', 0.0))

        # Hand
        if not get_user_config_var('GLOBAL_HAND_STIFFNESS_HIGH_ENABLE', 0):
            for i in range(num_upper_arm_joints, MplId.NUM_JOINTS):
                self.stiffness_high[i] = get_user_config_var(MplId(i).name + '_STIFFNESS_HIGH', 4.0)
        if not get_user_config_var('GLOBAL_HAND_STIFFNESS_LOW_ENABLE', 0):
            for i in range(num_upper_arm_joints, MplId.NUM_JOINTS):
                self.stiffness_low[i] = get_user_config_var(MplId(i).name + '_STIFFNESS_LOW', 4.0)

        self.shutdown_voltage = get_user_config_var('MPL.shutdown_voltage', 19.0)
        # self.enable_impedance = get_user_config_var('MPL.enable_impedance', 0)

        self.mpl_connection_check = get_user_config_var('MPL.connection_check', 1)

    def connect(self):
        self.transport.connect()

    def get_voltage(self):
        # returns the battery voltage as a string based on the last status message
        return '{:6.2f}'.format(self.mpl_status['bus_voltage'])

    def get_temperature(self):
        # Get the processor temperature from the system
        # returns float
        # units is celsius
        #
        # Note: this function allows setting a reduced rate for how many calls are made to the system

        # Bail out if Windows
        if os_name != 'posix':
            return 0.0

        # set a rate reduction factor to decrease calls to system process
        decimate_rate = 10

        if self.last_temperature_counter == 0:
            # Read the temperature
            try:
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    contents = f.read()
                temp = float(contents) / 1000.0
                logging.info('CPU Temp: ' + str(temp))
            except FileNotFoundError:
                # logging.warning('Failed to get system processor temperature')
                temp = 0.0
            self.last_temperature = temp
        else:
            # Use the old temp
            temp = self.last_temperature

        # increment and roll counter
        self.last_temperature_counter += 1

        if self.last_temperature_counter > decimate_rate:
            self.last_temperature_counter = 0

        return temp

    def get_status_msg(self):
        # returns a general purpose status message about the system state
        # e.g. ' 22.5V 72.6C'

        msg = u'{:4.1f}V '.format(self.mpl_status['bus_voltage'])
        msg += u'{:3.0f}\u00b0C '.format(self.get_temperature())
        msg += '<br>NFU:{} '.format(self.mpl_status['nfu_state'])
        msg += '<br>LC:{} '.format(self.mpl_status['lc_software_state'])
        msg += '<br>dt:{:.1f}ms '.format(self.mpl_status['nfu_ms_per_ACTUATEMPL'])
        msg += f'<br>Percepts:{self.transport.get_packet_data_rate():.0f} Hz'

        return msg

    def close(self):
        logging.info("Closing Nfu Data Sink")
        # self.transport.transport.close()
        self.transport.close()

    def send_joint_angles(self, values, velocity=None):
        # Transmit joint angle command in radians
        #
        # Inputs:
        #
        # values -
        #    joint angles in radians of size 7 for arm joints  (e.g. [0.0] * 7 )
        #    joint angles in radians of size 27 for all arm joints (e.g. [0.0] * 27 )
        #

        if self.mpl_connection_check and self.transport is not None and not self.transport.data_received:
            logging.warning('MPL Connection is closed; not sending joint angles.')
            return

        if len(values) == mpl.NUM_UPPER_ARM_JOINTS:
            # append hand angles
            # TODO: consider keeping hand in current position
            values = np.append(values, mpl.NUM_HAND_JOINTS * [0.0])

        if velocity is None:
            velocity = [0.0] * mpl.JointEnum.NUM_JOINTS

        # 1/10/2020 RSA: Further compressed 0.00 to 0, others to 2 decimal places
        log_msg = 'CmdAngles: ' + ','.join(['0' if elem == 0 else '%.2f' % elem for elem in values])
        logging.info(log_msg)

        values = np.array(values) + self.joint_offset

        # velocity is currently unused, but need to assign value for correct transmission
        if self.reset_impedance:
            msg = nfu.encode_impedance_reset(values, velocity)
        elif self.enable_impedance:
            # Impedance ON; PVI Commands
            if self.impedance_level == 'low':
                # Low Impedance
                msg = nfu.encode_position_velocity_impedance_command(values, velocity, self.stiffness_low)
            else:
                # High Impedance
                msg = nfu.encode_position_velocity_impedance_command(values, velocity, self.stiffness_high)
        else:
            # Impedance OFF; PV Commands
            msg = nfu.encode_position_velocity_command(values, velocity)

        self.send_udp_command(msg)

    def set_limb_idle(self):
        # Send limb to idle; this is a lower power mode that still maintains position
        self.send_udp_command(nfu.encode_cmd_state_limb_idle())

    def set_limb_soft_reset(self):
        # Send limb to soft reset.  This will allow back driving joints. Active state resumes when next command received
        self.send_udp_command(nfu.encode_cmd_state_limb_soft_reset())

    def send_udp_command(self, msg):
        # transmit packets (and optionally write to log for DEBUG)
        self.transport.send(msg)

    def get_percepts(self):
        return self.percepts

    # raw_chars, address = self.sock.recvfrom(8192)  # blocks until timeout or socket closed
    # msg_bytes = bytearray(raw_chars)
    def parse_messages(self, data):
        """General purpose message routing and logging

        Directs message bytes to the appropriate parsing function based on msg_id
        """

        # Get the message ID
        try:
            msg_id = data[2]
        except IndexError:
            logging.warning('Message received was too small. Minimum message size is 3 bytes')
            return

        if msg_id == nfu.NfuUdpMsgId.UDPMSGID_HEARTBEATV2:
            # When we get a heartbeat message, parse the message, update the running battery voltage
            # and check for shutdown conditions

            # pass message bytes
            mpl_status = nfu.parse_heartbeat(data[3:])
            # msg will have fields according to 'default_status_structure'

            self.mpl_status = mpl_status

            logging.info(mpl_status)

            self.battery_samples.append(mpl_status['bus_voltage'])

            # Check Limb Shutdown Condition
            # Note that 0.0 is a voltage reported as a valid heartbeat when hand disconnected
            v_battery = sum(self.battery_samples) / len(self.battery_samples)
            logging.info('Moving Average Bus Voltage: ' + str(v_battery))
            if v_battery != 0.0 and v_battery < self.shutdown_voltage:
                # Execute limb Shutdown procedure
                # Send a log message; set LC to soft reset; poweroff NFU
                from utilities.sys_cmd import shutdown
                mpl_status = 'MPL bus voltage is {} and below critical value {}.  Shutting down system!'
                print(mpl_status)
                logging.critical(mpl_status)
                self.set_limb_soft_reset()
                shutdown()

        elif msg_id == nfu.NfuUdpMsgId.UDPMSGID_PERCEPTDATA:
            # Percept message comes in as follows: <class:bytes> len=879
            #
            # Note this has some useful info on message creation and timing on the DART processor
            #
            # After switching to str join, this whole function with logging is 1.5-3 ms

            # t = time.time()
            percepts = extract_percepts.extract(data)  # takes 1-3 ms on DART
            self.percepts = percepts

            values = np.array(percepts['jointPercepts']['position'])
            log_msg = 'Pos: ' + ','.join(['0' if elem == 0 else '%.2f' % elem for elem in values])  # DART Time: 220 us
            logging.info(log_msg)
            self.position['last_percept'] = values

            values = np.array(percepts['jointPercepts']['torque'])  # DART Time: 50-70 us
            log_msg = 'Torque: ' + ','.join(['0' if elem == 0 else '%.2f' % elem for elem in values])
            logging.info(log_msg)  # 60 us

            values = np.array(percepts['jointPercepts']['temperature'])  # DART Time: 50-70 us
            log_msg = 'Temp: ' + ','.join(['%d' % elem for elem in values])  # DART Time: 220 us
            logging.info(log_msg)  # 60 us

    def data_received(self):
        """
        Define a check for whether data (percepts) are actively coming in.  Note you can be connected (udp socket open)
        but not receiving data, hence this function

        @return: bool
        """
        return self.position['last_percept'] is not None and self.transport.get_packet_data_rate() > 0
