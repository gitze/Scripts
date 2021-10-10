#!/usr/bin/python3
# -*- coding: utf-8 -*-

# pip3 install pyserial

import os
import sys
import binascii
import json
# import requests
# from urllib.parse import urlencode, quote_plus
import time
import datetime
import signal
import configparser
import solar_logger
import serial
import serial.tools.list_ports
import solar_threadhandler
import logging

# ###########################
# Config Parameter
# ###########################
emoncsm_apikey = "apikey"
emoncsm_node = "node_name"
emoncsm_url = "https://url"

config = configparser.ConfigParser()
config.read('/opt/solar/emoncms.conf')
emoncsm_apikey = config.get(
    'DEFAULT', 'emoncsm_apikey', fallback=emoncsm_apikey)
emoncsm_url = config.get('DEFAULT', 'emoncsm_url',    fallback=emoncsm_url)
emoncsm_node = config.get('Victron', 'emoncsm_node',   fallback=emoncsm_node)

USBDeviceName = ["Victron", "VE Direct cable"]
ShowDebug = False

# ###########################
# Functions
# ###########################


def findSerialDevices(SearchPhraseArray=["VE Direct cable"]):
    #   SearchTerms = len(SearchPhraseArray)
    for SearchPhrase in SearchPhraseArray:
        #        print(SearchPhrase)
        SearchPhrase = "(?i)" + SearchPhrase  # forces case insensitive
#        lines = len(list(serial.tools.list_ports.grep(SearchPhrase)))
#        print (lines)
        for port in serial.tools.list_ports.grep(SearchPhrase):
            USBPortId = port[0]
            return USBPortId
    return None


def checksum256(the_bytes):
    return (sum(the_bytes) % 256)


# def signal_handler(signum, frame):
#     print('Here you go - you presses CTRL-C')
#     abortProgram("due to CTRL-C'")
# signal.signal(signal.SIGINT, signal_handler)


def ve_readinput(SerialCon):
    Bytes = b''
    ControlCycles = 0
    while True:
        try:
            Byte = SerialCon.readline()
        except Exception as Error:
            logger.debug("SerialCon Error: An exception occurred: {}".format(Error))
            return 98

        ControlCycles = ControlCycles+1
        if (ControlCycles > 100):
            logger.error("SerialCon Issues: No data received within the last {} reading cycles".format(ControlCycles))
            # abortProgram("No valid Victron Serial data received. Device not connected?")
            return 99

        # Remove '\r\n' as first bytes in the result
        if (Bytes == b'\r\n'): Bytes = b'' 
        
        # Remove '\r\n' as last bytes in the result
        if (Byte[:8] == b'Checksum'): Byte = Byte[:10]  

        Bytes = Bytes + Byte

        if (Byte[:8] == b'Checksum'):
            # Add '\r\n' to the correct checksum calsulation
            ByteChecksum = checksum256(Bytes + b'\r\n')
            if (ByteChecksum > 0):
                logger.error("ERROR|Checksum wrong|{}|{}".format(ByteChecksum, Bytes))
                return 1  # Checksum wrong
            try:
                InputDict = dict(xx.split(b'\t') for xx in Bytes.split(b'\r\n'))
                # Remove Checksum, but without `KeyError`
                InputDict.pop(b'Checksum', None)
                InputDict = {keyy.decode('utf-8'): InputDict.get(keyy).decode('utf-8') for keyy in InputDict.keys()}
                return InputDict
            except Exception as Error:
                logger.error("An unexpected exception occurred: {}".format(Error))
                logger.error("InputData: {}".format(Bytes)) 
                return 10  # An Error occured during value processing. This should not happen
            Bytes = b''
        # else:
        #         print ("ELSE")
    logger.error("ERROR|Unexpected point of code")
    logit("ERROR|Unexpected point of code")
    return 999


def openSerial(DevicePort, BaudRate, TimeOut):
    SerialCon = serial.Serial(
        port=DevicePort, baudrate=BaudRate,
        parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS,
        timeout=TimeOut
    )
    return SerialCon



def cleanupData(dicData):
    entriesToRemove = ('PID', 'SER#', 'FW', 'HSDS')
    for key in entriesToRemove:
        dicData.pop(key, None)

    dicData.update(LOAD=1) if dicData.get(
        "LOAD") == "ON" else dicData.update(LOAD=0)

    entriesToRecalc = {'V': 0.001, 'VPV': 0.001, 'I': 0.001,
                       'IL': 0.001, 'H19': 10, 'H20': 10, 'H22': 10}
    for key, val in entriesToRecalc.items():
        dicData[key] = round(int(dicData.get(key, 0)) * val, 3)

    return dicData


# ###########################
# Input Parameter
# ###########################
def getSerialPort():
    if len(sys.argv) < 2:
        logger.info("Autodetecting USB Port for '{}'".format(USBDeviceName))
        serialPort = findSerialDevices(USBDeviceName)
        if (serialPort == None):
            logger.error("Device {} not found".format(USBDeviceName))
            sys.exit(1)
        else:
            logger.info("Device found, using port {}".format(serialPort))
    else:
        serialPort = sys.argv[1]
        logger.info("Using device {}".format(serialPort))
    return(serialPort)


def printvars():
    tmp = globals().copy()
    print("============================================================================")
    [print(k, '  :  ', v, ' type:', type(v)) for k, v in tmp.items() if not k.startswith(
        '_') and k != 'tmp' and k != 'In' and k != 'Out' and not hasattr(v, '__call__')]
    # pprint(vars(EmonCMS))
    print("============================================================================")


# ###########################
# Exception Handling
# ###########################
def handle_exit(sig, frame):
    raise(SystemExit)


signal.signal(signal.SIGTERM, handle_exit)

# ###########################
# Main
# ###########################
if __name__ == '__main__':
    # create logger
    logger = logging.getLogger(__name__)
    solar_logger.logger_setup('/home/pi/')

    logger.info("Starting Victron Monitoring")
    serialPort = getSerialPort()
    SerialCon = openSerial(serialPort, 19200, 0.200)
    EmonCMS = solar_threadhandler.DataLoggerQueue(
        "victron", emoncsm_url, emoncsm_apikey)
    EmonCMS.StartQueue()
    try:
        while True:
            if EmonCMS.isAlive() is False:
                logger.error(
                    "ERROR: solar_threadhandler is not running anymore")
                raise (SystemExit)
            TimerStart = int(time.time())
            ve_data = ve_readinput(SerialCon)
            if isinstance(ve_data, dict):
                #print (ve_data)
                ve_data = cleanupData(ve_data)
                TimeStamp = int(time.time())
                #print (ve_data)
                EmonCMS.addDataQueue(ve_data, emoncsm_node)
                # HTTPReturnCode = sendData2webservice(TimeStamp, ve_data)
                # logit(str(TimerStart) + "|" + emoncsm_node + "|" + str(HTTPReturnCode) + "|" + json.dumps(ve_data))
                TimerEnd = int(time.time())
                time.sleep(max([5 - (TimerEnd - TimerStart), 0]))
            else:
                logger.error(f"ERROR|veDateRead Error Code|{ve_data}")
                # if (ve_data == None):
                # if (ve_data == 10):
                if (ve_data == 99):
                    logger.error(
                        "No valid Victron Serial data received. Device not connected?")
                    raise(SystemExit)
    except KeyboardInterrupt:
        # Programm wird beendet wenn CTRL+C gedrückt wird.
        logger.info('Warte auf Ende von DataLoggerQueueProcessing')
        EmonCMS.StopQueue()
        logger.info('Datensammlung wird beendet')
    except Exception as e:
        logger.critical(f'Unerwarteter Abbruch: {str(e)}')
        sys.exit(1)
    except (KeyboardInterrupt, SystemExit):
        logger.info('Programm Abbruch wird eingeleitet')
    finally:
        # Das Programm wird hier beendet, sodass kein Fehler in die Console geschrieben wird.
        EmonCMS.StopQueue()
        SerialCon.close()
        logger.info('Programm wurde beendet.')
        sys.exit(0)
