import socket
import time

import numpy as np

import utilities

__version__ = "1.0.0"


def emulate_myo_udp_exe(destination='//127.0.0.1:10001'):
    """
    Emulate MyoUdp.exe outputs for testing

    Example Usage within python:
        import os
        os.chdir(r"C:\git\minivie\python\minivie")
        import Inputs.MyoUdp
        Inputs.MyoUdp.EmulateMyoUdpExe() # CTRL+C to END

    Example Usage from command prompt:
        python Myo.py -SIMEXE

    MyoUdp.exe Data packet information:
    Data packet size is 48 bytes.
         uchar values encoding:
         Bytes 0-7: int8 [8] emgSamples
         Bytes 8-23: float [4]  quaternion (rotation)
         Bytes 24-35: float [3] accelerometer data, in units of g
         Bytes 36-47: float [3] gyroscope data, in units of deg / s

    Revisions:
        2016OCT23 Armiger: Created
        2016OCT24 Armiger: changed randint behavior for python 27 compatibility

    """

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP

    print('Running MyoUdp.exe Emulator to ' + destination)
    try:
        while True:
            # generate random bytes matching the size of MyoUdp.exe streaming
            # Future: generate orientation data in valid range

            # dtyp of randint is invalid in numpt 1.8, python 2.7:
            # data = np.random.randint(255, size=48, dtype='i1')
            # TypeError: randint() got an unexpected keyword argument 'dtype'

            data = np.random.randint(255, size=48).astype('int8')
            sock.sendto(data.tostring(), utilities.get_address(destination))
            time.sleep(0.005)  # 200Hz
    except KeyError:
        pass
    print('Closing MyoUdp.exe Emulator')
    sock.close()


def emulate_myo_unix(destination='//127.0.0.1:15001'):
    """
    Emulate Myo UNIX streaming outputs for testing

    Example Usage within python:
        import os
        os.chdir(r"C:\git\minivie\python\minivie")
        from inputs.myo import myo_sim
        myo_sim.emulate_myo_unix() # CTRL+C to END

    Example Usage from command prompt:
        python -m inputs.myo.myo_sim.py -SIM_UNIX

    Revisions:
        2016OCT23 Armiger: Created
        2016OCT24 Armiger: changed randint behavior for python 27 compatibility

    """

    # Multicast Demo
    # ANY = "0.0.0.0"
    # SENDERPORT = 32000
    # MCAST_ADDR = "239.255.1.1"
    # MCAST_PORT = 1600
    #
    # sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM,
    #                      socket.IPPROTO_UDP)
    # sock.bind((ANY, SENDERPORT))
    # sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 255)
    # sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    #
    # address = (MCAST_ADDR, MCAST_PORT)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP
    address = utilities.get_address(destination)
    counter = 0
    print('Running MyoUdp.exe Emulator to ' + destination)
    try:
        while True:
            counter += 1

            # generate random bytes matching the size of MyoUdp.exe streaming
            # Future: generate orientation data in valid range
            vals = np.random.randint(255, size=16).astype('uint8')
            sock.sendto(vals.tostring(), address)
            vals = np.random.randint(255, size=16).astype('uint8')
            sock.sendto(vals.tostring(), address)

            # simulate a battery level
            if counter > 500: # delay frequency of battery levels
                # send battery levels
                sock.sendto(bytes([98]), address)
                counter = 0

            # create synthetic orientation data
            # rpy = np.random.rand(90, size=3)
            # rpy = [30.0, 45.0, 15.0]
            # q = [1.0, 0.0, 0.0, 0.0] * MYOHW_ORIENTATION_SCALE

            # np.array(q, dtype=int16).tostring
            vals = np.random.randint(255, size=20).astype('uint8')
            sock.sendto(vals.tostring(), address)

            time.sleep(0.02)  # 200Hz

    except KeyError:
        pass
    print('Closing Myo Emulator')
    sock.close()


def main():
    """Parse command line arguments into argparse model.

    Command-line arguments:
    -h or --help -- output help text describing command-line arguments.

    """
    import sys
    import argparse

    # Parameters:
    parser = argparse.ArgumentParser(description='MyoUdp: Read from myo and stream UDP.')
    parser.add_argument('-e', '--SIM_EXE', help='Run MyoUdp.exe EMG Simulator', action='store_true')
    parser.add_argument('-u', '--SIM_UNIX', help='Run UNIX EMG Simulator', action='store_true')
    parser.add_argument('-a', '--ADDRESS', help=r'Destination Address (e.g. //127.0.0.1:15001)',
                        default='//127.0.0.1:15001')
    args = parser.parse_args()

    if args.SIM_EXE:
        emulate_myo_udp_exe(args.ADDRESS)
    elif args.SIM_UNIX:
        emulate_myo_unix(args.ADDRESS)
    else:
        # No Action
        print(sys.argv[0] + " Version: " + __version__)


if __name__ == '__main__':
    main()
