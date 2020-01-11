#!/usr/bin/env python3
# test script for MPL interface
#
# This test function is intended to be operated from the command line to bring up a short menu allow communication
# tests with the MPL.
#
# Revisions:
# 2016OCT05 Armiger: Created

# Python 3:
import time
import numpy as np
from builtins import input
import logging
import threading
import tornado.ioloop

import utilities.sys_cmd
from mpl.open_nfu_sink import NfuSink
# from mpl.unity import UnityUdp
import mpl.roc as roc


# Show menu
print(30 * '-')
print("   M P L - T E S T ")
print(30 * '-')
print("1. Ping: Limb system and router using OS")
print("2. MPL Wrist")
print("3. MPL Grasps")
print("4. MPL Heartbeats")
print("5. MPL Range of Motion (All Joints)")
print(30 * '-')
print("0. Exit")
print(30 * '-')
print(30 * '-')
print("NOTE: Ensure no other MPL control processes are running. E.g. sudo systemctl stop mpl_run_www.service")
print(30 * '-')

# Get input
choice = input('Enter selection : ')
assert isinstance(choice, str)  # native str on Py2 and Py3

# Convert string to int type
choice = int(choice)

AA = -0.3
EL = 0
armTestStart = [0, AA, 0, EL, 0, 0, 0]

#udp_params = dict(hostname="192.168.7.2", udp_telem_port=9028, udp_command_port=9027)
udp_params = dict(hostname="localhost", udp_telem_port=9028, udp_command_port=9027)

# Take action as per selected menu-option #
if choice == 0:
    pass
if choice == 1:
    print("Starting ping...")
    print(60 * '-')
    print("NOTE: MPL/NFU and host MAC addresses must be on the approved access list in /etc/iptables/rules.v4")
    print(60 * '-')

    result = 0
    while not result:
        result = utilities.sys_cmd.ping('192.168.8.1')
    print(result)

elif choice == 2:
    print("Starting MPL Wrist...")
    # hSink = UnityUdp()  commands on cmd_port, telem 9028
    hSink = NfuSink()
    hSink.mpl_connection_check = True
    hSink.connect(local_address='//0.0.0.0:9028', remote_address='//127.0.0.1:9027')

    # start network services
    thread = threading.Thread(target=tornado.ioloop.IOLoop.instance().start, name='WebThread')
    thread.start()

    hSink.send_joint_angles([0, AA, 0, EL, -0.7, -0.5, -0.5])
    time.sleep(1.0)
    AA = -0.25
    hSink.send_joint_angles([0, AA, 0, EL + 0.55, -0.7, -0.5, -0.5])
    time.sleep(1.0)
    hSink.send_joint_angles([0, AA, 0, EL, 0.7, 0.5, 0.5])
    time.sleep(1.0)
    hSink.send_joint_angles(armTestStart)
    hSink.close()

elif choice == 3:
    print("Starting MPL Grasps...")
    # hSink = UnityUdp()
    hSink = NfuSink()
    hSink.mpl_connection_check = True
    hSink.connect(local_address='//0.0.0.0:9028', remote_address='//127.0.0.1:9027')

    # start network services
    thread = threading.Thread(target=tornado.ioloop.IOLoop.instance().start, name='WebThread')
    thread.start()

    # Read ROC Table
    filename = "../../WrRocDefaults.xml"
    rocTable = roc.read_roc_table(filename)

    for iRoc in [2, 4, 5, 7, 15]:
        numOpenSteps = 50
        numWaitSteps = 50
        numCloseSteps = 50

        mplAngles = np.zeros(27)
        mplAngles[1] = -0.3
        mplAngles[3] = EL + 0.05

        rocElem = roc.get_roc_id(rocTable, iRoc)

        graspVal = np.concatenate(
            (np.linspace(0, 1, numOpenSteps), np.ones(numWaitSteps), np.linspace(1, 0, numCloseSteps)))
        for iVal in graspVal:
            print('Entry #{}, RocId={}, {} {:6.1f} Pct'.format(iRoc, rocElem.id, rocElem.name, iVal * 100))
            mplAngles[rocElem.joints] = roc.get_roc_values(rocElem, iVal)
            hSink.send_joint_angles(mplAngles)
            time.sleep(0.02)
    hSink.close()

elif choice == 4:
    logging.basicConfig(level=logging.INFO)
    hSink = NfuSink()
    hSink.mpl_connection_check = True
    hSink.connect(local_address='//0.0.0.0:9028', remote_address='//127.0.0.1:9027')

    # start network services
    thread = threading.Thread(target=tornado.ioloop.IOLoop.instance().start, name='WebThread')
    thread.start()

    while True:
        try:
            print(hSink.get_status_msg())
            time.sleep(1)
        except KeyboardInterrupt:
            break

    hSink.close()

elif choice == 5:
    print("Starting MPL Range of Motion Test...")

    # Read ROM File
    filename = "../tests/mpl_motion_arm5.csv"
    with open(filename) as f:
        mpl_angles = f.read().splitlines()

    # hSink = UnityUdp()
    # By selecting a different port for telemetry, this can run while run_www is open
    hSink = NfuUdp(**udp_params)
    hSink.connect()
    time.sleep(1.5)
    # hSink.wait_for_connection()
    hSink.enable_impedance = 1
    hSink.reset_impedance = 0

    i_loop = 0
    while 1:
        i_loop += 1
        print('Running.  Starting Loop: {}'.format(i_loop))

        try:
            for s in mpl_angles:
                angles = [float(x) for x in s.split(',')]
                # msg = 'JointCmd: ' + ','.join(['%.1f' % elem for elem in angles])
                # print(msg)
                hSink.active_connection = True
                hSink.send_joint_angles(angles)
                time.sleep(0.02)
        except KeyboardInterrupt:
            break

    hSink.close()

else:  # default
    print("Exiting...")
