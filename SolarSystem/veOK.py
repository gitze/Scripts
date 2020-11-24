#!/usr/bin/python
# -*- coding: utf-8 -*-
# Plus que largement inspiré de karioja : https://github.com/karioja/vedirect

import os, sys
import binascii
import json
import requests
from urllib.parse import urlencode, quote_plus
import time, datetime
import configparser
try:
    import serial
    import serial.tools.list_ports
except ImportError as e:
    error = "Please install pyserial 2.7+! pip install pyserial"
    log.error(error)
    raise ImportError(error)


# ###########################
# Config Parameter
# ###########################
emoncsm_apikey = "apikey"
emoncsm_node = "node_name"
emoncsm_url = "https://url"

config = configparser.ConfigParser()
config.read('./emoncms.conf')
emoncsm_apikey = config.get('DEFAULT', 'emoncsm_apikey', fallback = emoncsm_apikey)
emoncsm_url    = config.get('DEFAULT', 'emoncsm_url',    fallback = emoncsm_url)
emoncsm_node   = config.get('Victron', 'emoncsm_node',   fallback = emoncsm_node)


USBDeviceName="Victron MPPT"
ShowDebug = False

# ###########################
# Functions
# ###########################
def findSerialDevices(SearchPhrase="search phrase"):
    SearchPhrase = "(?i)" + SearchPhrase  # forces case insensitive
    USBPortId="NOT FOUND"
    for port in serial.tools.list_ports.grep(SearchPhrase):
        USBPortId = port[0]
    return USBPortId


class vedirect:
    def __init__(self, serialport):
        self.serialport = serialport
        self.ser = serial.Serial(serialport, baudrate = 19200, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=1)
        self.header1 = b'\r'
        self.header2 = b'\n'
        self.delimiter = b'\t'
        self.key = b''
        self.value = b''
        self.bytes_sum = 0
        self.state = self.WAIT_HEADER
        self.dict = {}

    (WAIT_HEADER, IN_KEY, IN_VALUE, IN_CHECKSUM) = range(4)

    def input(self, byte):
        self.bytes_sum += ord(byte)
        if self.state == self.WAIT_HEADER:
            if byte == self.header2:
                self.state = self.IN_KEY
                self.key = b''
            return None
        elif self.state == self.IN_KEY:
            if byte == self.delimiter:
                self.state = self.IN_CHECKSUM if self.key == b'Checksum' else self.IN_VALUE
            else:
                self.key += byte
            return None
        elif self.state == self.IN_VALUE:
            if byte == self.header1:
                self.state = self.WAIT_HEADER
                #  print (self.key + ":" + self.value)
                self.dict[self.key.decode("utf-8") ] = self.value.decode("utf-8") 
                self.key = b''
                self.value = b''
            else:
                self.value += byte
            return None
        elif self.state == self.IN_CHECKSUM:
            self.key = b''
            self.value = b''
            self.state = self.WAIT_HEADER
            if (self.bytes_sum % 256 == 0):
                self.bytes_sum = 0
                return self.dict
            else:
                print ("Checksum ERROR: ",self.dict)
#                print (self.dict)
                self.dict.clear()
                self.bytes_sum = 0
                return None
        else:
            raise AssertionError()

    def read_data_single(self):
        while True:
            byte = self.ser.read(1)
            packet = self.input(byte)
            # print ("{} {}".format(self.key,self.value))
            if (packet != None):
                return packet

    def reset_input_buffer(self):
        self.ser.reset_input_buffer()
        

def openSerial(DevicePort, BaudRate, TimeOut):
    SerialCon = serial.Serial(
        port=DevicePort, baudrate=BaudRate,
        parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS,
        timeout=TimeOut
    )
    return SerialCon


def sendData2webservice(data123):
    data = json.dumps(data123)
    TimeStamp = int(time.time())
    HTTPStatus=999
    myurl = '{}{}'.format(
        emoncsm_url, 
        urlencode({'node': emoncsm_node, 'time': TimeStamp, 'fulljson': data, 'apikey': emoncsm_apikey})
    )
    try:
#        print ("Vor dem Call  {}".format(int(time.time())))
        r = requests.get(myurl, timeout=1.5)
#        print ("Nach dem Call {}".format(int(time.time())))
        HTTPStatus=r.status_code
        r.raise_for_status()
        #print (r)
#    except requests.exceptions.Timeout:
#        print ("Timeout Block {}".format(int(time.time())))
#        print (r)
        #logit("ERROR|Webservice Timeout|{}".format(HTTPerror))
#        HTTPStatus = 999
    # Maybe set up for a retry, or continue in a retry loop
    # except requests.exceptions.TooManyRedirects:
    # Tell the user their URL was bad and try a different one
    except requests.exceptions.RequestException as HTTPerror: 
#        print ("Error Block {}".format(int(time.time())))
        logit("ERROR|Webservice Fehler|{}".format(HTTPerror))

    return HTTPStatus

def cleanupData(dicData):
    entriesToRemove = ('PID', 'SER#', 'FW','HSDS')
    for key in entriesToRemove:
        dicData.pop(key, None)
    
    dicData.update(LOAD = 1) if dicData.get("LOAD") == "ON" else dicData.update(LOAD = 0)
    
    #print (dicData)
    entriesToRecalc = {'V': 0.001, 'VPV': 0.001, 'I': 0.001, 'IL': 0.001, 'H19': 10, 'H20': 10, 'H22': 10 }
    for key, val in entriesToRecalc.items():
        dicData[key] = round(int(dicData.get(key,0)) * val ,3)
    # print (dicData)
    return dicData


def logit(logvalue):
    filehandler = open("/home/pi/victron.log","a")
    filehandler.write(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "|" + logvalue + "\n")
    filehandler.flush()
    filehandler.close ()
    if ShowDebug: print("DEBUG:" + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "|" + logvalue)
    return


# ###########################
# Input Parameter
# ###########################
if len(sys.argv) < 2:
    print("Autodetecting USB Port for '{}'".format(USBDeviceName))
    serialPort = findSerialDevices(USBDeviceName)
    if (serialPort == "NOT FOUND"):
        print ("Device {} not found".format(USBDeviceName))
        sys.exit(1)
    else:
        print("Device found, using port {}".format(serialPort))
else:
    serialPort = sys.argv[1]
    print("Using device {}".format(serialPort))


# ###########################
# Main
# ###########################
if __name__ == '__main__':
#    SerialCon = openSerial(serialPort, 19200, 10))
    data123 = dict() 
    checksumFail = 0
    HTTPReturnCode = 0
    ve = vedirect(serialPort)
    while True:
        TimerStart = int(time.time())
        data123 = ve.read_data_single()
        data123 = cleanupData(data123)
        HTTPReturnCode = sendData2webservice(data123)
        logit(str(TimerStart) + "|"  + emoncsm_node + "|" + str(HTTPReturnCode) + "|" + json.dumps(data123))
        # fileout.write(myurl)
        # print (data123)
        # print (myurl)
        data123.clear()
        ve.reset_input_buffer()
        TimerEnd = int(time.time())
#        print (max([5 - (TimerEnd - TimerStart), 0]))
        time.sleep(max([5 - (TimerEnd - TimerStart), 0]))
    #sys.stdout.flush()
