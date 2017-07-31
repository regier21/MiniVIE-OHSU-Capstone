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
    parser.add_argument('-ru', '--Right_Upper', help='Right Upper', action='store_true')
    parser.add_argument('-lu', '--Left_Upper', help='Left Upper', action='store_true')
    parser.add_argument('-rb', '--Right_Both', help='Right Both', action='store_true')
    parser.add_argument('-lb', '--Left_Both', help='Left Both', action='store_true')
    parser.add_argument('-rd', '--Right_Daq', help='Right Daq', action='store_true')
    parser.add_argument('-ld', '--Left_Daq', help='Left Daq', action='store_true')
    args = parser.parse_args()

    if args.Right_Upper:
        ID = "MPL Embedded Right"
        trainingDataArm = "_Right"
        unityArm = "right"
        source = [myo.MyoUdp(source='//0.0.0.0:15001')]

    elif args.Left_Upper:
        ID = "MPL Embedded Left"
        trainingDataArm = "_Left"
        unityArm = "left"
        source = [myo.MyoUdp(source='//0.0.0.0:15003')]

    elif args.Right_Both:
        ID = "MPL Embedded Right"
        trainingDataArm = "_Right"
        unityArm = "right"
        source = [myo.MyoUdp(source='//0.0.0.0:15001'),myo.MyoUdp(source='//0.0.0.0:15002')]

    elif args.Left_Both:
        ID = "MPL Embedded Left"
        trainingDataArm = "_Left"
        unityArm = "left"
        source = [myo.MyoUdp(source='//0.0.0.0:15003'),myo.MyoUdp(source='//0.0.0.0:15004')]

    elif args.Right_Daq:
        ID = "MPL Embedded Right"
        trainingDataArm = "_Right"
        unityArm = "right"
        source = [daqEMGDevice.DaqEMGDevice('Dev2/ai0:7')]

    elif args.Left_Daq:
        ID = "MPL Embedded Left"
        trainingDataArm = "_Left"
        unityArm = "left"
        source = [daqEMGDevice.DaqEMGDevice('Dev3/ai0:7')]

    else:
        ID = "MPL Embedded Right"
        trainingDataArm = "_Right"
        unityArm = "right"
        source = [myo.MyoUdp(source='//0.0.0.0:15001')]


    # setup logging
    user_config.setup_file_logging(prefix='VMPL_')

    # Setup MPL scenario
    vie = mpl_nfu.setup(source, trainingDataArm, unityArm)

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
