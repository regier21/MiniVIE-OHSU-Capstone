"""

Module contains communication protocol for exchanging data with the MPL

Basic formatting of messages from nfu_event program is:
[uint16 msg_length][uint8 msg_id][bytearray payload]

messages are parsed based on msg_id first, then payload size

"""
from enum import Enum, IntEnum, unique
import struct
import numpy as np
import mpl
import mpl.extract_percepts
import controls


class AutoNumber(Enum):
    # While Enum, IntEnum, IntFlag, and Flag are expected to cover the majority of use-cases,
    # they cannot cover them all. Here are recipes for some different types of enumerations
    # that can be used directly, or as examples for creating one's own.
    # https://docs.python.org/3/library/enum.html
    # 8.13.14.1.4. Using a custom __new__()
    # Using an auto-numbering __new__()
    def __new__(cls):
        value = len(cls.__members__)  # + 1 Note the starts autonumbering at 0
        obj = object.__new__(cls)
        obj._value_ = value
        return obj


@unique
class NfuUdpMsgId(IntEnum):
    """
        Enumerate NFU UDP Message Types

        This enum is defined in RP3-SD630-9930-ICD_MPL_UDP_ICD_RevB_20120731, Section 3.1.2.4, Table 3 - Messages

        Example:
            import mpl
            (mpl.NfuUdpMsgId.UDPMSGID_HEARTBEATV2 == 203)
                True

            str(mpl.NfuUdpMsgId(203)).split('.')[1]

                'UDPMSGID_HEARTBEATV2'

    """

    UDPMSGID_RESERVED = 0,
    UDPMSGID_WRITE_CONFIGVALUES = 1,
    UDPMSGID_READ_CONFIGVALUES = 2,
    UDPMSGID_PING_VULCANX = 3,
    UDPMSGID_RESET_CONFIGVALUES_DEFAULTS = 4,
    UDPMSGID_ACTUATEMPL = 5, # primary control method, used to send DOM, ROC, and EP motion commands
    UDPMSGID_WRITE_IMPEDANCEVALUES = 6,
    UDPMSGID_READ_MPLSTATUS = 7,
    UDPMSGID_WRITE_PERCEPTCONFIGURATION = 8,
    UDPMSGID_NFU_IDLE = 9,
    UDPMSGID_NFU_SOFTRESTART = 10,
    UDPMSGID_NACK = 100,
    UDPMSGID_PERCEPTDATA = 200,
    UDPMSGID_PERCEPTDATA_HANDONLY = 201,
    # UDPMSGID_HEARTBEATV1 is not packed with MUD headers, no message identifier is used
    UDPMSGID_HEARTBEATV2 = 203,
    UDPMSGID_MPLERROR = 210,


class BOOTSTATE(AutoNumber):
    BOOTSTATE_UNKNOWN = ()
    BOOTSTATE_INIT_REQ = ()
    BOOTSTATE_INIT_ACK = ()
    BOOTSTATE_NODELIST_REQ = ()
    BOOTSTATE_NODELIST_ACK = ()
    BOOTSTATE_NOS_DIAG_REQ = ()
    BOOTSTATE_NOS_DIAG_ACK = ()
    #BOOTSTATE_LMC_WARMUP = ()
    #BOOTSTATE_LMC_READY = ()
    BOOTSTATE_PERCEPT_REQ = ()
    BOOTSTATE_PERCEPT_ACK = ()
    BOOTSTATE_COMMAND_REQ = ()
    BOOTSTATE_COMMAND_ACK = ()
    BOOTSTATE_UP = ()
    BOOTSTATE_IDLE_REQ = ()
    BOOTSTATE_IDLE_ACK = ()
    BOOTSTATE_ERR = ()
    BOOTSTATE_DOWN = ()


@unique
class LcSwState(IntEnum):
    SWSTATE_INIT = 0,
    SWSTATE_PRG = 1,
    SWSTATE_FS = 2,
    SWSTATE_NOS_CONTROL_STIMULATION = 3,
    SWSTATE_NOS_IDLE = 4,
    SWSTATE_NOS_SLEEP = 5,
    SWSTATE_NOS_CONFIGURATION = 6,
    SWSTATE_NOS_HOMING = 7,
    SWSTATE_NOS_DATA_ACQUISITION = 8,
    SWSTATE_NOS_DIAGNOSTICS = 9,
    #SWSTATE_NUM_STATES = 10
    SWSTATE_UNK = 15,


default_status_structure = {
    'nfu_state': 'NULL',
    'lc_software_state': 'NULL',
    'lmc_software_state': [0, 0, 0, 0, 0, 0, 0],
    'bus_voltage': 0.0,
    'nfu_ms_per_CMDDOM': 0.0,
    'nfu_ms_per_ACTUATEMPL': 0.0,
    }


def parse_percepts(msg_bytes):
    return mpl.extract_percepts.extract(msg_bytes)  # takes 1-3 ms on DART


def parse_heartbeat(msg_bytes):
    # Check if b is input as bytes, if so, convert to uint8
    if isinstance(msg_bytes, (bytes, bytearray)):
        msg_bytes = struct.unpack('B' * len(msg_bytes), msg_bytes)
        msg_bytes = np.array(msg_bytes, np.uint8)

    # REF: state enumerations
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
        nfu_state_str = str(BOOTSTATE(nfu_state_id)).split('.')[1]
    except ValueError:
        nfu_state_str = 'NFUSTATE_ENUM_ERROR={}'.format(nfu_state_id)

    # Lookup LC state id from the enumeration
    lc_state_id = msg_bytes[1].view(np.uint8)
    try:
        lc_state_str = str(LcSwState(lc_state_id)).split('.')[1]
    except ValueError:
        lc_state_str = 'LCSTATE_ENUM_ERROR={}'.format(nfu_state_id)

    return {
        'nfu_state': nfu_state_str,
        'lc_software_state': lc_state_str,
        'lmc_software_state': msg_bytes[2:9],
        'bus_voltage': msg_bytes[9:13].view(np.float32)[0],
        'nfu_ms_per_CMDDOM': msg_bytes[13:17].view(np.float32)[0],
        'nfu_ms_per_ACTUATEMPL': msg_bytes[17:21].view(np.float32)[0],
    }


def encode_position_velocity_impedance_command(position, velocity, impedance):
    """ All DOM PVI command """
    # Impedance Notes
    # 0 to 256 for upper arm (256 is off)
    # upper arm around 40
    # wrist around 20, start around 40
    # hand is 0 to 16 (16 is off)
    # 0 to 1.5 for hand is useful range
    #
    # imp = [256*ones(1,4) 256*ones(1,3) 15.6288*ones(1,20)];
    # imp = [256*ones(1,4) 256*ones(1,3) 0.5*ones(1,20)];

    # PVI Command
    payload = np.append(position, velocity)
    payload = np.append(payload, impedance)

    # uint16 MSG_LENGTH + uint8 MSG_TYPE + 1 msg_id + payload + checksum
    packer = struct.Struct('HBB81f')

    # 327 message length equals 27 joint angles * 3 PVI params * 4 bytes per float + 2 header bytes + 1 checksum byte
    msg_bytes = bytearray(packer.pack(327, 5, 8, *payload))
    return encode_checksum(msg_bytes)


def encode_position_velocity_command(position, velocity):
    """ All DOM PV command
    Encode MPL joint command using all degrees of motion (DOM), providing desired position and velocity of arm

    @param position: 27 by 1 numpy array of joint angular position in radians
    @param velocity: 27 by 1 numpy array of joint angular velocities
    @return: Python string of encoded bytes
    """
    # PV Command
    payload = np.append(position, velocity)

    # uint16 MSG_LENGTH + uint8 MSG_TYPE + 1 msg_id + payload + checksum
    packer = struct.Struct('HBB54f')

    # 219 message length equals 27 joint angles * 2 PV params * 4 bytes per float + 2 header bytes + 1 checksum byte
    msg_bytes = bytearray(packer.pack(219, 5, 1, *payload))
    return encode_checksum(msg_bytes)


def encode_impedance_reset(position, velocity):
    """ All DOM PVI command with impedance 'magic number' causing torque zeroing

    This command is for use with impedance mode, but the impedance value is omitted in lieu of the
    'magic number' which is interpreted by the Limb Controller to reset the toque values of the hand


    @param position: 27 by 1 numpy array of joint angular position in radians
    @param velocity: 27 by 1 numpy array of joint angular velocities
    @return: Python string of encoded bytes
    """

    magic_impedance = [40.0] * mpl.NUM_UPPER_ARM_JOINTS + [15.6288] * mpl.NUM_HAND_JOINTS
    return encode_position_velocity_impedance_command(position, velocity, magic_impedance)


def encode_cmd_state_limb_idle():
    """ Encode limb idle command state
    Send limb to idle; this is a lower power mode that still maintains position

    @return: Python string
    """
    return encode_checksum(bytearray([3, 0, 10, 10]))


def encode_cmd_state_limb_soft_reset():
    """ Encode limb 'soft rest' command state
    Send limb to soft reset.  This will allow back driving joints. Active state resumes when next command received

    @return:
    """
    return encode_checksum(bytearray([3, 0, 11, 11]))


def encode_checksum(payload):
    """
    Adds the expected checksum to the formatted message bytes

    @param payload: Python string of bytes of length N to be transmitted
    @return: Python string of bytes with length N + 1 with checksum appended
    """
    # add on the checksum
    payload.append(sum(payload) % 256)
    return payload
