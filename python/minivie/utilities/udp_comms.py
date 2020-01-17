import logging
import socket
import threading
import time

from utilities import get_address


class Udp(threading.Thread):
    # Basic Template for thread based udp communications
    #
    # key function is the onmessage attribute that is called on data receive

    def __init__(self, local_address='//0.0.0.0:9027', remote_address='//127.0.0.1:9028'):

        threading.Thread.__init__(self)
        self.run_control = False  # Used by the start and terminate to control thread
        self.read_buffer_size = 1024
        self.sock = None

        remote_hostname, remote_port = get_address(remote_address)
        local_hostname, local_port = get_address(local_address)
        self.udp = {'RemoteHostname': remote_hostname, 'RemotePort': remote_port,
                    'LocalHostname': local_hostname, 'LocalPort': local_port}

        self.is_data_received = False
        self.is_connected = False
        self.timeout = 3.0

        # store some rate counting parameters
        self.packet_count = 0
        self.packet_time = 0.0
        self.packet_rate = 0.0
        self.packet_update_time = 1.0  # seconds

        # default callback is just the print function.  this can be overwritten. also for i in callbacks??
        self.onmessage = lambda s: 1 + 1
        # self.onmessage = print
        pass

    def data_received(self):
        return self.is_data_received

    def connect(self):
        logging.info("{} local port: {}:{}".format(self.name, self.udp['LocalHostname'], self.udp['LocalPort']))
        logging.info("{} remote port: {}:{}".format(self.name, self.udp['RemoteHostname'], self.udp['RemotePort']))
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1) # Enable broadcasting
        self.sock.bind((self.udp['LocalHostname'], self.udp['LocalPort']))
        self.sock.settimeout(self.timeout)
        self.is_connected = True

        # Create a thread for processing new data
        if not self.is_alive():
            logging.info('Starting thread: {}'.format(self.name))
            self.start()

    def terminate(self):
        logging.info('Terminating receive thread: {}'.format(self.name))
        self.run_control = False

    def on_connection_lost(self):
        msg = "{} timed out during recvfrom() on IP={} Port={}".format(
            self.name, self.udp['LocalHostname'], self.udp['LocalPort'])
        logging.warning(msg)
        logging.info('{} Connection is Lost'.format(self.name))

    def run(self):
        # Loop forever to receive data via UDP
        #
        # This is a thread to receive data as soon as it arrives.

        if not self.is_connected:
            logging.error("Socket is not connected")
            return

        self.run_control = True

        while self.run_control:
            # Blocking call until data received
            try:
                # receive call will error if socket closed externally (i.e. on exit)
                # blocks until timeout or socket closed
                data_bytes, address = self.sock.recvfrom(self.read_buffer_size)

                # if the above function returns (without error) it means we have a connection
                if not self.is_data_received:
                    logging.info('{} Connection is Active: Data received'.format(self.name))
                    self.is_data_received = True

                self.packet_count += 1

                # Execute the callback function assigned to self.onmessage
                self.onmessage(data_bytes)

            except socket.timeout:
                # the data stream has stopped.  don't break the thread, just continue to wait
                self.is_data_received = False
                self.on_connection_lost()
                continue

            except socket.error:
                # The connection has been closed
                msg = "{} Socket Closed on IP={} Port={}.".format(
                    self.name, self.udp['LocalHostname'], self.udp['LocalPort'])
                logging.info(msg)
                # break so that the thread can terminate
                self.run_control = False
                break

    def send(self, msg_bytes, address=None):
        """
        Send msg_bytes to remote host using either the established parameters stored as properties, or those
        parameters provided to the function call
        :param msg_bytes:
            encoded message bytes to be sent via socket
        :param address:
            address is a tuple (host, port)
        :return:
            None
        """

        address = address if address is not None else (self.udp['RemoteHostname'], self.udp['RemotePort'])

        if self.is_connected:
            # Note this command can error if socket disconnected
            try:
                self.sock.sendto(msg_bytes, address)
            except Exception as e:
                logging.ERROR(e)
        else:
            logging.warning('Socket disconnected')

    def get_packet_data_rate(self):
        # Return the packet data rate

        # get the number of new samples over the last n seconds

        # compute data rate
        t_now = time.time()
        t_elapsed = t_now - self.packet_time

        if t_elapsed > self.packet_update_time:
            # compute rate (every few seconds second)
            self.packet_rate = self.packet_count / t_elapsed
            self.packet_count = 0  # reset counter
            self.packet_time = t_now

        return self.packet_rate

    def close(self):
        """
            Cleanup socket
            close the socket
            disable the run control loop and join receive thread to main

        :return:
            None
        """
        self.run_control = False
        if self.sock is not None:
            logging.info("{} Closing Socket IP={} Port={} to IP={} Port={}".format(
                self.name, self.udp['LocalHostname'], self.udp['LocalPort'],
                self.udp['RemoteHostname'], self.udp['RemotePort']))
            self.sock.close()
        self.join()