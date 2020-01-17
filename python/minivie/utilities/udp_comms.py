import logging
import socket
import threading
import time


class Udp(threading.Thread):
    def __init__(self, local_address=None, remote_address=None):
        """
            Handles UDP communications layer

            Once created and connected, user can use send() to transmit data.  Receiving data involves adding a
            message_handler function to process incoming data


        @param local_address: tuple of ('IP_ADDRESS', Port)
        @param remote_address: tuple of ('IP_ADDRESS', Port)
        """

        threading.Thread.__init__(self)
        self.run_control = False  # Used by the start and terminate to control thread
        self.read_buffer_size = 1024
        self.sock = None

        self.local_addr = local_address
        self.remote_addr = remote_address

        self.is_data_received = False  # This is True when packets are actively coming in without timout
        self.is_connected = False  # This is True once socket open, but no guarantee of data incoming
        self.timeout = 3.0

        # store some rate counting parameters
        self.packet_count = 0
        self.packet_time = 0.0
        self.packet_rate = 0.0
        self.packet_update_time = 1.0  # seconds

        # store functions to be called on for incoming data
        self.message_handlers = []

    def data_received(self):
        return self.is_data_received

    def add_message_handler(self, message_handler):
        # attach a function to subscribe to messages
        if message_handler not in self.message_handlers:
            self.message_handlers.append(message_handler)

    def connect(self):

        logging.info(f"Udp local address: {self.local_addr}, remote address: {self.remote_addr}")

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # Enable broadcasting
        self.sock.bind(self.local_addr)
        self.sock.settimeout(self.timeout)
        self.is_connected = True

        # Create a thread for processing new data
        if not self.is_alive():
            logging.info('Starting thread: {}'.format(self.name))
            self.start()

    def terminate(self):
        logging.info(f'Terminating receive thread: {self.name}')
        self.run_control = False

    def on_connection_lost(self):
        logging.warning(f"Timed out during recvfrom() on address: {self.local_addr}")

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
                    logging.info('Connection is Active: Data received')
                    self.is_data_received = True

                self.packet_count += 1

                # Execute the callback function assigned to message_handlers
                for message_handler in self.message_handlers:
                    message_handler(data_bytes)

            except socket.timeout:
                # the data stream has stopped.  don't break the thread, just continue to wait
                self.is_data_received = False
                self.on_connection_lost()
                continue

            except socket.error:
                # The connection has been closed
                logging.info(f"Socket Closed at {self.local_addr}")
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

        address = address if address is not None else self.remote_addr

        if self.is_connected:
            # Note this command can error if socket disconnected
            try:
                self.sock.sendto(msg_bytes, address)
            except Exception as e:
                logging.error(e)
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
            logging.info(f"Closing Socket Address {self.local_addr} --> {self.remote_addr}")
            self.sock.close()
        self.join()
