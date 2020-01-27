#!/usr/bin/env python
"""
communicate between cyberglove bluetooth serial interface and UDP

sudo python3 -m inputs.cyber_glove

@author: Armiger
"""
import serial
import socket


def main():
    port = ("10.132.13.210", 16700)

    print('Starting...')
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # Enable broadcasting
    sock.settimeout(1.0)

    ser = serial.Serial("/dev/rfcomm0", 115200, timeout=1.0)
    #   ser.open()
    ser.write(b'?W')
    r = ser.read(100)
    print(r)
    ser.write(b'?S')
    r = ser.read(100)
    print(r)
    print('Starting Streaming')
    ser.write(b'S')

    while 1:
        # print('Getting Data')
        # ser.write(b'G')
        buff = b''

        # Read full response
        while 1:
            r = ser.read()
            if r == b'\x00':
                print(f'Msg [{len(buff)}] = {buff}')
                break
            buff += r
        sock.sendto(buff, port)


if __name__ == '__main__':
    main()
