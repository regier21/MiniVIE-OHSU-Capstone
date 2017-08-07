#!/usr/bin/env python
# test script for MPL interface
#
# This test function is intended to be operated from the command line to bring up a short menu allow communication
# tests with the MPL.
#
# Revisions:
# 2016OCT05 Armiger: Created

# Python 2 and 3:
import sys
import argparse
from utilities import user_config
import scenarios.mpl_nfu as mpl_nfu
from pattern_rec import training, assessment
from inputs import myo, daqEMGDevice


def main():
    # Parameters:
    parser = argparse.ArgumentParser(description='Run Unity.')
    parser.add_argument('-r', '--Right', help='Right Upper', action='store_true')
    parser.add_argument('-l', '--Left', help='Left Upper', action='store_true')
    parser.add_argument('-ae8', '--Above_ELbow_8_Channel', help='Right Both', action='store_true')
    parser.add_argument('-ae16', '--Above_ELbow_16_Channel', help='Left Both', action='store_true')
    parser.add_argument('-be', '--Below_Elbow', help='Right Daq', action='store_true')
    parser.add_argument('-d', '--DAQ', help='DAQ', action='store_true')
    parser.add_argument('-dc', '--Device_Name_and_Channels', help=r'Device Name and Channels',
                        default='Dev1/ai0:7')
    args = parser.parse_args()

    if args.Right:
        ID = "MPL Embedded Right"
        trainingDataArm = "_Right"
        unityArm = "right"
        Myo1 = '//0.0.0.0:15001'
        Myo2 = '//0.0.0.0:15002'

    elif args.Left:
        ID = "MPL Embedded Left"
        trainingDataArm = "_Left"
        unityArm = "left"
        Myo1 = '//0.0.0.0:15003'
        Myo2 = '//0.0.0.0:15004'

    else:
        ID = "MPL Embedded Right"
        trainingDataArm = "_Right"
        unityArm = "right"
        Myo1 = '//0.0.0.0:15001'
        Myo2 = '//0.0.0.0:15002'

    if args.Above_ELbow_8_Channel:
        shoulder = True
        elbow = False
        source = [myo.MyoUdp(source=Myo1)]

    elif args.Above_ELbow_16_Channel:
        shoulder = True
        elbow = False
        source = [myo.MyoUdp(source=Myo1),myo.MyoUdp(source=Myo2)]

    elif args.Below_Elbow:
        shoulder = True
        elbow = True
        source = [myo.MyoUdp(source=Myo1),myo.MyoUdp(source=Myo2)]

    elif args.DAQ:
        shoulder = False
        elbow = False
        source = [daqEMGDevice.DaqEMGDevice(args.Device_Name_and_Channels)]

    else:
        shoulder = True
        elbow = False
        source = [myo.MyoUdp(source=Myo1)]


    # setup logging
    user_config.setup_file_logging(prefix='VMPL_')

    # Setup MPL scenario
    vie = mpl_nfu.setup(source, trainingDataArm, unityArm, shoulder, elbow)

    # setup web interface
    vie.TrainingInterface = training.TrainingManagerSpacebrew()
    vie.TrainingInterface.setup(description="JHU/APL Embedded Controller", server="127.0.0.1", port=9000, id = ID)
    vie.TrainingInterface.add_message_handler(vie.command_string)

    # Setup Assessment
    tac = assessment.TargetAchievementControl(vie, vie.TrainingInterface)
    motion_test = assessment.MotionTester(vie, vie.TrainingInterface)
    vie.TrainingInterface.add_message_handler(motion_test.command_string)
    vie.TrainingInterface.add_message_handler(tac.command_string)

    mpl_nfu.run(vie)


if __name__ == '__main__':
    main()
