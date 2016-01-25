# Initial pass at simulating MiniVIE processing using python so that this runs on an embedded device
#
# Created 1/23/2016 Armiger

import math
import time
from MyoUdp import MyoUdp
from Plant import Plant
from UnityUdp import UnityUdp
import sys
import feature_extract

VERBOSE = 1
DEBUG = 1

dt = 0.02  # seconds per loop.  50Hz update

# Create data objects    
hPlant = Plant(dt)
hSink = UnityUdp("192.168.1.24")
hMyo = MyoUdp()#("192.168.1.3")

# Iteration counter
cnt = 0
try: 
    # setup main loop control
    print("Running...")
    sys.stdout.flush()
    
    while True: # main loop
        
        # Terminate after certain muber of steps
        cnt = cnt+1
        if DEBUG and cnt > 100:
            break

        timeBegin = time.time()
    
        f = feature_extract.feature_extract(hMyo.emg_buffer)
        
        hPlant.update()
        
        # perform joint update
        vals = hMyo.getAngles()
        hPlant.position[3] = vals[1] + math.pi/2
        
        # transmit output
        hSink.sendJointAngles(hPlant.position)
        
        if VERBOSE:
            print(("%8.4f" % hPlant.position[3], "%8.4f" % hPlant.position[4]))

        timeEnd = time.time()
        timeElapsed = timeEnd - timeBegin
        if dt > timeElapsed:
            time.sleep(dt-timeElapsed)
            
finally:
    print(hMyo.emg_buffer)
    print("Last timeElapsed was: ", timeElapsed)
    hSink.close()
    hMyo.close()
