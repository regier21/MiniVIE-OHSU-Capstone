# take in a vie object and perform a control assessment

import asyncio
import logging
import time
import numpy as np
import h5py
import datetime as dtime
from mpl import JointEnum as MplId
import random
from controls.plant import class_map
from abc import ABCMeta, abstractmethod
import os.path


class AssessmentInterface(object):
    __metaclass__ = ABCMeta

    def __init__(self):
        pass

    # All methods with this decorator must be overloaded
    @abstractmethod
    def start_assessment(self):
        pass

    @abstractmethod
    def save_results(self):
        pass


class MotionTester(AssessmentInterface):
    # Method to perform motion tester assessments, communicate results to user

    # Class Assessment - Elbow Extension - 6.0/8 Correct Classifications, 23.0 Misclassifications
    # Motion Incomplete
    # INFO:root:Class Assessment - Elbow Extension - 6.0/8 Correct Classifications, 23.0 Misclassifications
    # INFO:root:Motion Incomplete
    # Motion name No Motion does not exist
    # TODO: ERROR:root:must be str, not NoneType
    # [MotionTester] [ERROR]  must be str, not NoneType
    # Saved MOTION_TESTER_LOG
    # Motion Tester Assessment Completed.

    def __init__(self, vie, trainer):

        # Initialize superclass
        super(AssessmentInterface, self).__init__()

        self.vie = vie
        self.trainer = trainer
        # self.thread = None  # deprecated for asyncio tasks
        self.task = None
        self.filename = 'MOTION_TESTER_LOG'
        self.file_ext = '.hdf5'
        self.reset()

        # Assessment parameters
        self.repetitions = 3  # Assessment repetitions
        self.max_correct = 10  # Number of correct classifications required to complete assessment
        self.timeout = 5.0  # Time before assessment times out

        # Initialize data storage lists
        self.target_class = []
        self.class_decision = []
        self.correct_decision = []
        self.time_stamp = []
        self.class_id_to_test = []
        self.data = []  # List of dicts

        # Kill flag
        # self.stop_assessment = False  # deprecated for asyncio task.cancel()

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
            if 'StartMotionTester' in cmd_data:
                # parse parameter values
                self.repetitions = int(round(float(cmd_data.split('-')[1])))
                self.timeout = float(cmd_data.split('-')[2])
                self.max_correct = int(round(float(cmd_data.split('-')[3])))

                if self.task is not None:
                    print('Already Started!!!')
                else:
                    self.task = asyncio.create_task(self.run_assessment())

            elif 'StopMotionTester' in cmd_data:
                self.send_status('Assessment aborted')
                if self.task is not None:
                    self.cancel_task()
            else:
                logging.info('Unknown motion tester command: ' + cmd_data)

    def cancel_task(self):
        """
        Cancel the currently running assessment task and cleanup.  This is NOT acceptable to do if task completed
        :return:
        """
        self.task.cancel()
        self.clear_task()

    def clear_task(self):
        """
        Delete the task from the object history.  This is acceptable to do either with a completed of cancelled task
        :return:
        """
        self.task = None

    async def run_assessment(self):
        try:
            await self.start_assessment()
            self.clear_task()
        except asyncio.CancelledError:
            raise

    async def start_assessment(self):
        # Method to assess all trained classes

        # The stop_assessment is a lambda function that will kill the thread once turned to True

        # Clear assessment data from previous assessments
        self.reset()

        # Update progress bar to 0
        self.update_gui_progress(0, 1)

        # Determine which classes should be trained
        all_class_names = self.vie.TrainingData.motion_names
        totals = self.vie.TrainingData.get_totals()
        trained_classes = [all_class_names[i] for i, e in enumerate(totals) if e != 0]

        # Remove no movement class
        if 'No Movement' in trained_classes:
            trained_classes.remove('No Movement')

        # pause limb during test
        self.vie.pause('All', True)
        self.send_status('Holdout')

        for i_rep in range(self.repetitions):  # Right now, assessing each class 3 times
            self.send_status('New Motion Tester Assessment Trial')
            for i, i_class in enumerate(trained_classes):
                # Initiate new class storage "struct"
                self.class_id_to_test.append(all_class_names.index(i_class))
                self.data.append({'targetClass': [], 'classDecision': [], 'voteDecision': [], 'emgFrames': []})

                # Assess class
                is_complete = await self.assess_class(i_class)

                if is_complete:
                    self.send_status('Motion Completed!')
                else:
                    self.send_status('Motion Incomplete')

                # Update progress bar
                self.update_gui_progress(i + 1 + i_rep*len(trained_classes), self.repetitions*len(trained_classes))

        # Reset GUI to no-motion image
        image_name = self.vie.TrainingData.get_motion_image('No Movement')
        self.trainer.send_message("motion_test_setup", image_name)
        # Save out stored data
        self.save_results()
        # Send status
        self.send_status('Motion Tester Assessment Completed.')
        # Unlock limb
        self.vie.pause('All', False)

    async def assess_class(self, class_name):
        # Method to assess a single class, display/save results for viewing

        # Update GUI image
        image_name = self.vie.TrainingData.get_motion_image(class_name)
        if image_name:
            self.trainer.send_message("motion_test_setup", image_name)

        # # Give countdown
        # countdown_time = 3;
        # dt = 1;
        # tvec = np.linspace(countdown_time,0,int(round(countdown_time/dt)+1))
        # for t in tvec:
        #     self.send_status('Testing Class - ' + class_name + ' - In ' + str(t) + ' Seconds)')
        #     time.sleep(dt)

        # Start once user goes to no-movement, then first non- no movement classification is given
        self.send_status('Testing Class - <b>' + class_name + '</b> <br>Return to "No Movement" and Begin')
        entered_no_movement = False
        while True:
            current_class = self.vie.output['decision']
            if current_class == 'No Movement':
                entered_no_movement = True
            if (current_class != 'No Movement') and (current_class != 'None') and entered_no_movement:
                break
            await asyncio.sleep(0.1)  # Necessary to sleep, otherwise output gets backlogged

        dt = 0.1  # 100ms RIC JAMA
        timeout = self.timeout
        time_begin = time.time()
        max_correct = self.max_correct
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
            self.send_status('Testing Class -  <b>' + class_name + '</b> <br>' + str(num_correct) + '/' +
                             str(max_correct) + ' Correct Classifications')

            # update data for output
            self.add_data(class_name, current_class)

            # determine if move is completed
            if num_correct >= max_correct:
                move_complete = True

            # Sleep before next assessed classification
            await asyncio.sleep(dt)
            time_elapsed = time.time() - time_begin

        # Motion completed, update status
        self.send_status('Class Assessment - ' + class_name + ' - ' + str(num_correct) + '/' + str(max_correct) + ' Correct Classifications, ' + str(num_wrong) + ' Misclassifications')

        return move_complete

    def update_gui_progress(self,  num_correct, max_correct):
        # Method to update the progress bar in the web-based GUI
        self.trainer.send_message("motion_test_update", str(int(round((float(num_correct)/max_correct)*100))))

    def send_status(self, status):
        # Method to send more verbose status updates for command line users and logging purposes
        print(status)
        logging.info(status)
        self.trainer.send_message("motion_test_status", status)

    def add_data(self, class_name_to_test, current_class):
        # Method to add data following each assessment

        # TODO: Better fix for this, should 'None' be an available classification in first place?
        if current_class == 'None':
            current_class = 'No Movement'

        # Find ids
        # class_id_to_test = self.vie.TrainingData.motion_names.index(class_name_to_test)
        # dict_id = self.class_id_to_test.index(class_id_to_test)
        current_class_id = self.vie.TrainingData.motion_names.index(current_class)

        # Append to data dicts
        self.data[-1]['targetClass'].append(class_name_to_test)
        self.data[-1]['classDecision'].append(current_class_id)
        # TODO: Update the following metadata
        #self.data[class_id_to_test]['voteDecision'].append([])
        #self.data[class_id_to_test]['emgFrames'].append([])

    def save_results(self):
        # Method to save out compiled assessment results in h5df formal, following full assessment
        # Mimics struct hierarchy of MATLAB motion tester results

        t = dtime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        f = t + '_' + self.filename + self.file_ext
        counter = 1
        while os.path.exists(f):
            f = t + '_' + self.filename + str(counter) + self.file_ext
            counter=counter+1

        h5 = h5py.File(f, 'w')
        g1 = h5.create_group('TrialLog')
        g1.attrs['description'] = t + 'Motion Tester Data'
        encoded = [a.encode('utf8') for a in self.vie.TrainingData.motion_names]
        g1.create_dataset('AllClassNames', shape=(len(encoded), 1), data=encoded)
        g1.create_dataset('ClassIdToTest', data=self.class_id_to_test, shape=(len(self.class_id_to_test), 1))
        g1.create_dataset('MaxCorrect', data=[self.max_correct], shape=(1, 1))
        g1.create_dataset('Timeout', data=[self.timeout], shape=(1, 1))

        g2 = g1.create_group('Data')

        for i,d in enumerate(self.data):
            g3 = g2.create_group(str(i))
            encoded = [a.encode('utf8') for a in d['targetClass']]
            g3.create_dataset('targetClass', shape=(len(encoded), 1), data=encoded)
            g3.create_dataset('classDecision', shape=(len(d['classDecision']), 1), data=d['classDecision'])

        h5.close()
        self.send_status('Saved ' + self.filename)

        # Clear data for next assessment
        self.reset()


class TargetAchievementControl(AssessmentInterface):
    # Method to perform TAC assessments, with three conditions
    # 1) 1 joint assessment, all other joints locked
    # 2) 1 joint assessment, all other joints free
    # 3) 3-joint assessment

    def __init__(self, vie, trainer):

        # Initialize superclass
        super(AssessmentInterface, self).__init__()

        self.vie = vie
        self.trainer = trainer
        self._condition = None  # 1,2, or 3, corresponding to standard TAC conditions
        # self.thread = None  # deprecated for asyncio tasks
        self.task = None
        self.filename = 'TAC1_LOG'
        self.file_ext = '.hdf5'

        self.assessment_type = 'TAC1'  # TAC1 or TAC3 currently implemented

        # Default assessment parameters
        self.target_error_degree = 5.0  # Allowable error for degree-based joints
        self.target_error_percent = 5.0  # Allowable error for percent-based grasps (I.e., grasps)
        self.repetitions = 2  # Repetitions per joint
        self.timeout = 45.0  # Time before assessment failed
        self.dwell_time = 2.0  # Time required within target position

        # Data storage
        self.target_joint = []  # Joint or grasp id
        self.target_position = []  # Target position in degrees (joints) or percentage (grasps)
        self.target_error = []
        self.position_time_history = []  # Plant position
        self.intent_time_history = []  # Intent at each test during assessment
        self.time_history = []  # time list
        self.completion_time = []  # completion time
        self.lower_limit = []
        self.upper_limit = []
        self.data = []  # list of dicts

        # Kill flag
        # self.stop_assessment = False  # deprecated for asyncio task.cancel()

    def reset(self):
        # Method to reset data storage items
        self.target_joint = []  # Joint or grasp id
        self.target_position = []  # Target position in degrees (joints) or percentage (grasps)
        self.target_error = []  # Deviation from target position that is allowed
        self.position_time_history = []  # Plant position
        self.intent_time_history = []  # Intent at each test during assessment
        self.time_history = []  # time list
        self.completion_time = []  # completion time
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
            if 'StartTAC1' in cmd_data:
                # parse parameter values
                self.assessment_type = 'TAC1'
                self._condition = 1
                self.repetitions = int(round(float(cmd_data.split('-')[1])))
                self.timeout = float(cmd_data.split('-')[2])
                self.dwell_time = float(cmd_data.split('-')[3])
                self.target_error_degree = float(cmd_data.split('-')[4])
                self.target_error_percent = float(cmd_data.split('-')[5])

                if self.task is None:
                    # Only start if no tasks already running
                    self.task = asyncio.create_task(self.run_assessment())

            elif 'StartTAC3' in cmd_data:
                # parse parameter values
                self.assessment_type = 'TAC3'
                self._condition = 3
                self.repetitions = int(round(float(cmd_data.split('-')[1])))
                self.timeout = float(cmd_data.split('-')[2])
                self.dwell_time = float(cmd_data.split('-')[3])
                self.target_error_degree = float(cmd_data.split('-')[4])
                self.target_error_percent = float(cmd_data.split('-')[5])

                if self.task is None:
                    # Only start if no tasks already running
                    self.task = asyncio.create_task(self.run_assessment())

            elif 'StopTAC' in cmd_data:
                self.send_status('Assessment aborted')
                if self.task is not None:
                    self.cancel_task()
            else:
                logging.info('Unknown TAC command: ' + cmd_data)

    def cancel_task(self):
        """
        Cancel the currently running assessment task and cleanup.  This is NOT acceptable to do if task completed
        :return:
        """
        self.task.cancel()
        self.clear_task()

    def clear_task(self):
        """
        Delete the task from the object history.  This is acceptable to do either with a completed of cancelled task
        :return:
        """
        self.task = None

    async def run_assessment(self):
        try:
            await self.start_assessment()
            # print('TAC done - clearing task')
            self.clear_task()
        except asyncio.CancelledError:
            # print('TAC Cancelled')
            raise

    async def start_assessment(self):
        # condition should be
        # 1 - TAC1
        # 2 - TAC2
        # 3 - TAC3

        # Set condition specific parameters
        self.filename = self.assessment_type + '_LOG'  # e.g. TAC1_LOG or TAC3_LOG

        # Determine which classes have been trained
        all_class_names = self.vie.TrainingData.motion_names
        totals = self.vie.TrainingData.get_totals()
        trained_classes = [all_class_names[i] for i, e in enumerate(totals) if e != 0]

        # Remove no movement class
        if 'No Movement' in trained_classes:
            trained_classes.remove('No Movement')

        # Determine which joints/grasps have been trained
        # TAC is based on a joint being fully trained in both directions, and on having a grasp and Hand Open trained
        # the class_map is used to map motion names (e.g. Wrist Pronation) to the corresponding Joint and Direction
        # (e.g. WRIST_ROT (+) )
        # Not grasps have no joint ID so will be skipped here
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
        from collections import Counter
        d = Counter(all_joint_ids)
        trained_joints = []
        for joint, count in d.items():
            if count > 1 and joint is not None:
                trained_joints.append(joint)

        # We can assess any grasp, as long as 'Hand Open' has been trained
        if 'Hand Open' in trained_classes:
            trained_grasps = [x for x in all_grasp_ids if x is not None]
        else:
            trained_grasps = []

        # Identify which joints we will assess
        # TODO:Add interface to determine which joints/grasps to assess
        joints_to_assess = []
        is_grasp = []
        # For TAC1, we will just assess all joints and/or grasps independently
        if self._condition == 1:
            joints_to_assess = list(trained_joints) + list(trained_grasps)
            is_grasp = [False]*len(trained_joints) + [True]*len(trained_grasps)

        # For TAC3, we will require simultaneous assess elbow, one wrist motion, and one grasp
        if self._condition == 3:
            # First verify elbow is trained
            if 'ELBOW' in trained_joints:
                joints_to_assess.append('ELBOW')
                is_grasp.append(False)
            else:
                self.send_status('ELBOW must be fully trained to begin TAC3. Stopping assessment.')
                self.cancel_task()

            # Choose wrist motion, right now will just pick the first one
            if 'WRIST_ROT' in trained_joints:
                joints_to_assess.append('WRIST_ROT')
                is_grasp.append(False)
            elif 'WRIST_AB' in trained_joints:
                joints_to_assess.append('WRIST_AB_AD')
                is_grasp.append(False)
            elif 'WRIST_FE' in trained_joints:
                joints_to_assess.append('WRIST_FE')
                is_grasp.append(False)
            else:
                self.send_status('One WRIST DOF must be fully trained to begin TAC3. Stopping assessment.')
                self.cancel_task()

            # Choose grasp
            if trained_grasps:
                # Will just assess first trained grasp for now
                joints_to_assess.append(list(trained_grasps)[0])
                is_grasp.append(True)
            else:
                msg = 'One GRASP as well as Hand Open must be fully trained to begin TAC3. Stopping assessment.'
                self.send_status(msg)
                self.cancel_task()

        # Assess joints and grasps
        for i_rep in range(self.repetitions):
            self.send_status('New TAC Assessment Trial')

            # For TAC1, assess one joint at a time
            if self._condition == 1:
                for i, joint in enumerate(joints_to_assess):
                    await self.assess_joint([joint], [is_grasp[i]])  # Need to be passed in as list

            # For TAC3, assess all joints simultaneously
            if self._condition == 3:
                await self.assess_joint(joints_to_assess, is_grasp)

        self.send_status('TAC Assessment Completed')
        self.save_results()

    async def assess_joint(self, joint_name_list, is_grasp_list=[False]):

        # Set TAC parameters
        dt = 0.2  # Time between assessment queries
        dwell_time = self.dwell_time  # Time in target before pass
        timeout = self.timeout
        move_complete = False  # Flag for move completion

        # Set joint-specific parameters
        target_error_list = []  # Error range allowed
        lower_limit_list = []  # Lower limit for joint
        upper_limit_list = []  # Upper limit for joint
        target_position_list = []  # Target joint positions
        for i, joint_name in enumerate(joint_name_list):
            is_grasp = is_grasp_list[i]
            if is_grasp:
                target_error_list.append(float(self.target_error_percent))
                lower_limit_list.append(float(0))
                upper_limit_list.append(float(100))
                # Set target joint angle
                # TAC set an angle 75 degrees away from current position, for now we will just pick random number
                # within limits.  Will ensure this position is at least 25% of total range from current position,
                # and not at edge of limit
                current_position = self.vie.Plant.grasp_position * 100.0
                time_begin = time.time()
                while True:
                    target_position = float(random.randint(int(round(lower_limit_list[-1])), int(round(upper_limit_list[-1]))))
                    condition1 = abs(current_position - target_position) > 0.25*(float(upper_limit_list[-1]) - float(lower_limit_list[-1]))
                    condition2 = abs(target_position - float(upper_limit_list[-1])) > target_error_list[-1]
                    condition3 = abs(target_position - float(lower_limit_list[-1])) > target_error_list[-1]
                    if (condition1 and condition2 and condition3) or ((time.time() - time_begin) > 5):
                        break
                target_position_list.append(target_position)

            else:
                target_error_list.append(float(self.target_error_degree))
                mpl_id = getattr(MplId, joint_name)
                lower_limit_list.append(np.rad2deg(float(self.vie.Plant.lower_limit[mpl_id])))
                upper_limit_list.append(np.rad2deg(float(self.vie.Plant.upper_limit[mpl_id])))
                # Set target joint angle
                # TAC set an angle 75 degrees away from current position, for now we wil just pick random number
                # within limits
                # Will ensure this position is at least 25% of total range away from current position, and not at
                # edge of limit
                current_position = np.rad2deg(self.vie.Plant.joint_position[mpl_id])
                time_begin = time.time()
                while True:
                    target_position = float(random.randint(int(round(lower_limit_list[-1])), int(round(upper_limit_list[-1]))))
                    condition1 = abs(current_position - target_position) > 0.25 * (float(upper_limit_list[-1]) - float(lower_limit_list[-1]))
                    condition2 = abs(target_position - float(upper_limit_list[-1])) > target_error_list[-1]
                    condition3 = abs(target_position - float(lower_limit_list[-1])) > target_error_list[-1]
                    if (condition1 and condition2 and condition3) or ((time.time() - time_begin) > 5):
                        break
                target_position_list.append(target_position)

        # Set data storage properties
        self.target_joint = joint_name_list
        self.target_position = target_position_list
        self.target_error = target_error_list
        self.lower_limit = lower_limit_list
        self.upper_limit = upper_limit_list
        self.position_time_history = np.empty([0, len(joint_name_list)])  # Plant position
        self.intent_time_history = []
        self.completion_time = -1.0
        self.time_history = []  # time list
        position_row = np.empty([1, len(joint_name_list)])

        # Update web gui
        self.update_gui_joint_target(self._condition)

        time_elapsed = 0.0
        time_in_target = 0.0
        joint_in_target = [False] * len(joint_name_list)
        start_sequence = True
        entered_no_movement = False

        if self.assessment_type == 'TAC3':
            prefix = 'Testing Joint(s):<br>'
        else:
            prefix = 'Testing Joint:<br>'
        msg = prefix + '<b>' + ', '.join(joint_name_list) + '</b><br>Return to "No Movement" to Begin'
        self.send_status(msg)
        while not move_complete and (time_elapsed < timeout):

            # Loop through each joint we are assessing simultaneously
            for i, joint_name in enumerate(joint_name_list):

                is_grasp = is_grasp_list[i]
                target_position = target_position_list[i]
                target_error = target_error_list[i]

                # Get current joint position
                if is_grasp:
                    position = self.vie.Plant.grasp_position*100.0
                else:
                    mpl_id = getattr(MplId, joint_name)
                    position = np.rad2deg(self.vie.Plant.joint_position[mpl_id])

                # If within +- target_error of target_position, then flag this joint as within target
                if (position < (target_position + target_error)) and (position > (target_position - target_error)):
                    joint_in_target[i] = True
                    if is_grasp:
                        # Need an additional check if we are checking a grasp to make sure it is correct grasp that is
                        # falling within grasp percentage
                        if joint_name is not self.vie.Plant.grasp_id:
                            joint_in_target[i] = False
                else:
                    joint_in_target[i] = False

                # Update data storage properties for this joint
                position_row[0, i] = position

            # Get current intent
            current_class = self.vie.output['decision']

            #  Update data storage properties for all joints
            self.position_time_history = np.append(self.position_time_history, position_row, axis=0)  # Plant position
            self.intent_time_history.append(current_class)  # Intent at each test during assessment
            self.time_history.append(time_elapsed)  # time list

            # Update web gui
            self.update_gui_joint(self._condition)

            # Start once user goes to no-movement, then first non- no movement classification is given
            if start_sequence:
                if current_class == 'No Movement':
                    entered_no_movement = True
                if (current_class != 'No Movement') and (current_class != 'None') and entered_no_movement:
                    start_sequence = False
                    # First non-no movement command received.  Begin assessment
                    time_begin = time.time()

                # TODO: add a start condition for grasps that hand is all the way open
                # time.sleep(dt)  # Necessary to sleep, otherwise get output gets backlogged
                await asyncio.sleep(dt)
                continue

            # Output status
            if self.assessment_type == 'TAC3':
                prefix = 'Testing Joint(s):<br>'
            else:
                prefix = 'Testing Joint:<br>'
            # msg = prefix + '<b>' + ', '.join(joint_name_list) \
            #     + '</b><br>Dwell Time - ' + "{0:0.1f}".format(time_in_target) \
            #     + '<br>Elapsed Time - ' + "{0:0.1f}".format(time_elapsed)
            msg = prefix + '<b>' + ', '.join(joint_name_list) \
                + '</b><br>Dwell Time - ' + "{0:0.1f}".format(time_in_target) \
                + '<br>Elapsed Time - ' + "{0:0.1f}".format(time_elapsed) \
                + '<br>Current Grasp - ' + self.vie.Plant.grasp_id
            self.send_status(msg)

            # Commented out, too cluttered for now, could potentially allow this output with verbose option
            # self.send_status('Testing Joint - ' + joint_name + ' - Current Position - ' + str(position) +
            #                 ' - Target Position - ' + str(target_position) +
            #                 ' - Time in Target - ' + str(time_in_target))

            # If all joints in target, increment time_in_target, otherwise reset to 0
            if False in joint_in_target:
                time_in_target = 0.0
            else:
                time_in_target += dt

            # Exit criteria
            if time_in_target >= dwell_time:
                move_complete = True
                self.completion_time = time_elapsed  # completion time1

            # Sleep before next assessed classification
            time_elapsed = time.time() - time_begin
            await asyncio.sleep(dt)
            # time.sleep(dt)

        # Add data from current joint assessment
        self.add_data()

        self.send_status(', '.join(joint_name_list) + ' Assessment Completed')

        return move_complete

    def update_gui_joint(self, num_dof):
        # Will set joint bar display on web interface

        # format message:
        payload = str(num_dof)
        for joint_num in range(num_dof):
            # pull from position_time_history so we are displaying what is being recorded/tested
            raw_pos = self.position_time_history[-1, joint_num]
            normalized_joint_position = (raw_pos - self.lower_limit[joint_num]) / (
                        self.upper_limit[joint_num] - self.lower_limit[joint_num]) * 100

            payload += ",{bar:.2f}".format(
                id=joint_num, bar=normalized_joint_position)
        self.trainer.send_message("TAC_update", payload)

    def update_gui_joint_target(self, num_dof):
        # Will set joint bar display on web interface

        # format message:
        payload = str(num_dof)
        for joint_num in range(num_dof):
            normalized_target_position = (self.target_position[joint_num] - self.lower_limit[joint_num]) / (
                    self.upper_limit[joint_num] - self.lower_limit[joint_num]) * 100.0

            normalized_target_error = (self.target_error[joint_num]) / (
                    self.upper_limit[joint_num] - self.lower_limit[joint_num]) * 100.0

            payload += ",{name},{target:.2f},{error:.2f}".format(
                name=self.target_joint[joint_num], target=normalized_target_position, error=normalized_target_error)
        self.trainer.send_message("TAC_setup", payload)

    def send_status(self, status):
        # Method to send more verbose status updates for command line users and logging purposes
        logging.info(status)
        self.trainer.send_message("TAC_status", status)

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
        f = t + '_' + self.filename + self.file_ext
        counter = 1
        while os.path.exists(f):
            f = t + '_' + self.filename + str(counter) + self.file_ext
            counter = counter + 1
        h5 = h5py.File(f, 'w')
        g1 = h5.create_group('Data')
        g1.attrs['description'] = t + 'TAC' + str(self._condition)+ ' Data'

        for i, d in enumerate(self.data):
            g2 = g1.create_group('Trial ' + str(i+1))
            encoded = [a.encode('utf8') for a in d['target_joint']] # Need to encode strings
            g2.create_dataset('target_joint', shape=(len(encoded), 1), data=encoded)
            g2.create_dataset('target_position', data=d['target_position'], shape=(len(d['target_position']), 1))
            g2.create_dataset('target_error', data=d['target_error'], shape=(len(d['target_error']), 1))
            encoded = [a.encode('utf8') for a in d['intent_time_history']]
            g2.create_dataset('intent_time_history', shape=(1, len(d['intent_time_history'])), data=encoded)
            g2.create_dataset('position_time_history', shape=d['position_time_history'].shape[::-1],
                              data=d['position_time_history'].transpose())
            g2.create_dataset('time_history', shape=(1, len(d['time_history'])),
                              data=d['time_history'])
            g2.create_dataset('completion_time', data=[d['completion_time']], shape=(1,1))

        h5.close()
        self.send_status('Saved ' + self.filename)

        # Clear data for next assessment
        self.reset()
