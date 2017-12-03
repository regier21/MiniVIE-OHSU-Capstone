"""
Created on Tue Jan 23 10:17:58 2016

Initial pass at simulating MiniVIE processing using python so that this runs on an embedded device

@author: R. Armiger
"""

import sys
import time
from inputs import myo
import pattern_rec as pr
from mpl.unity import UnityUdp
from controls.plant import Plant, class_map
from scenarios import Scenario
from utilities import user_config

dt = 0.02  # seconds per loop.  50Hz update


def setup():
    """
    Create the building blocks of the MiniVIE

        SignalSource - source of EMG data
        SignalClassifier - algorithm to classify emg into 'intent'
        Plant - Perform forward integration and apply joint limits
        DataSink - output destination of command signals (e.g. real or virtual arm)
    """

    # Create data objects
    vie = Scenario()

    # attach inputs
    vie.attach_source([myo.MyoUdp(source='//0.0.0.0:15001'), myo.MyoUdp(source='//0.0.0.0:15002')])
    #vie.attach_source([myo.MyoUdp(source='//0.0.0.0:15001')])

    # Training Data holds data labels
    # training data manager
    vie.TrainingData = pr.TrainingData()
    vie.TrainingData.load()
    vie.TrainingData.num_channels = vie.num_channels

    # Setup feature extract and properties
    vie.FeatureExtract = pr.FeatureExtract()
    vie.FeatureExtract.zc_thresh = user_config.get_user_config_var('FeatureExtract.zcThreshold', 0.05)
    vie.FeatureExtract.ssc_thresh = user_config.get_user_config_var('FeatureExtract.sscThreshold', 0.05)
    vie.FeatureExtract.sample_rate = 200

    # Classifier parameters
    vie.SignalClassifier = pr.Classifier(vie.TrainingData)
    vie.SignalClassifier.fit()

    # Plant maintains current limb state (positions) during velocity control
    filename = user_config.get_user_config_var('rocTable', "../../WrRocDefaults.xml")
    vie.Plant = Plant(dt, filename)

    # Sink is output to outside world (in this case to VIE)
    # For MPL, this might be: real MPL/NFU, Virtual Arm, etc.
    vmpl = UnityUdp(remote_host="127.0.0.1")  # ("192.168.1.24")
    vie.DataSink = vmpl

    return vie


def run(vie):
    """
        Main function that involves setting up devices,
        looping at a fixed time interval, and performing cleanup
    """

    # setup main loop control
    print("")
    print("Running...")
    print("")
    sys.stdout.flush()

    # ##########################
    # Run the control loop
    # ##########################
    time_elapsed = 0.0
    while True:
        try:
            # Fixed rate loop.  get start time, run model, get end time; delay for duration
            time_begin = time.time()

            # Run the actual model
            output = vie.update()

            # send gui updates
            if vie.TrainingInterface is not None:
                msg = '<br>' + vie.DataSink.get_status_msg()  # Limb Status
                msg += ' ' + output['status']  # Classifier Status
                for src in vie.SignalSource:
                    msg += '<br>MYO:' + src.get_status_msg()
                msg += '<br>' + time.strftime("%c")

                # Forward status message (voltage, temp, etc) to mobile app
                vie.TrainingInterface.send_message("strStatus", msg)
                # Send classifier output to mobile app (e.g. Elbow Flexion)
                vie.TrainingInterface.send_message("strOutputMotion", output['decision'])
                # Send motion training status to mobile app (e.g. No Movement [70]
                msg = '{} [{:.0f}]'.format(vie.training_motion, round(vie.TrainingData.get_totals(vie.training_id), -1))
                vie.TrainingInterface.send_message("strTrainingMotion", msg)

            time_end = time.time()
            time_elapsed = time_end - time_begin
            if dt > time_elapsed:
                time.sleep(dt - time_elapsed)
            else:
                # print("Timing Overload: {}".format(time_elapsed))
                pass

            # print('{0} dt={1:6.3f}'.format(output['decision'],time_elapsed))

        except KeyboardInterrupt:
            break

    print("")
    print("Last time_elapsed was: ", time_elapsed)
    print("")
    print("Cleaning up...")
    print("")

    vie.close()