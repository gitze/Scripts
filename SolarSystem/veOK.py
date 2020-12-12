#!/usr/bin/python
# -*- coding: utf-8 -*-

# pip3 install pyserial

import os, sys
import binascii
import json
import requests
from urllib.parse import urlencode, quote_plus
import time, datetime
import signal
import configparser
import solar_logger
import serial, serial.tools.list_ports


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

USBDeviceName="VictronEnergy"
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


def checksum256(the_bytes):
    return (sum(the_bytes) % 256)


def abortProgram(errortext):
        print ("ABORT PROGRAM")
        print (errortext)
        SerialCon.close()
        sys.exit(1)

def signal_handler(signum, frame):
    print ('Here you go - you presses CTRL-C')
    abortProgram("due to CTRL-C'")

signal.signal(signal.SIGINT, signal_handler)

def ve_readinput(SerialCon):
        Bytes = b''
        ControlCycles = 0
        while True:
                try: Byte=SerialCon.readline()
                except Exception as Error: print("An exception occurred: {}".format(Error))
                ControlCycles=ControlCycles+1
                if (ControlCycles > 100):
                    logit("ERROR|Serial Connection Issues. No data received within the last {} reading cycles|{}".format(ControlCycles))
                    return 99 # abortProgram("No valid Victron Serial data received. Device not connected?")
                if (Bytes == b'\r\n'): Bytes = b'' # Remove '\r\n' as first bytes in the result
                if (Byte[:8] == b'Checksum') : Byte = Byte[:10] # Remove '\r\n' as last bytes in the result
                Bytes = Bytes + Byte
                if (Byte[:8] == b'Checksum') : 
                        ByteChecksum = checksum256(Bytes + b'\r\n')  # Add '\r\n' to the correct checksum calsulation
                        if (ByteChecksum > 0):
                            logit("ERROR|Checksum wrong|{}|{}".format(ByteChecksum,Bytes))
                            return None # Checksum wrong
                        try:
                                InputDict = dict(xx.split(b'\t') for xx in Bytes.split(b'\r\n'))
                                InputDict.pop(b'Checksum', None)  # Remove Checksum, but wiothout `KeyError`
                                InputDict = { keyy.decode('utf-8'): InputDict.get(keyy).decode('utf-8') for keyy in InputDict.keys() } 
                                return InputDict
                        except Exception as Error: 
                            print("An unexpected exception occurred: {}".format(Error))
                            return 10 # An Error occured during value processing. This should not happen
                        Bytes = b''
                # else:
                #         print ("ELSE")   
        logit("ERROR|Unexpected point of code ")         
        return None


def openSerial(DevicePort, BaudRate, TimeOut):
    SerialCon = serial.Serial(
        port=DevicePort, baudrate=BaudRate,
        parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS,
        timeout=TimeOut
    )
    return SerialCon


def sendData2webservice(TimeStamp, data123):
    data = json.dumps(data123)
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
    for key in entriesToRemove: dicData.pop(key, None)

    dicData.update(LOAD = 1) if dicData.get("LOAD") == "ON" else dicData.update(LOAD = 0)

    entriesToRecalc = {'V': 0.001, 'VPV': 0.001, 'I': 0.001, 'IL': 0.001, 'H19': 10, 'H20': 10, 'H22': 10 }
    for key, val in entriesToRecalc.items(): dicData[key] = round(int(dicData.get(key,0)) * val ,3)

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
    SerialCon = openSerial(serialPort, 19200, 0.200)
    while True:
        TimerStart = int(time.time())
        ve_data = ve_readinput(SerialCon)
        if isinstance(ve_data, dict): 
            #print (ve_data)
            ve_data = cleanupData(ve_data)
            TimeStamp = int(time.time())
            #print (ve_data)
            HTTPReturnCode = sendData2webservice(TimeStamp, ve_data)
            logit(str(TimerStart) + "|"  + emoncsm_node + "|" + str(HTTPReturnCode) + "|" + json.dumps(ve_data))
            TimerEnd = int(time.time())
            time.sleep(max([5 - (TimerEnd - TimerStart), 0]))
        else: 
            logit("ERROR|veDateRead Error Code|{}".format(ve_data))
            # if (ve_data == None): 
            # if (ve_data == 10):   
            if (ve_data == 99):   abortProgram("No valid Victron Serial data received. Device not connected?")

    #sys.stdout.flush()