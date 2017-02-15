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
import collections
import random
from controls.plant import class_map

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
            self.send_status('New Motion Tester Assessment Trial')
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
        self.send_status('Motion Tester Assessment Completed.')
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
        timeout = 5.0
        time_begin = time.time()
        max_correct = 10.0
        move_complete = False
        num_correct = 0.0
        num_wrong = 0.0
        time_elapsed = 0.0

        while not move_complete and (time_elapsed < timeout):

            # get the class
            current_class = self.vie.output['decision']

            if current_class == class_name:
                num_correct += 1.0

            else:
                num_wrong += 1.0

            # print status
            self.send_status('Testing Class - ' + class_name + ' - ' + str(num_correct) + '/' +
                             str(max_correct) + ' Correct Classifications')

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
        h5 = h5py.File(t + '_' + self.filename + self.file_ext, 'w')
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
    # Method to perform TAC assessments, with three conditions
    # 1) 1 joint assessment, all other joints locked
    # 2) 1 joint assessment, all other joints free
    # 3) 3-joint assessment

    def __init__(self, vie, trainer):
        self.vie = vie
        self.trainer = trainer
        self._condition = None # 1,2, or 3, corresponding to standard TAC conditions
        self.thread = None
        self.filename = 'TAC_LOG'
        self.file_ext = '.hdf5'

        # Data storage
        self.target_joint = [] # Joint or grasp id
        self.target_position = [] # Target position in degrees (joints) or percentage (grasps)
        self.target_error = []
        self.position_time_history = [] # Plant position
        self.intent_time_history = [] # Intent at each test during assessment
        self.time_history = [] # time list
        self.completion_time = [] # completion time1
        self.lower_limit = []
        self.upper_limit = []
        self.data = []

    def reset(self):
        # Method to reset data storage items
        self.target_joint = []  # Joint or grasp id
        self.target_position = []  # Target position in degrees (joints) or percentage (grasps)
        self.target_error = [] # Deviation from target position that is allowed
        self.position_time_history = []  # Plant position
        self.intent_time_history = []  # Intent at each test during assessment
        self.time_history = []  # time list
        self.completion_time = []  # completion time1
        self.lower_limit = []
        self.upper_limit = []
        self.data = []

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
            if cmd_data == 'StartTAC':
                self.thread = threading.Thread(target=self.start_assessment(condition=1))
                self.thread.name = 'TAC'
                self.thread.start()

    def start_assessment(self, condition=1):

        # Set condition
        self._condition = condition

        # Set number of trials from TAC article
        if condition==1 or condition==2:
            num_trials = 2
        else:
            num_trials = 1

        # Determine which classes have been trained
        all_class_names = self.vie.TrainingData.motion_names;
        totals = self.vie.TrainingData.get_totals()
        trained_classes = [all_class_names[i] for i, e in enumerate(totals) if e != 0]

        # Remove no movement class
        if 'No Movement' in trained_classes: trained_classes.remove('No Movement')

        # Determine which joints/grasps have been trained
        all_joint_ids = []
        all_grasp_ids = []
        for class_name in trained_classes:
            this_class_info = class_map(class_name)
            try:
                all_joint_ids.append(this_class_info['JointId'].name)
            except AttributeError:
                all_joint_ids.append(None)
            all_grasp_ids.append(this_class_info['GraspId'])

        # We will only assess joints where both directions have been trained
        # Logic used here will be simply to see if there are two instances of given joint id in all_joint_ids
        trained_joints = set([x for x in all_joint_ids if (all_joint_ids.count(x) > 1) and (x is not None)])

        # We can assess any grasp, as long as 'Hand Open' has been trained
        if 'Hand Open' in trained_classes:
            trained_grasps = set([x for x in all_grasp_ids if x is not None])
        else:
            trained_grasps = []

        # Group trained_joints/trained_grasps into groups of 3 for conditions 2 and 3
        # Alternatively, could we just feed all trained joints plus one grasp?
        # TODO

        for i_rep in range(num_trials):
            self.send_status('New TAC Assessment Trial')
            # Assess joints and grasps
            for i_joint in trained_joints:
                is_complete = self.assess_joint(i_joint)
            for i_grasp in trained_grasps:
                is_complete = self.assess_joint(i_grasp, is_grasp=True)

        self.send_status('TAC Assessment Completed')
        self.save_results()

    def assess_joint(self, joint_name, is_grasp=False):

        # Set TAC parameters
        dt = 0.1
        if self._condition == 1 or self._condition == 2: timeout = float(15)
        else: timeout = float(45)
        if is_grasp:target_error = float(5)
        else: target_error = float(5)
        if is_grasp: min_start_difference = float(25)
        else: min_start_difference = float(25)
        dwell_time = float(2)
        move_complete = False

        #  Pause other joints
        #if self._condition==1:
            # TODO: How to pause only specific joints?
            # self.vie.pause('All', True)

        # Get joint limits
        if is_grasp:
            lower_limit = float(0)
            upper_limit = float(100)
        else:
            mplId = getattr(MplId, joint_name)
            lower_limit = self.vie.Plant.lowerLimit[mplId] * 180.0 / math.pi
            upper_limit = self.vie.Plant.upperLimit[mplId] * 180.0 / math.pi

        # Set target joint angle
        # TAC set an angle 75 degrees away from current position, for now we wil just pick random number within limits
        # Will ensure this position is at least 25 degrees away from current position
        while True:
            self.send_status('Determining target position.')
            target_position = float(random.randint(lower_limit, upper_limit))
            if is_grasp:
                current_position = self.vie.Plant.GraspPosition*100.0
            else:
                current_position = self.vie.Plant.JointPosition[mplId] * 180.0 / math.pi
            if abs(current_position-target_position) > min_start_difference: break

        # Set data storage properties
        self.target_joint = joint_name  # Joint or grasp id
        self.target_position = target_position  # Target position in degrees (joints) or percentage (grasps)
        self.target_error = target_error
        self.lower_limit = lower_limit
        self.upper_limit = upper_limit

        # Update web gui
        self.update_gui_joint1_target()

        # Start once user goes to no-movement, then first non- no movement classification is given
        self.send_status('Testing Joint - ' + joint_name + ' - Return to "No Movement" and Begin')
        entered_no_movement = False
        while True:
            current_class = self.vie.output['decision']
            if current_class == 'No Movement': entered_no_movement = True
            if (current_class != 'No Movement') and (current_class != 'None') and entered_no_movement: break

        # Start timer
        time_begin = time.time()
        time_elapsed = 0.0
        time_in_target = 0.0

        while not move_complete and (time_elapsed < timeout):

            # Get current joint position
            if is_grasp:
                position = self.vie.Plant.GraspPosition*100.0
            else:
                position = self.vie.Plant.JointPosition[mplId] * 180.0 / math.pi

            # Get current intent
            current_class = self.vie.output['decision']

            #  Update data storage properties
            self.position_time_history.append(position)  # Plant position
            self.intent_time_history.append(current_class)  # Intent at each test during assessment
            self.time_history.append(time_elapsed)  # time list

            # Update web gui
            self.update_gui_joint1()

            # If within +- target_error of target_position, increment time_in_target, othwerwise reset to 0
            if (position < (target_position + target_error)) and (position > (target_position - target_error)):
                time_in_target += dt
            else:
                time_in_target = 0.0

            # Output status
            self.send_status('Testing Joint - ' + joint_name + ' - Current Position - ' + str(position) +
                             ' - Target Position - ' + str(target_position) +
                             ' - Time in Target - '  + str(time_in_target))

            # Exit criteria
            if time_in_target>=dwell_time:
                move_complete = True
                self.completion_time = time_elapsed  # completion time1

            # Sleep before next assessed classification
            time.sleep(dt)
            time_elapsed = time.time() - time_begin

        # Add data from current joint assessmet
        self.add_data()

        self.send_status(joint_name + 'Assessment Completed')

        return move_complete

    def update_gui_joint1(self):
        # Will set joint bar display on web interface
        normalized_joint_position = (self.position_time_history[-1] - self.lower_limit)/(self.upper_limit - self.lower_limit) * 100
        self.trainer.send_message("strTACJoint1Bar", str(normalized_joint_position))

    def update_gui_joint1_target(self):
        # Will set joint bar display on web interface
        self.trainer.send_message("strTACJoint1Name", self.target_joint)
        normalized_target_position = (self.target_position - self.lower_limit) / (
        self.upper_limit - self.lower_limit) * 100.0
        normalized_target_error = (self.target_error) / (
        self.upper_limit - self.lower_limit) * 100.0
        self.trainer.send_message("strTACJoint1Error", str(normalized_target_error))
        self.trainer.send_message("strTACJoint1Target", str(normalized_target_position))

    def send_status(self, status):
        # Method to send more verbose status updates for command line users and logging purposes
        print(status)
        logging.info(status)
        self.trainer.send_message("strTAC", status)

    def add_data(self):
        # Method to add data from single jon assessment to overall output data block

        new_data_dict = {}
        new_data_dict['target_joint'] = self.target_joint
        new_data_dict['target_position'] = self.target_position
        new_data_dict['target_error'] = self.target_error
        new_data_dict['position_time_history'] = self.position_time_history
        new_data_dict['intent_time_history'] = self.intent_time_history
        new_data_dict['time_history'] = self.time_history
        new_data_dict['completion_time'] = self.completion_time
        new_data_dict['lower_limit'] = self.lower_limit
        new_data_dict['upper_limit'] = self.upper_limit

        self.data.append(new_data_dict)

    def save_results(self):
        # Method to save out compiled assessment results in h5df formal, following full assessment

        t = dtime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        h5 = h5py.File(t + '_' + self.filename + self.file_ext, 'w')
        g1 = h5.create_group('Data')
        g1.attrs['description'] = t + 'TAC Data'

        for i,d in enumerate(self.data):
            g2 = g1.create_group('Trial ' + str(i+1))
            encoded = [a.encode('utf8') for a in d['target_joint']] # Need to encode strings
            g2.create_dataset('target_joint', shape=(len(encoded), 1), data=encoded)
            g2.create_dataset('target_position', (d['target_position'],))  # Notice, for scalars have to make tuple
            g2.create_dataset('target_error', (d['target_error'],))
            encoded = [a.encode('utf8') for a in d['intent_time_history']]
            g2.create_dataset('intent_time_history', shape=(len(encoded), 1), data=encoded)
            g2.create_dataset('position_time_history', shape=(len(d['position_time_history']), 1),
                              data=d['position_time_history'])
            g2.create_dataset('time_history', shape=(len(d['time_history']), 1),
                              data=d['time_history'])
            g2.create_dataset('completion_time', (d['completion_time'],))

        h5.close()
        self.send_status('Saved ' + self.filename)
