# take in a vie object and perform a control assessment

import logging
import threading
import time
import numpy as np
import h5py
import datetime as dtime
import math
import time
from mpl import JointEnum as MplId


class MotionTester(object):
# Method to perform motion tester assessments, communicate results to user

    def __init__(self, vie, trainer):
        self.vie = vie
        self.trainer = trainer
        self.thread = None
        self.filename = 'MOTION_TESTER_LOG'
        self.file_ext = '.hdf5'
        self.reset()

        # Initialize data storage lists
        self.target_class = []
        self.class_decision = []
        self.correct_decision = []
        self.time_stamp = []
        self.class_id_to_test = []
        self.data = []  # List of dicts

    def reset(self):
        # Method to reset all stored data

        self.target_class = []
        self.class_decision = []
        self.correct_decision = []
        self.time_stamp = []
        self.class_id_to_test = []
        self.data = []  # List of dicts

    def command_string(self, value):
        """
        Commands are strings with the following format:

        [CMD_TYPE]:[CMD_VALUE]

        [CMD_TYPE] options are:
            Cmd - Indicates the cmd_value is a command word. Options are:
                StartAssessment
        """

        logging.info('Received new motion tester command:' + value)
        parsed = value.split(':')
        if not len(parsed) == 2:
            logging.warning('Invalid motion tester command: ' + value)
            return
        else:
            cmd_type = parsed[0]
            cmd_data = parsed[1]

        if cmd_type == 'Cmd':
            if cmd_data == 'StartMotionTester':
                self.thread = threading.Thread(target=self.start_assessment)
                self.thread.name = 'MotionTester'
                self.thread.start()
            else:
                logging.info('Unknown motion tester command: ' + cmd_data)

    def start_assessment(self, num_trials=3):
        # Method to assess all trained classes

        # Clear assessment data from previous assessments
        self.reset()

        # Update progress bar to 0
        self.update_gui_progress(0, 1)

        # Determine which classes should be trained
        all_class_names = self.vie.TrainingData.motion_names;
        totals = self.vie.TrainingData.get_totals()
        trained_classes = [all_class_names[i] for i, e in enumerate(totals) if e != 0]
        # Remove no movement class
        if 'No Movement' in trained_classes: trained_classes.remove('No Movement')

        # pause limb during test
        self.vie.pause('All', True)
        self.send_status('Holdout')

        for i_rep in range(num_trials):  # Right now, assessing each class 3 times
            self.send_status('New Assessment Trial')
            for i,i_class in enumerate(trained_classes):
                if i_rep == 0:
                    # Initiate new class storage "struct"
                    self.class_id_to_test.append(all_class_names.index(i_class))
                    self.data.append({'targetClass': [], 'classDecision': [], 'voteDecision': [], 'emgFrames': []})

                # Assess class
                is_complete = self.assess_class(i_class)
                if is_complete:
                    self.send_status('Motion Completed!')
                else:
                    self.send_status('Motion Incomplete')

                # Update progress bar
                self.update_gui_progress(i + 1 + i_rep*len(trained_classes), num_trials*len(trained_classes))

        # Reset GUI to no-motion image
        image_name = self.vie.TrainingData.get_motion_image('No Motion')
        self.trainer.send_message("strMotionTesterImage", image_name)
        # Save out stored data
        self.save_results()
        # Send status
        self.send_status('Assessment Completed.')
        # Unlock limb
        self.vie.pause('All', False)

    def assess_class(self, class_name):
        # Method to assess a single class, display/save results for viewing

        # Update GUI image
        image_name = self.vie.TrainingData.get_motion_image(class_name)
        if image_name:
            self.trainer.send_message("strMotionTesterImage", image_name)

        # # Give countdown
        # countdown_time = 3;
        # dt = 1;
        # tvec = np.linspace(countdown_time,0,int(round(countdown_time/dt)+1))
        # for t in tvec:
        #     self.send_status('Testing Class - ' + class_name + ' - In ' + str(t) + ' Seconds)')
        #     time.sleep(dt)

        # Start once user goes to no-movement, then first non- no movement classification is given
        self.send_status('Testing Class - ' + class_name + ' - Return to "No Movement" and Begin')
        entered_no_movement = False
        while True:
            current_class = self.vie.output['decision']
            if current_class == 'No Movement': entered_no_movement = True
            if (current_class != 'No Movement') and (current_class != 'None') and entered_no_movement: break

        dt = 0.1  # 100ms RIC JAMA
        timeout = 5
        time_begin = time.time()
        max_correct = 10
        move_complete = False
        num_correct = 0
        num_wrong = 0
        time_elapsed = 0.0

        while not move_complete and (time_elapsed < timeout):

            # get the class
            current_class = self.vie.output['decision']

            if current_class == class_name:
                num_correct += 1

            else:
                num_wrong += 1

            # print status
            self.send_status('Testing Class - ' + class_name + ' - ' + str(num_correct) + '/' + str(max_correct) + ' Correct Classifications')

            # update data for output
            self.add_data(class_name,current_class)

            # determine if move is completed
            if num_correct >= max_correct:
                move_complete = True

            # Sleep before next assessed classification
            time.sleep(dt)
            time_elapsed = time.time() - time_begin

        # Motion completed, update status
        self.send_status('Class Assessment - ' + class_name + ' - ' + str(num_correct) + '/' + str(max_correct) + ' Correct Classifications, ' + str(num_wrong) + ' Misclassifications')

        return move_complete

    def update_gui_progress(self,  num_correct, max_correct):
        # Method to update the progress bar in the web-based GUI
        self.trainer.send_message("strMotionTesterProgress", str(int(round((float(num_correct)/max_correct)*100))))

    def send_status(self, status):
        # Method to send more verbose status updates for command line users and logging purposes
        print(status)
        logging.info(status)
        self.trainer.send_message("strMotionTester", status)

    def add_data(self, class_name_to_test, current_class):
        # Method to add data following each assessment

        # TODO: Better fix for this, should 'None' be an available classification in first place?
        if current_class is 'None':
            current_class = 'No Movement'

        # Find ids
        class_id_to_test = self.vie.TrainingData.motion_names.index(class_name_to_test)
        dict_id = self.class_id_to_test.index(class_id_to_test)
        current_class_id = self.vie.TrainingData.motion_names.index(current_class)

        # Append to data dicts
        self.data[dict_id]['targetClass'].append(class_name_to_test)
        self.data[dict_id]['classDecision'].append(current_class_id)
        # TODO: Update the following metadata
        #self.data[class_id_to_test]['voteDecision'].append([])
        #self.data[class_id_to_test]['emgFrames'].append([])

    def save_results(self):
        # Method to save out compiled assessment results in h5df formal, following full assessment
        # Mimics struct hierarchy of MATLAB motion tester results

        t = dtime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        h5 = h5py.File(self.filename + self.file_ext, 'w')
        g1 = h5.create_group('TrialLog')
        g1.attrs['description'] = t + 'Motion Tester Data'
        encoded = [a.encode('utf8') for a in self.vie.TrainingData.motion_names]
        g1.create_dataset('AllClassNames', shape=(len(encoded), 1), data=encoded)
        g1.create_dataset('ClassIdToTest', self.class_id_to_test)

        g2 = g1.create_group('Data')

        for d in self.data:
            g3 = g2.create_group(d['targetClass'][0])
            encoded = [a.encode('utf8') for a in d['targetClass']]
            g3.create_dataset('targetClass', shape=(len(encoded), 1), data=encoded)
            g3.create_dataset('classDecision', shape=(len(d['classDecision']), 1), data=d['classDecision'])

        h5.close()
        self.send_status('Saved ' + self.filename)


class TargetAchievementControl(object):
    def __init__(self, vie, trainer):
        self.vie = vie
        self.trainer = trainer

    def command_string(self, value):
        """
        Commands are strings with the following format:

        [CMD_TYPE]:[CMD_VALUE]

        [CMD_TYPE] options are:
            Cmd - Indicates the cmd_value is a command word. Options are:
                StartAssessment
        """

        logging.info('Received new  TAC command:' + value)
        parsed = value.split(':')
        if not len(parsed) == 2:
            logging.warning('Invalid TAC command: ' + value)
            return
        else:
            cmd_type = parsed[0]
            cmd_data = parsed[1]

        if cmd_type == 'Cmd':
            if cmd_data == 'StartAssessment':
                self.thread = threading.Thread(target=self.start_assessment)
                self.thread.name = 'Assessement'
                self.thread.start()

    def start_assessment(self):

        timeout = 6.0 #seconds
        dt = 0.05 # seconds
        time_end = 0
        # start timer

        time_begin = time.time()
        self.vie.pause('All',True)
        print('Holdout')
        time.sleep(timeout)
        self.vie.pause('All',False)

        time_begin = time.time()
        while (time_end - time_begin) < timeout:

            arm = self.vie.Plant.JointPosition[MplId.ELBOW] * 180 / math.pi
            hand = self.vie.Plant.GraspPosition
            decision = self.vie.output['decision']
            print('Elbow: {0:6.2f}  Grasp: {1:6.2f} Class:{2}'.format(arm, hand, decision))

            time_end = time.time()
            time.sleep(dt)

        print('Done')