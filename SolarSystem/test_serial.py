#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
import serial
import sys
import binascii
import serial.tools.list_ports


def findSerialDevices(hardwareID="1D50:60AB"):
    hardwareID = "(?i)" + hardwareID  # forces case insensitive
    id="NOT FOUND"
    for port in serial.tools.list_ports.grep(hardwareID):
        id = port[0]
    return id

ports = serial.tools.list_ports.comports()

for  port, desc, hwid in sorted(ports):
        print("{}: {} [{}]".format(port, desc, hwid))
print ("Find USB Ports ....")
print (findSerialDevices("123SmartBMS ControllerX"))
print (findSerialDevices("123SmartBMS Controller"))
print (findSerialDevices("Victron MPPT"))

sys.exit(0)


def readSerialData(SerialConsole):
    SerialByte = b''

    SerialByte = SerialConsole.read(3)
    print(binascii.hexlify(SerialByte), end = '')
    return SerialByte


def openSerial(DevicePort):
    SerialCon = serial.Serial(
        port=DevicePort, baudrate=9600,
        parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS,
        timeout=0.1
    )
    return SerialCon


# ###########################
# Main
# ###########################
if __name__ == '__main__':
    Device = "/dev/ttyUSB1"    
    SerialCon = openSerial(Device)
    SerialByte = readSerialData(SerialCon)
    SerialCon.close()
    sys.exit(0)
