/* global blueimp, $ */

$(function () {
    'use strict';

    // Initialize the Gallery as image carousel:
    blueimp.Gallery([
        {
        title: 'No Movement',
        href:  'img_arm_motions/No_Movement.png',
        type: 'image/png',
        thumbnail: 'img_arm_motions/No_Movement.png'
        },
		{
        title: 'Shoulder Flexion',
        href:  'img_arm_motions/Shoulder_Flexion.png',
        type: 'image/png',
        thumbnail: 'img_arm_motions/Shoulder_Flexion.png'
        },
		{
        title: 'Shoulder Extension',
        href:  'img_arm_motions/Shoulder_Extension.png',
        type: 'image/png',
        thumbnail: 'img_arm_motions/Shoulder_Extension.png'
        },
		{
        title: 'Shoulder Adduction',
        href:  'img_arm_motions/Shoulder_Adduction.png',
        type: 'image/png',
        thumbnail: 'img_arm_motions/Shoulder_Adduction.png'
        },
		{
        title: 'Shoulder Abduction',
        href:  'img_arm_motions/Shoulder_Abduction.png',
        type: 'image/png',
        thumbnail: 'img_arm_motions/Shoulder_Abduction.png'
        },
		{
        title: 'Humeral Internal Rotation',
        href:  'img_arm_motions/Humeral_Internal_Rotation.png',
        type: 'image/png',
        thumbnail: 'img_arm_motions/Humeral_Internal_Rotation.png'
        },
		{
        title: 'Humeral External Rotation',
        href:  'img_arm_motions/Humeral_External_Rotation.png',
        type: 'image/png',
        thumbnail: 'img_arm_motions/Humeral_External_Rotation.png'
        },
        {
        title: 'Elbow Flexion',
        href:  'img_arm_motions/Elbow_Flexion.png',
        type: 'image/png',
        thumbnail: 'img_arm_motions/Elbow_Flexion.png'
        },
        {
        title: 'Elbow Extension',
        href:  'img_arm_motions/Elbow_Extension.png',
        type: 'image/png',
        thumbnail: 'img_arm_motions/Elbow_Extension.png'
        },
        {
        title: 'Wrist Rotate In (Pronate)',
        href:  'img_arm_motions/Wrist_Rotate_In.png',
        type: 'image/png',
        thumbnail: 'img_arm_motions/Wrist_Rotate_In.png'
        },
        {
        title: 'Wrist Rotate Out (Supinate)',
        href:  'img_arm_motions/Wrist_Rotate_Out.png',
        type: 'image/png',
        thumbnail: 'img_arm_motions/Wrist_Rotate_Out.png'
        },
        {
        title: 'Wrist Flex In',
        href:  'img_arm_motions/Wrist_Flexion.png',
        type: 'image/png',
        thumbnail: 'img_arm_motions/Wrist_Flexion.png'
        },
        {
        title: 'Wrist Extend Out',
        href:  'img_arm_motions/Wrist_Extension.png',
        type: 'image/png',
        thumbnail: 'img_arm_motions/Wrist_Extension.png'
        },
        {
        title: 'Hand Open',
        href:  'img_grasps/Hand_Open.png',
        type: 'image/png',
        thumbnail: 'img_grasps/Hand_Open.png'
        },
        {
        title: 'Spherical Grasp',
        href:  'img_grasps/Spherical_Grasp.png',
        type: 'image/png',
        thumbnail: 'img_grasps/Spherical_Grasp.png'
        },
        {
        title: 'Tip Grasp',
        href:  'img_grasps/Tip_Grasp.png',
        type: 'image/png',
        thumbnail: 'img_grasps/Tip_Grasp.png'
        },
        {
        title: 'Three Finger Pinch',
        href:  'img_grasps/Tripod_Grasp.bmp',
        },
        {
        title: 'Lateral Grasp',
        href:  'img_grasps/Hook_Grasp.bmp',
        },
        {
        title: 'Cylindrical Grasp',
        href:  'img_grasps/Hook_Grasp.bmp',
        },
        {
        title: 'Point Grasp',
        href:  'img_grasps/Trigger_Grasp.png',
        }
    ], {
        container: '#blueimp-image-carousel',
        carousel: true,
        onslide: function (index, slide) {
                // Callback function executed on slide change.
                // Note these class commands must match those listed in pattern_rec\__init__.py class TrainingData
                switch(index) {
                case  0: sendCmd("Cls:No Movement"); break;
				case  1: sendCmd("Cls:Shoulder Flexion"); break;
				case  2: sendCmd("Cls:Shoulder Extension"); break;
				case  3: sendCmd("Cls:Shoulder Adduction"); break;
				case  4: sendCmd("Cls:Shoulder Abduction"); break;
				case  5: sendCmd("Cls:Humeral Internal Rotation"); break;
				case  6: sendCmd("Cls:Humeral External Rotation"); break;
                case  7: sendCmd("Cls:Elbow Flexion"); break;
                case  8: sendCmd("Cls:Elbow Extension"); break;
                case  9: sendCmd("Cls:Wrist Rotate In"); break;
                case 10: sendCmd("Cls:Wrist Rotate Out"); break;
                case 11: sendCmd("Cls:Wrist Flex In"); break;
                case 12: sendCmd("Cls:Wrist Extend Out"); break;
                case 13: sendCmd("Cls:Hand Open"); break;
                case 14: sendCmd("Cls:Spherical Grasp"); break;
                case 15: sendCmd("Cls:Tip Grasp"); break;
                case 16: sendCmd("Cls:Three Finger Pinch Grasp"); break;
                case 17: sendCmd("Cls:Lateral Grasp"); break;
                case 18: sendCmd("Cls:Cylindrical Grasp"); break;
                case 19: sendCmd("Cls:Point Grasp"); break;
                default: break;
                }
        }
    });
}); // function
