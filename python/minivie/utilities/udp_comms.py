import logging
import socket
import threading
import time


class Udp(threading.Thread):
    def __init__(self, local_address=None, remote_address=None):
        """
            Handles UDP communications layer

            This creates a socket and checks for received data on a separate thread

            Once created and connected, user can use send() to transmit data.  Receiving data involves adding a
            message_handler function to process incoming data


        @param local_address: tuple of ('IP_ADDRESS', Port)
        @param remote_address: tuple of ('IP_ADDRESS', Port)
        """

        threading.Thread.__init__(self)
        self.__run_control = False  # Used by the start and terminate methods to control thread
        self.read_buffer_size = 1024
        self.sock = None

        self.local_addr = local_address
        self.remote_addr = remote_address

        self.__is_data_received = False  # This is True when packets are actively coming in without timout
        self.__is_connected = False  # This is True once socket open, but no guarantee of data incoming
        self.timeout = 3.0

        # store some rate counting parameters
        self.__packet_count = 0
        self.__packet_time = 0.0
        self.__packet_rate = 0.0
        self.__packet_update_time = 1.0  # seconds

        # store functions to be called on for incoming data
        self.__message_handlers = []

    def data_received(self):
        return self.__is_data_received

    def add_message_handler(self, message_handler):
        # attach a function to subscribe to messages
        if message_handler not in self.__message_handlers:
            self.__message_handlers.append(message_handler)

    def connect(self):

        logging.info(f"Udp local address: {self.local_addr}, remote address: {self.remote_addr}")

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # Enable broadcasting
        self.sock.bind(self.local_addr)
        self.sock.settimeout(self.timeout)
        self.__is_connected = True

        # Create a thread for processing new data
        if not self.is_alive():
            logging.info('Starting thread: {}'.format(self.name))
            self.start()

    def terminate(self):
        logging.info(f'Terminating receive thread: {self.name}')
        self.__run_control = False
        self.__is_connected = False

    def on_connection_lost(self):
        logging.warning(f'Udp "{self.name}" timed out during recvfrom() on address: {self.local_addr}')

    def run(self):
        """
        This is the thread function to receive data as soon as it arrives.

        Loop forever to receive data via UDP

        Note this overrides the Thread run() method

        @return:
        """

        if not self.__is_connected:
            logging.error("Socket is not connected")
            return

        self.__run_control = True

        while self.__run_control:
            # Blocking call until data received
            try:
                # receive call will error if socket closed externally (i.e. on exit)
                # blocks until timeout or socket closed
                data_bytes, address = self.sock.recvfrom(self.read_buffer_size)

                # if the above function returns (without error) it means we have a connection
                if not self.__is_data_received:
                    logging.info('Connection is Active: Data received')
                    self.__is_data_received = True

                # Count new packets
                self.__packet_count += 1

                # Execute the callback function assigned to __message_handlers
                for message_handler in self.__message_handlers:
                    message_handler(data_bytes)

            except socket.timeout:
                # the data stream has stopped.  don't break the thread, just continue to wait
                self.__is_data_received = False
                self.on_connection_lost()
                continue

            except socket.error:
                # The connection has been closed
                logging.info(f"Socket Closed at {self.local_addr}")
                # break so that the thread can terminate
                self.__run_control = False
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

        if self.__is_connected:
            # Note this command can error if socket disconnected
            try:
                self.sock.sendto(msg_bytes, address)
            except Exception as e:
                # This exception is only expected in the transient case where the socket disconnects during sendto()
                logging.error(e)
        else:
            logging.warning('Socket disconnected')

    def get_packet_data_rate(self):
        # Return the packet data rate

        # get the number of new samples over the last n seconds

        # compute data rate
        t_now = time.time()
        t_elapsed = t_now - self.__packet_time

        if t_elapsed > self.__packet_update_time:
            # compute rate (every few seconds second)
            self.__packet_rate = self.__packet_count / t_elapsed
            self.__packet_count = 0  # reset counter
            self.__packet_time = t_now

        return self.__packet_rate

    def close(self):
        """
            Cleanup socket
            close the socket
            disable the run control loop and join receive thread to main

        :return:
            None
        """
        self.terminate()
        if self.sock is not None:
            logging.info(f"Closing Socket Address {self.local_addr} --> {self.remote_addr}")
            self.sock.close()
        self.join()


def main():
    print('Starting Udp Test')

    # Create two reciprocal udp objects, one posing as server, the other a client
    # Test various comms scenarios

    # Create server
    server = Udp()
    server.local_addr = ('localhost', 1234)
    server.remote_addr = ('localhost', 4321)
    server.name = 'TestServer'
    server.add_message_handler(lambda p: print(f'Server Received: {p}'))
    server.timeout = 2.0
    server.run()
    server.connect()

    # On initial connection, we don't expect to have received any data
    if not server.data_received():
        print('#1 Server has not received any data')
    # Data rate should be zero
    print(f'Server data rate is {server.get_packet_data_rate()} (0 expected)')

    # Create client
    client = Udp()
    client.local_addr = ('localhost', 4321)
    client.remote_addr = ('localhost', 1234)
    client.name = 'TestClient'
    client.timeout = 2.5
    client.connect()

    # Now send some data
    client.send(b'#1 Test message from client')
    # It might take some finite amount of time to receive the data
    if not server.data_received():
        print('#2 Server has not received any data')
    client.send(b'#2 Another test message from client')
    client.send(b'#3 Yet another test message from client')

    time.sleep(0.2)
    # But by now the data should have come through
    if server.data_received():
        print('#3 Server has received data!')

    # Data rate can now be computed
    print(f'Server data rate is {server.get_packet_data_rate():.2E} (non-zero expected)')

    # with no more data, a timeout warning is expected
    print('Waiting for timeout')
    time.sleep(3.0)

    # close client by terminating loop then closing
    client.terminate()
    client.close()

    # Should not be able to send once closed
    client.send(b'Test message from client')

    server.close()
    time.sleep(1.0)

    # close server by closing then terminating loop

    print('Done')

    pass


if __name__ == '__main__':
    main()
