#!/usr/bin/env python
# test script for MPL interface
#
# This test function is intended to be operated from the command line to bring up a short menu allow communication
# tests with the MPL.
#
# Revisions:
# 2016OCT05 Armiger: Created

# Python 2 and 3:
from utilities import user_config
from scenarios import mpl_nfu
from mpl.open_nfu import NfuUdp
from pattern_rec import training, assessment


def main():

    # setup logging
    user_config.setup_file_logging(prefix='MPL_WWW_')

    # Setup MPL scenario
    vie = mpl_nfu.setup()
    vie.DataSink.close()  # close default unity sink

    # Replace sink with actual arm
    sink = NfuUdp(hostname="127.0.0.1", udp_telem_port=9028, udp_command_port=9027)
    sink.connect()
    vie.DataSink = sink

    # setup web interface
    vie.TrainingInterface = training.TrainingManagerSpacebrew()
    vie.TrainingInterface.setup(description="JHU/APL Embedded Controller", server="127.0.0.1", port=9000)
    vie.TrainingInterface.add_message_handler(vie.command_string)

    # Setup Assessment
    tac = assessment.TargetAchievementControl(vie, vie.TrainingInterface)
    motion_test = assessment.MotionTester(vie, vie.TrainingInterface)
    vie.TrainingInterface.add_message_handler(motion_test.command_string)
    vie.TrainingInterface.add_message_handler(tac.command_string)

    #setup features
    select_features = features_selected.Features_selected(vie)
    vie.TrainingInterface.add_message_handler(select_features.command_string)
    select_features.create_instance_list()

    mpl_nfu.run(vie)

if __name__ == '__main__':
    main()
