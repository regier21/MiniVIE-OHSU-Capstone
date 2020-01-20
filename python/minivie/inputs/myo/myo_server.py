#!/usr/bin/env python3
"""

This module is a linux based application for establishing myo armband streaming as a server via UDP
This relies on the bluepy module for linux

Typical use would be to set this up as a service on a linux system to continually scan
for myo armbands and stream data as available

Setting up service (on raspberry pi):

Create the service file
    $ sudo nano /etc/systemd/system/mpl_myo1.service

------------------------- mpl_myo1.service ------------------------------
[Unit]
Description=Myo Streamer
Requires=bluetooth.target
After=network.target bluetooth.target

[Service]
ExecStart=/usr/bin/python3.7 -u -m inputs.myo_server -x vmpl_user_config.xml
WorkingDirectory=/home/pi/git/minivie/python/minivie
StandardOutput=inherit
StandardError=inherit
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
------------------------- mpl_myo1.service ------------------------------

Enable the service

    $ sudo systemctl enable mpl_myo1.service

    Created symlink from /etc/systemd/system/multi-user.target.wants/mpl_myo1.service to /lib/systemd/system/mpl_myo1.service.

Start service and check status

    $ sudo systemctl start mpl_myo1.service
    $ sudo systemctl status mpl_myo1.service
    ● mpl_myo1.service - Myo Streamer
       Loaded: loaded (/etc/systemd/system/mpl_myo1.service; enabled; vendor preset: enabled)
       Active: active (running) since Thu 2018-08-16 03:54:51 UTC; 5s ago
     Main PID: 942 (python3)
       CGroup: /system.slice/mpl_myo1.service
               ├─942 /usr/bin/python3.7 -u -m inputs.myo_server -x vmpl_user_config.xml
               └─951 /usr/local/lib/python3.7/dist-packages/bluepy/bluepy-helper 0

    Aug 16 03:54:51 raspberrypi systemd[1]: Started Myo Streamer.






"""

import logging
import time
import socket
import struct
import binascii
from bluepy import btle

from utilities import user_config as uc
from utilities import get_address

__version__ = "1.1.0"


class MyoUdpServer(object):

    def __init__(self, data_logger=None, name='Myo'):
        import threading
        import subprocess

        # These are defaults but can be changed prior to connecting
        self.iface = 0
        self.mac_address = 'XX:XX:XX:XX:XX:XX'  # note this needs to be upper when finding handle to peripheral
        self.local_port = ('localhost', 16001)
        self.remote_port = ('localhost', 15001)

        # Setup file and console logging
        self.logger = data_logger
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = 0
        fh = logging.FileHandler(
            'EMG_MAC_{}_PORT_{}.log'.format(self.mac_address.replace(':', ''), self.remote_port[1]))
        fh.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setLevel(logging.WARNING)
        fh.setFormatter(logging.Formatter('%(created)f %(message)s'))
        ch.setFormatter(logging.Formatter("[%(threadName)-s] [%(levelname)-5.5s]  %(message)s"))
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)

        # Create data object handles
        self.peripheral = None
        self.sock = None
        send_udp = lambda data: self.sock.sendto(data, self.remote_port)
        self.delegate = MyoDelegate(send_udp, self.logger)
        self.thread = threading.Thread(target=self.run)
        self.thread.name = name

        self.logger.debug('Running subprocess command: hcitool dev')
        hci = 'hci' + str(self.iface)

        # Note that if running from startup, you should require bluetooth.target
        # to ensure that the bluetooth device is started
        output = subprocess.check_output(["hcitool", "dev"])
        if hci in output.decode('utf-8'):
            self.logger.info('Found device: ' + hci)
        else:
            self.logger.info('Device not found: ' + hci)

    def set_device_parameters(self):
        """function parameters"""
        # Notifications are unacknowledged, while indications are acknowledged. Notifications are therefore faster,
        # but less reliable.
        # Indication = 0x02; Notification = 0x01
        import struct

        write = self.peripheral.writeCharacteristic

        # Setup main streaming:
        write(0x12, struct.pack('<bb', 1, 0), 1)  # Un/subscribe from battery_level notifications
        write(0x24, struct.pack('<bb', 0, 0), 1)  # Un/subscribe from classifier indications
        write(0x1d, struct.pack('<bb', 1, 0), 1)  # Subscribe from imu notifications
        write(0x2c, struct.pack('<bb', 1, 0), 1)  # Subscribe to emg data0 notifications
        write(0x2f, struct.pack('<bb', 1, 0), 1)  # Subscribe to emg data1 notifications
        write(0x32, struct.pack('<bb', 1, 0), 1)  # Subscribe to emg data2 notifications
        write(0x35, struct.pack('<bb', 1, 0), 1)  # Subscribe to emg data3 notifications

        # note: Default values indicated by [] below:
        # [1]Should be for Classifier modes (00,01)
        # [1]Should be for IMU modes (00,01,02,03,04,05)
        # [1]Should be for EMG modes (00,02,03) **?can use value=1,4,5?
        # [2]Should be for payload size 03
        # [1]Should be for command 01
        # 200Hz (default) streaming
        #write(0x19, struct.pack('<bbbbb', 1, 3, 3, 1, 0), 1)  # Tell the myo we want EMG, IMU

        # Custom Streaming
        # Tell the myo we want EMG@300Hz, IMU@50Hz
        # write(0x19, struct.pack('<bbbbbhbbhb',2,0xa,3,1,0,0x12c,0,0,0x32,0x62), 1)

        # turn off sleep
        write(0x19, struct.pack('<bbb', 9, 1, 1), 1)

    def set_host_parameters(self):
        """
            Set parameters on the host adapter to allow low-latency streaming

            The command sets the Preferred Peripheral Connection Parameters (PPCP).  You can find summary Bluetooth
            information here: https://www.bluetooth.com/specifications/gatt/viewer?attributeXmlFile=org.bluetooth.
                characteristic.gap.peripheral_preferred_connection_parameters.xml

            Breaking down the command "sudo hcitool cmd 0x08 0x0013 40 00 06 00 06 00 00 00 90 01 00 00 07 00"

            the syntax for the 'cmd' option in 'hcitool' is:
                hcitool cmd <ogf> <ocf> [parameters]

                OGF: 0x08 "7.8 LE Controller Commands"

                OCF: 0x0013 "7.8.18 LE Connection Update Command"

            The significant command parameter bytes are "06 00 06 00 00 00 90 01" (0x0006, 0x0006, 0x0000, 0x0190)

            These translate to setting the min, and max Connection Interval to 0x0006=6;6*1.25ms=7.5ms, with no slave
                latency, and a 0x0190=400; 400*10ms=4s timeout.
            UPDATE: Added non-zero slave latency for robustness on DART board

            For more info, you can search for the OGF, OCF sections listed above in the Bluetooth Core 4.2 spec

        """
        import subprocess

        # get the connection information
        conn_raw = subprocess.check_output(['hcitool', 'con'])

        # parse to get our connection handle
        conn_lines = conn_raw.decode('utf-8').split('\n')

        handle_hex = None
        for conn in conn_lines:
            if conn.find(self.mac_address) > 0:
                start = 'handle'
                end = 'state'
                handle = int(conn.split(start)[1].split(end)[0])
                handle_hex = '{:04x}'.format(handle)
                self.logger.info('MAC: {} is handle {}'.format(self.mac_address, handle))

        if handle_hex is None:
            logging.error('Connection not found while setting adapter rate')
            return

        cmd_str = "hcitool -i hci{} cmd 0x08 0x0013 {} {} 06 00 06 00 00 00 90 01 01 00 07 00".format(
            self.iface, handle_hex[2:], handle_hex[:2])
        self.logger.info("Setting host adapter update rate: " + cmd_str)
        # subprocess.Popen(cmd_str, shell=True)
        subprocess.run(cmd_str, shell=True)

    def connect(self):
        # connect bluetooth
        # Make this a blocking call that overrides timeout to ensure connection order
        self.logger.info("Connecting to: " + self.mac_address)

        # This blocks until device is awake and connection established
        self.peripheral = btle.Peripheral()
        while True:
            try:
                self.peripheral.connect(self.mac_address, addrType=btle.ADDR_TYPE_PUBLIC, iface=self.iface)
                self.logger.info('Connection Successful')
                break
            except btle.BTLEException:
                self.logger.info('Timed out while connecting to device at address {}'.format(self.mac_address))

        self.set_device_parameters()

        # connect udp
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)
        self.sock.bind(self.local_port)

        # Assign event handler
        self.peripheral.withDelegate(self.delegate)

    def run(self):

        # start run loop
        status_msg_rate = 2.0  # seconds
        t_start = time.time()

        while True:
            t_now = time.time()
            t_elapsed = t_now - t_start

            #  waitForNotifications(timeout) Blocks until a notification is received from the peripheral
            # or until the given timeout (in seconds) has elapsed
            if not self.peripheral.waitForNotifications(1.0):
                self.logger.warning('Missed Myo notification.')
                self.peripheral.writeCharacteristic(0x19, struct.pack('5b', 1, 3, 3, 1, 0), 1)  # Tell the myo we want EMG, IMU

            if t_elapsed > status_msg_rate:
                rate_myo = self.delegate.counter['emg'] / t_elapsed
                rate_imu = self.delegate.counter['imu'] / t_elapsed
                status = "MAC: %s Port: %d EMG: %4.1f Hz IMU: %4.1f Hz BattEvts: %d" % (
                    self.mac_address, self.remote_port[1], rate_myo, rate_imu, self.delegate.counter['battery'])
                self.logger.info(status)

                # reset timer and rate counters
                t_start = t_now
                self.delegate.counter['emg'] = 0
                self.delegate.counter['imu'] = 0

            # Check for receive messages
            #
            # Define a simple protocol for commands to Myo
            #
            # Message ID:
            # 0 - Send vibration. Expects a 1 byte payload with duration
            # 1 - Send myo to Deep Sleep
            #
            # Send a single byte for vibration command with duration of 0-3 seconds
            # s.sendto(bytearray([2]),('localhost',16001))
            #
            # import socket
            # sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # sock.bind(('0.0.0.0', 9097))
            # sock.sendto(bytearray([0, 2]), ('127.0.0.1', 16001))
            # sock.sendto(bytearray([1]), ('127.0.0.1', 16001))

            try:
                data, address = self.sock.recvfrom(1024)
                if (data[0] == 0) & (len(data) == 2):
                    # Send vibration
                    logging.warning('Sending Myo vibration command')
                    duration = int(data[1])
                    if 0 <= duration <= 3:
                        self.peripheral.writeCharacteristic(0x19, struct.pack('3b', 0x03, 0x01, duration), True)
                elif (data[0] == 1) & (len(data) == 1):
                    # Send Deep sleep
                    logging.warning('Sending Myo to deep sleep')
                    self.peripheral.writeCharacteristic(0x19, struct.pack('2b', 0x04, 0x01), True)

            except BlockingIOError:
                pass

    def close(self):
        self.sock.close()


class MyoDelegate(btle.DefaultDelegate):
    """
    Callback function for handling incoming data from bluetooth connection

    """
    # TODO: Currently this only supports udp streaming.  consider internal buffer for udp-free mode (local)

    def __init__(self, send_udp, raw_logger=None):
        self.send_udp = send_udp
        self.counter = {'emg': 0, 'imu': 0, 'battery': 0}
        self.logger = raw_logger
        super(MyoDelegate, self).__init__()

    def handleNotification(self, cHandle, data):
        if cHandle == 0x2b:  # EmgData0Characteristic
            self.send_udp(data)
            self.logger.debug('E0: ' + binascii.hexlify(data).decode('utf-8'))
            self.counter['emg'] += 2
        elif cHandle == 0x2e:  # EmgData1Characteristic
            self.send_udp(data)
            self.logger.debug('E1: ' + binascii.hexlify(data).decode('utf-8'))
            self.counter['emg'] += 2
        elif cHandle == 0x31:  # EmgData2Characteristic
            self.send_udp(data)
            self.logger.debug('E2: ' + binascii.hexlify(data).decode('utf-8'))
            self.counter['emg'] += 2
        elif cHandle == 0x34:  # EmgData3Characteristic
            self.send_udp(data)
            self.logger.debug('E3: ' + binascii.hexlify(data).decode('utf-8'))
            self.counter['emg'] += 2
        elif cHandle == 0x1c:  # IMUCharacteristic
            self.send_udp(data)
            self.logger.debug('IMU: ' + binascii.hexlify(data).decode('utf-8'))
            self.counter['imu'] += 1
        elif cHandle == 0x11:  # BatteryCharacteristic
            self.send_udp(data)
            self.logger.info('Battery Level: {}'.format(ord(data)))
            self.counter['battery'] += 1
        else:
            self.logger.warning('Got Unknown Notification: %d' % cHandle)

        return


def setup_threads():

    # get parameters from xml files and create Servers
    s1 = MyoUdpServer(data_logger=logging.getLogger('Myo1'), name='Myo1')

    if uc.get_user_config_var('MyoUdpServer.num_devices', 2) < 2:
        s2 = None
        return s1, s2

    s2 = MyoUdpServer(data_logger=logging.getLogger('Myo2'), name='Myo2')

    return s1, s2


def main():
    """Parse command line arguments into argparse model.

    Command-line arguments:
    -h or --help -- output help text describing command-line arguments.

    """
    import sys
    import argparse

    # Parameters:
    parser = argparse.ArgumentParser(description='myo_server: read bluetooth packets from myo and stream to UDP.')
    parser.add_argument('-x', '--XML', help=r'XML Parameter File (e.g. user_config.xml)', default=None)
    args = parser.parse_args()

    if args.XML is not None:
        uc.read_user_config_file(file=args.XML)
        s1, s2 = setup_threads()

        if s2 is None:
            print('Connecting Device #1')
            s1.connect()
            time.sleep(0.5)
            s1.thread.start()
            time.sleep(0.5)
            s1.set_host_parameters()
        else:
            print('Connecting Device #1')
            s1.connect()
            print('Connecting Device #2')
            s2.connect()
            print('Both Connected')

            time.sleep(0.5)
            s1.thread.start()
            time.sleep(0.5)
            s2.thread.start()
            time.sleep(1.5)
            s2.set_host_parameters()
            time.sleep(0.5)
            s1.set_host_parameters()

    print(sys.argv[0] + " Version: " + __version__)


if __name__ == '__main__':
    main()
