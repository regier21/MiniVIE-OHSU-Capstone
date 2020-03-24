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
from mpl.open_nfu.open_nfu_sink import NfuSink
from mpl.unity_asyncio import UnityUdp
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
if choice == '':
    choice = 0
else:
    choice = int(choice)

# Set the starting values for the test
AA = -0.3
EL = 0
armTestStart = [0, AA, 0, EL, 0, 0, 0]

# Take action as per selected menu-option #
if choice == 0:
    print("Exiting...")
    exit(0)
elif choice == 1:
    print("Starting ping...")
    print(60 * '-')
    print("NOTE: MPL/NFU and host MAC addresses must be on the approved access list in /etc/iptables/rules.v4")
    print(60 * '-')

    result = 0
    while not result:
        result = utilities.sys_cmd.ping('192.168.8.1')
    print(result)
else:
    # All remaining commands need a device connection
    logging.basicConfig(level=logging.DEBUG)
    vmpl = False
    if vmpl:
        hSink = UnityUdp(local_addr_str='//0.0.0.0:25009', remote_addr_str='//127.0.0.1:25000')
    else:
        hSink = NfuSink(local_addr_str='//0.0.0.0:9028', remote_addr_str='//127.0.0.1:9027')
    hSink.connect()

    # start network services
    thread = threading.Thread(target=tornado.ioloop.IOLoop.instance().start, name='WebThread')
    thread.start()

    connection_check = False
    while connection_check and not hSink.data_received():
        time.sleep(0.1)
        print(f'Waiting for valid percepts...')

    try:
        if choice == 2:
            print("Starting MPL Wrist...")
            hSink.send_joint_angles([0, AA, 0, EL, -0.7, -0.5, -0.5])
            time.sleep(1.0)
            AA = -0.25
            hSink.send_joint_angles([0, AA, 0, EL + 0.55, -0.7, -0.5, -0.5])
            time.sleep(1.0)
            hSink.send_joint_angles([0, AA, 0, EL, 0.7, 0.5, 0.5])
            time.sleep(1.0)
            hSink.send_joint_angles(armTestStart)

        elif choice == 3:
            print("Starting MPL Grasps...")
            # Read ROC Table
            filename = "mpl/#MPL_GEN3_ROC.xml"
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

        elif choice == 4:
            # get status message and print every few seconds
            while True:
                print(hSink.get_status_msg())
                time.sleep(1)

        elif choice == 5:
            print("Starting MPL Range of Motion Test...")
            # Read ROM File
            filename = "../tests/mpl_motion_arm5.csv"
            with open(filename) as f:
                mpl_angles = f.read().splitlines()
            time.sleep(1.5)
            hSink.enable_impedance = 1
            hSink.reset_impedance = 0

            i_loop = 0
            while 1:
                i_loop += 1
                print('Running.  Starting Loop: {}'.format(i_loop))
                for s in mpl_angles:
                    angles = [float(x) for x in s.split(',')]
                    # msg = 'JointCmd: ' + ','.join(['%.1f' % elem for elem in angles])
                    # print(msg)
                    hSink.active_connection = True
                    hSink.send_joint_angles(angles)
                    time.sleep(0.02)

    except KeyboardInterrupt:
        print("Got Keyboard Break")
        pass

    finally:
        hSink.close()
        tornado.ioloop.IOLoop.instance().stop()
        #thread.join()
        exit(0)
