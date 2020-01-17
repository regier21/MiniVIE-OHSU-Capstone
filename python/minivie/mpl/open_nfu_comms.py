import asyncio
import time
import logging
from utilities import get_address


class UdpProtocol(asyncio.DatagramProtocol):
    """ Extend the UDP Protocol for device communication
    """
    def __init__(self, parent):
        self.parent = parent

    def datagram_received(self, data, addr):
        self.parent.packet_count += 1
        for func in self.parent.func_handle:
            func(data)


class AsyncUdp(object):
    def __init__(self, local_address='//0.0.0.0:9028', remote_address='//127.0.0.1:9027'):
        self.name = "AsyncUdp"

        self.loop = None
        self.transport = None
        self.protocol = None
        self.local_addr = get_address(local_address)  # str to addr tuple
        self.remote_addr = get_address(remote_address)  # str to addr tuple
        self.is_connected = False

        # store some rate counting parameters
        self.packet_count = 0
        self.packet_time = 0.0
        self.packet_rate = 0.0
        self.packet_update_time = 1.0  # seconds

        self.func_handle = []  # list of callbacks for message recv

    def connect(self):
        """ Connect UDP socket and register callback for data received """
        self.loop = asyncio.get_event_loop()
        # Get a reference to the event loop as we plan to use low-level APIs.
        # From python 3.7 docs (https://docs.python.org/3.7/library/asyncio-protocol.html#)
        listen = self.loop.create_datagram_endpoint(
            lambda: UdpProtocol(parent=self), local_addr=self.local_addr)
        self.is_connected = True
        self.transport, self.protocol = self.loop.run_until_complete(listen)

    def send(self, packed_data):
        if self.is_connected:
            self.transport.sendto(packed_data, self.remote_addr)

    def add_message_handler(self, func):
        # attach a function to receive commands from websocket
        if func not in self.func_handle:
            self.func_handle.append(func)

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
        logging.info(f"Closing {self.name} Socket @ {self.remote_addr}")
        self.transport.close()
        self.is_connected = False

