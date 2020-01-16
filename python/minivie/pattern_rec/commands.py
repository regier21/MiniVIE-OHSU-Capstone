from mpl import JointEnum as MplId


def class_map(class_name):
    """ Map a pattern recognition class name to a joint command

     The objective of this function is to decide how to interpret a class decision
     as a movement action.

     return JointId, Direction, IsGrasp, Grasp

       'No Movement' is not necessary in dict_Joint with '.get default return
     JointId, Direction = self.Joint.get(class_name,[ [], 0 ])
    """
    class_info = {'IsGrasp': None, 'JointId': None, 'Direction': 0, 'GraspId': None}

    # Map classes to joint id and direction of motion
    # Class Name: IsGrasp, JointId, Direction, GraspId
    class_lookup = {
        'No Movement': [False, None, 0, None],
        'Shoulder Flexion': [False, MplId.SHOULDER_FE, +1, None],
        'Shoulder Extension': [False, MplId.SHOULDER_FE, -1, None],
        'Shoulder Adduction': [False, MplId.SHOULDER_AB_AD, +1, None],
        'Shoulder Abduction': [False, MplId.SHOULDER_AB_AD, -1, None],
        'Humeral Internal Rotation': [False, MplId.HUMERAL_ROT, +1, None],
        'Humeral External Rotation': [False, MplId.HUMERAL_ROT, -1, None],
        'Elbow Flexion': [False, MplId.ELBOW, +1, None],
        'Elbow Extension': [False, MplId.ELBOW, -1, None],
        'Wrist Rotate In': [False, MplId.WRIST_ROT, +1, None],
        'Wrist Rotate Out': [False, MplId.WRIST_ROT, -1, None],
        'Wrist Adduction': [False, MplId.WRIST_AB_AD, +1, None],
        'Wrist Abduction': [False, MplId.WRIST_AB_AD, -1, None],
        'Wrist Flex In': [False, MplId.WRIST_FE, +1, None],
        'Wrist Extend Out': [False, MplId.WRIST_FE, -1, None],
        'Hand Open': [True, None, -1, None],
        # 'Spherical Grasp': [True, None, +1, 'Spherical Grasp'],
        # 'Tip Grasp': [True, None, +1, 'Tip Grasp'],
    }

    # rather than listing out all grasps, just list the arm motions and assume others are grasps

    if class_name in class_lookup:
        class_info['IsGrasp'], class_info['JointId'], class_info['Direction'], class_info['GraspId'] = class_lookup[
            class_name]
    else:
        # Assume this is a grasp in the ROC table
        # logging.warning('Unmatched class name {}'.format(class_name))
        class_info['IsGrasp'] = True
        class_info['JointId'] = None
        class_info['Direction'] = +1
        class_info['GraspId'] = class_name

    return class_info
