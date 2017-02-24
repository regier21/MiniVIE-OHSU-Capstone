from inputs import myo
from gui import signal_viewer
import threading

# Start myo udp stream
#thread = threading.Thread(target=myo.emulate_myo_udp_exe(destination='//127.0.0.1:10001'))
#thread.start()

# Read myo udp stream
source = myo.MyoUdp(source='//127.0.0.1:15001')
source.connect()

# Start signal viewer
s = signal_viewer.SignalViewer(signal_source=source)
