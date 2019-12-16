# open_nfu.py
# Interface class for the JHU/APL openNFU
#
# Interface is via UDP messages to send and receive data
#
#
#
# Revisions:
#    08SEP2017 Armiger: Added limb state commands
#    03DEC2017 Armiger: Removed locking since only attributes are being changed.
#                        Updated log format for better performance
#                        Added SHUTDOWN_VOLTAGE Critical bus voltage that will trigger immediate system shutdown
#


from collections import deque
from os import name as os_name
import threading
import socket
import logging
import struct
import time
import numpy as np
import mpl
import controls
from mpl.data_sink import DataSink
from mpl import JointEnum as MplId, extract_percepts
from utilities.user_config import read_user_config_file, get_user_config_var


class NfuUdp(DataSink):
    """
    Python Class for NFU connections

    Hostname is the IP of the NFU
    UdpTelemPort is where percepts and EMG from NFU are received locally
    UdpCommandPort
    TcpCommandPort

    """

    def __init__(self, hostname="127.0.0.1", udp_telem_port=9028, udp_command_port=9027):

        # Initialize superclass
        super(NfuUdp, self).__init__()

        self.udp = {'Hostname': hostname, 'TelemPort': udp_telem_port, 'CommandPort': udp_command_port}
        self.verbosity = {'echoHeartbeat': True, 'echoPercepts': False}

        self.sock = None

        # Create a receive thread
        self.thread = threading.Thread(target=self.message_handler)
        self.thread.name = 'NfuUdpRcv'

        # mpl_status updated by heartbeat messages
        self.mpl_status_default = {
            'nfu_state': 'NULL',
            'lc_software_state': 'NULL',
            'lmc_software_state': [0, 0, 0, 0, 0, 0, 0],
            'bus_voltage': 0.0,
            'nfu_ms_per_CMDDOM': 0.0,
            'nfu_ms_per_ACTUATEMPL': 0.0,
        }
        self.mpl_status = self.mpl_status_default

        # battery samples will contain N most recent samples for averaging
        self.battery_samples = deque([], maxlen=15)

        self.reset_impedance = False
        self.magic_impedance = [40.0] * controls.NUM_UPPER_ARM_JOINTS + [15.6288] * controls.NUM_HAND_JOINTS

        # create a counter to delay how often CPU temperature is read and logged
        self.last_temperature = 0.0
        self.last_temperature_counter = 0

        self.stiffness_high = None
        self.stiffness_low = None
        self.joint_offset = None

        self.shutdown_voltage = None
        # RSA: moved this parameter out of the load function to not overwrite on reload from app
        # self.enable_impedance = None
        self.enable_impedance = get_user_config_var('MPL.enable_impedance', 0)
        self.impedance_level = 'high'  # Options are low | high
        self.percepts = None
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
        # open up the socket and bind to IP address

        # log socket creation
        logging.info('Setting up UDP comms on port {}. Default destination is {}:{}:'.format(
            self.udp['TelemPort'], self.udp['Hostname'], self.udp['CommandPort']))

        # create socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # bind to any IP address at the 'Telemetry' port (the port on which percepts are received)
        self.sock.bind(('0.0.0.0', self.udp['TelemPort']))
        # set timeout in seconds
        self.sock.settimeout(3.0)

        # Create a thread for processing new data
        if not self.thread.isAlive():
            logging.warning('Starting NfuUdp rcv thread')
            self.thread.start()

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
                #logging.warning('Failed to get system processor temperature')
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

        return msg

    def stop(self):
        # stop the receive thread
        self.thread.join()

    def close(self):
        """ Cleanup socket """
        if self.sock is not None:
            logging.info("Closing NfuUdp Socket IP={} Port={}".format(self.udp['Hostname'], self.udp['TelemPort']))
            self.sock.close()
        self.stop()

    def message_handler(self):
        # Loop forever to receive data via UDP
        #
        # This is a thread to receive data as soon as it arrives.
        while True:
            # Blocking call until data received
            try:
                # receive call will error if socket closed externally (i.e. on exit)
                raw_chars, address = self.sock.recvfrom(8192)  # blocks until timeout or socket closed
                data = bytearray(raw_chars)

                # if the above function returns (without error) it means we have a connection
                if not self.active_connection:
                    logging.info('MPL Connection is Active: Data received')
                    self.active_connection = True

            except socket.timeout as e:
                # the data stream has stopped.  don't break the thread, just continue to wait
                msg = "NfuUdp timed out during recvfrom() on IP={} Port={}. Error: {}".format(
                    self.udp['Hostname'], self.udp['TelemPort'], e)
                logging.warning(msg)
                logging.info('MPL Connection is Lost')
                self.active_connection = False
                self.mpl_status = self.mpl_status_default
                continue

            except socket.error:
                # The connection has been closed
                msg = "NfuUdp Socket Closed on IP={} Port={}.".format(
                    self.udp['Hostname'], self.udp['TelemPort'])
                logging.info(msg)
                # break so that the thread can terminate
                break

            # Get the message ID
            if len(data) < 3:
                logging.warning('Message received was too small. Minimum message size is 3 bytes')
                continue
            else:
                msg_id = data[2]

            if msg_id == mpl.NfuUdpMsgId.UDPMSGID_HEARTBEATV2:
                # When we get a heartbeat message, parse the message, update the running battery voltage
                # and check for shutdown conditions

                # pass message bytes
                msg = decode_heartbeat_msg_v2(data[3:])
                self.mpl_status = msg

                logging.info(msg)
                if self.verbosity['echoHeartbeat']:
                    print(msg)

                self.battery_samples.append(msg['bus_voltage'])

                # Check Limb Shutdown Condition
                # Note that 0.0 is a voltage reported as a valid heartbeat when hand disconnected
                v_battery = sum(self.battery_samples)/len(self.battery_samples)
                logging.info('Moving Average Bus Voltage: ' + str(v_battery))
                if v_battery != 0.0 and v_battery < self.shutdown_voltage:
                    # Execute limb Shutdown procedure
                    # Send a log message; set LC to soft reset; poweroff NFU
                    from utilities.sys_cmd import shutdown
                    msg = 'MPL bus voltage is {} and below critical value {}.  Shutting down system!'
                    print(msg)
                    logging.critical(msg)
                    self.set_limb_soft_reset()
                    shutdown()

            elif msg_id == mpl.NfuUdpMsgId.UDPMSGID_PERCEPTDATA:
                # Percept message comes in as follows: <class:bytes> len=879
                #
                # Note this has some useful info on message creation and timing on the DART processor
                #
                # After switching to str join, this whole function with logging is 1.5-3 ms

                # t = time.time()
                percepts = extract_percepts.extract(raw_chars)  # takes 1-3 ms on DART
                self.percepts = percepts

                self.position['last_percept'] = np.array(percepts['jointPercepts']['position'])

                values = np.array(percepts['jointPercepts']['torque'])  # DART Time: 50-70 us
                msg = 'Torque: ' + ','.join(['%.1f' % elem for elem in values])  # DART Time: 220 us
                logging.info(msg)  # 60 us

                values = np.array(percepts['jointPercepts']['temperature'])  # DART Time: 50-70 us
                msg = 'Temp: ' + ','.join(['%d' % elem for elem in values])  # DART Time: 220 us
                logging.info(msg)  # 60 us

                # msg = 'Joint Percepts:' + np.array2string(values,
                #                                           formatter={'float_kind': lambda x: "%6.2f" % x},
                #                                           separator=',',
                #                                           max_line_width=200) # 3-10ms

                # Takes 8ms:
                # msg = np.array2string(values, precision=2, separator=',',max_line_width=200, prefix='Joint Percepts')

                # print('Percept time: {}'.format(time.time() - t))

                if self.verbosity['echoPercepts']:
                    print(msg)

                pass

    def send_joint_angles(self, values, velocity=[0.0]*mpl.JointEnum.NUM_JOINTS):
        # Transmit joint angle command in radians
        #
        # Inputs:
        #
        # values -
        #    joint angles in radians of size 7 for arm joints  (e.g. [0.0] * 7 )
        #    joint angles in radians of size 27 for all arm joints (e.g. [0.0] * 27 )
        #
        # Impedance Notes
        # 0 to 256 for upper arm (256 is off)
        # upper arm around 40
        # wrist around 20, start around 40
        # hand is 0 to 16 (16 is off)
        # 0 to 1.5 for hand is useful range
        #
        # imp = [256*ones(1,4) 256*ones(1,3) 15.6288*ones(1,20)];
        # imp = [256*ones(1,4) 256*ones(1,3) 0.5*ones(1,20)];
        #

        if not self.active_connection and self.mpl_connection_check:
            logging.warning('MPL Connection is closed; not sending joint angles.')
            return

        if len(values) == controls.NUM_UPPER_ARM_JOINTS:
            # append hand angles
            # TODO: consider keeping hand in current position
            values = np.append(values, controls.NUM_HAND_JOINTS * [0.0])

        # 3/24/2017 RSA: Updated angle formatting
        # 'Joint Angles: [0.00 1.20 3.14 ... ]'
        # logging.info('Joint Angles: ' +
        #             np.array2string(np.array(values),
        #                             formatter={'float_kind': lambda x: "%.2f" % x}, max_line_width=250,
        #                             suppress_small=True))
        # 12/3/2017 RSA: Updated angle formatting again after seeing how slow array2string can be
        msg = 'CmdAngles: ' + ','.join(['%.1f' % elem for elem in values])
        logging.info(msg)

        # TEMP fix to lock middle finger and prevent drift
        # values[mpl.JointEnum.MIDDLE_MCP] = 0.35
        # values[mpl.JointEnum.MIDDLE_PIP] = 0.35
        # values[mpl.JointEnum.MIDDLE_DIP] = 0.35
        # values[mpl.JointEnum.THUMB_CMC_FE] = values[mpl.JointEnum.THUMB_CMC_AB_AD] + 0.5
        values = np.array(values) + self.joint_offset

        # velocity is currently unused, but need to assign value for correct transmission
        if self.reset_impedance:
            # PVI Command w/ magic number
            payload = np.append(values, velocity)
            payload = np.append(payload, self.magic_impedance)
            # uint16 MSG_LENGTH + uint8 MSG_TYPE + 1 msg_id + payload + checksum
            packer = struct.Struct('HBB81f')
            msg_bytes = packer.pack(327, 5, 8, *payload)

        elif self.enable_impedance:
            # PVI Command
            payload = np.append(values, velocity)
            if self.impedance_level == 'low':
                payload = np.append(payload, self.stiffness_low)
            else:
                payload = np.append(payload, self.stiffness_high)
            # uint16 MSG_LENGTH + uint8 MSG_TYPE + 1 msg_id + payload + checksum
            packer = struct.Struct('HBB81f')
            msg_bytes = packer.pack(327, 5, 8, *payload)

        else:
            # PV Command
            payload = np.append(values, velocity)
            # uint16 MSG_LENGTH + uint8 MSG_TYPE + 1 msg_id + payload + checksum
            packer = struct.Struct('HBB54f')
            msg_bytes = packer.pack(219, 5, 1, *payload)

        checksum = bytearray([sum(msg_bytes) % 256])

        # add on the checksum
        self.send_udp_command(msg_bytes + checksum)

    def set_limb_idle(self):
        # Send limb to idle; this is a lower power mode that still maintains position
        msg = bytearray([3, 0, 10, 10, 23])
        self.send_udp_command(msg)

    def set_limb_soft_reset(self):
        # Send limb to soft reset.  This will allow back driving joints. Active state resumes when next command received
        msg = bytearray([3, 0, 11, 11, 25])
        self.send_udp_command(msg)

    def send_udp_command(self, msg):
        # transmit packets (and optionally write to log for DEBUG)
        self.sock.sendto(msg, (self.udp['Hostname'], self.udp['CommandPort']))

    def get_percepts(self):
        return self.percepts


def decode_heartbeat_msg_v2(msg_bytes):

    # Check if b is input as bytes, if so, convert to uint8
    if isinstance(msg_bytes, (bytes, bytearray)):
        msg_bytes = struct.unpack('B' * len(msg_bytes), msg_bytes)
        msg_bytes = np.array(msg_bytes, np.uint8)

    # REF: mpl.__init__.py for state enumerations
    # // published by openNFU (v2) at 1Hz
    # uint16_t length;                // the number of bytes excluding this field; 6 for an 8byte packet
    # uint8_t msgID;                  // should be UDPMSGID_PERCEPT_HEARTBEATV2
    #
    # uint8_t nfu_state;              // enum corresponding to BOOTSTATE of the NFU
    # uint8_t lc_software_state;      // enum corresponding to SWSTATE of the LC
    # uint8_t lmc_software_state[7];  // enum corresponding to SWSTATE of the LMCs
    # float32_t bus_voltage;          // units in Volts
    # float32_t nfu_ms_per_CMDDOM;    // average number of milliseconds between CMD_DOM issuances
    # float32_t nfu_ms_per_ACTUATEMPL;// average number of milliseconds between ACTUATE_MPL receipts
    #
    # // additional data possible
    # // messages per second
    # // flag - doubled messages per handle

    # Lookup NFU state id from the enumeration
    nfu_state_id = msg_bytes[0].view(np.uint8)
    try:
        nfu_state_str = str(mpl.BOOTSTATE(nfu_state_id)).split('.')[1]
    except ValueError:
        nfu_state_str = 'NFUSTATE_ENUM_ERROR={}'.format(nfu_state_id)

    # Lookup LC state id from the enumeration
    lc_state_id = msg_bytes[1].view(np.uint8)
    try:
        lc_state_str = str(mpl.LcSwState(lc_state_id)).split('.')[1]
    except ValueError:
        lc_state_str = 'LCSTATE_ENUM_ERROR={}'.format(nfu_state_id)

    msg = {
        'nfu_state': nfu_state_str,
        'lc_software_state': lc_state_str,
        'lmc_software_state': msg_bytes[2:9],
        'bus_voltage': msg_bytes[9:13].view(np.float32)[0],
        'nfu_ms_per_CMDDOM': msg_bytes[13:17].view(np.float32)[0],
        'nfu_ms_per_ACTUATEMPL': msg_bytes[17:21].view(np.float32)[0],
    }

    return msg


class Simulator(object):

    def __init__(self):
        # Create a simulator that sends percepts and heartbeats.  Data comes from nfu_event_sim.csv file
        print('Starting Simulator')

        self.sim_file = '../tests/nfu_event_sim.csv'

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', 9027))
        self.sock.settimeout(3.0)

        self.stop_event = threading.Event()

        self.thread = threading.Thread(target=self.loop)
        self.thread.name = 'OpenNfuSimulator'

    def start(self):
        self.thread.start()

    def loop(self):
        import csv
        import time

        run = True

        while run:
            print('Running Simulator...')
            with open(self.sim_file, 'rt', encoding='ascii') as csv_file:
                rows = csv.reader(csv_file, delimiter=',')
                for row in rows:
                    b = bytearray.fromhex(''.join(row))
                    self.sock.sendto(b, ('127.0.0.1', 9028))
                    time.sleep(controls.timestep)
                    if self.stop_event.is_set():
                        run = False
                        break

    def stop(self):
        # stop simulator thread
        print('Stopping Simulator')
        self.stop_event.set()
        self.sock.close()


def test_simulator(duration=10):
    # Run simulator for testing.  From command line:
    # py -3 -c "from mpl.open_nfu import test_simulator; test_simulator()"
    import time

    a = Simulator()
    a.start()
    try:
        time.sleep(duration)
    except KeyboardInterrupt:
        pass

    a.stop()


def main():
    # Main function for testing limb communications, especially timing
    #
    # Note, ensure to make deep copies of joint angles, so no references are used
    import copy

    read_user_config_file('../user_config_default.xml')
    nfu = NfuUdp(hostname="127.0.0.1", udp_telem_port=9028, udp_command_port=9027)
    nfu.connect()

    # need to add a wait here to synch percepts
    # without synching first, user will get a few messages until first percepts received:
    # WARNING:root:MPL Connection is closed; not sending joint angles.
    nfu.wait_for_connection()
    start_angles = copy.deepcopy(nfu.position['last_percept'])
    angles = copy.deepcopy(start_angles)

    # Decide which way to move arm
    if start_angles[mpl.JointEnum.ELBOW] < np.deg2rad(45):
        direction = +1.0
    else:
        direction = -1.0

    # on connect, data should be streaming
    for iAngle in np.arange(0.0, 30.0, 0.2):
        time.sleep(controls.timestep)
        new_val = start_angles[mpl.JointEnum.ELBOW] + (np.deg2rad(iAngle) * direction)
        angles[mpl.JointEnum.ELBOW] = new_val
        nfu.send_joint_angles(angles)
        msg = 'JointCmd: ' + ','.join(['%.2f' % elem for elem in angles])
        print(msg)

    nfu.close()

    pass


if __name__ == '__main__':
    main()
