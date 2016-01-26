# Initial pass at simulating MiniVIE processing using python so that this runs on an embedded device
#
# Created 1/23/2016 Armiger

import math
import time
from MyoUdp import MyoUdp
from Plant import Plant
from UnityUdp import UnityUdp
import sys
from feature_extract import feature_extract
import numpy as np

VERBOSE = 1

dt = 0.02  # seconds per loop.  50Hz update
    
# Create data objects    
hPlant = Plant(dt)
hSink = UnityUdp("192.168.1.24")
hMyo = MyoUdp()#("192.168.1.3")

W = np.genfromtxt("weights.txt", dtype=None)
C = np.genfromtxt("centers.txt", dtype=None)
with open("classes.txt") as f:
    classNames = f.read().splitlines()


# Iteration counter
cycleMax = 1000
cycleCnt = 0
timeElapsed = -1
try: 
    # setup main loop control
    print("Running...")
    sys.stdout.flush()
    
    while True: # main loop
        
        # Terminate after certain muber of steps
        cycleCnt = cycleCnt + 1
        if (cycleMax > 0) and cycleCnt > cycleMax:
            break

        timeBegin = time.time()
    
        f = feature_extract(hMyo.getData()*0.01)

        # Classify
        #   features[1,numChannels*NumFeatures] * Wg[numChannels*NumFeatures,numClasses] + Cg[1,numClasses]
        v = np.dot(f.T.reshape(1,32),W) + C
        classNum = v.argmax()

        # Move joints using classifier
        jointId,jointDir = hPlant.class_map(classNames[classNum])

        # Set joint velocities        
        hPlant.velocity[:hPlant.NUM_JOINTS] = [0.0] * hPlant.NUM_JOINTS        
        if jointId:
            for i in jointId:     
                hPlant.velocity[i] = jointDir

        hPlant.update()
                
        # perform joint motion update
        vals = hMyo.getAngles()
        hPlant.position[3] = vals[1] + math.pi/2

        
        # transmit output
        hSink.sendJointAngles(hPlant.position)
        
        if VERBOSE:
            #print(f[:1,:])
            print(("%8.4f" % hPlant.position[3], "%8.4f" % hPlant.position[4]), 'Class: %s' % classNames[classNum])

        timeEnd = time.time()
        timeElapsed = timeEnd - timeBegin
        if dt > timeElapsed:
            time.sleep(dt-timeElapsed)
        else:
            print("Timing Overload")
            
finally:
    print(hMyo.getData())
    print("Last timeElapsed was: ", timeElapsed)
    hSink.close()
    hMyo.close()