#!/usr/bin/env python3
"""
Basic module defines the class to communicate with Open Bionics Brunel Hand controled via chestnut board
Communication is established with the chestnut board via USB
Joint position are sent via 'serial mode' to the chestnut
Documentation: https://openbionicslabs.com/obtutorials/beetroot-v1-0-firmware-user-guide-wydtx

Revisions:
2019OCT09 Rojas: Created

"""

# TODO: wring log information to the global log file
import time
import serial
import logging
import numpy as np

# Define the actuator class
class Brunel(object):
    def __init__(self):
        self.port_dir = '/dev/ttyACM1' 

        # Initial digit speed values
        self.speed = np.array([255,255,255,255])

        # Recomended Max/Min digit positions & speed values
        self.max_value = 973
        self.min_value = 50
        self.min_speed = 200

    def connect(self):

        # Establish Serial Connection
        self.ser = serial.Serial(
                port=self.port_dir,
                baudrate = 115200,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=0
        )

        # Read Initialization Information
        for count in range(0,80):
            x = self.ser.readline()

        # Configure Brunel Finger Speeds
        for x in range (0,len(self.speed)):
            speed_string = ""
            # Generate Speed Command (ex. F0 P0 S220)
            speed_string = "F" + str(x) + " P0 S" + str(int(self.speed[x])) + "**\r"
            # Write Speed Command
            self.ser.write(speed_string.encode())
        logging.info('Brunel Serial Opened') 

    def close(self):
        # Close Serial Connection
        self.ser.close()
        logging.info('Brunel Serial Closed')
        
    def send_joint_angles(self,joint_position,joint_velocity):
        # TODO: Ignore velocity.. or should we? digit speed command? 
        # Check to make sure that the values aren't outside of the MAX/MIN bounds
        for x in range(0,len(joint_position)):
            joint_position[x] = np.clip(joint_position, self.min_value, self.max_value)

        # New csv string line
        csv_string = ""

        # Package the first three positions into the string
        for x in range(0,len(joint_position)-1):
            csv_string = csv_string + str(int(joint_position[x])) + ","

        # Package fourth position into the string along with the cariage return
        csv_string = csv_string + str(int(joint_position[3])) + "**\r"
        
        # Write line
        self.ser.write(csv_string.encode())

def main():
    # Read some commnad from the user and send to the brunel
    print("Brunel Driver v0.1")
    
if __name__ == '__main__':
    main()

