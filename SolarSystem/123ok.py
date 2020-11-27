#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import serial
import serial.tools.list_ports
import sys
import binascii
import json
import requests
from urllib.parse import urlencode, quote_plus
import time
import datetime
import configparser
import solar_logger


# ###########################
# Config Parameter
# ###########################
emoncsm_apikey = "apikey"
emoncsm_node = "node_name"
emoncsm_url = "https://url"

config = configparser.ConfigParser()
config.read('./emoncms.conf')
emoncsm_apikey = config.get('DEFAULT',     'emoncsm_apikey', fallback = emoncsm_apikey)
emoncsm_url    = config.get('DEFAULT',     'emoncsm_url',    fallback = emoncsm_url)
emoncsm_node   = config.get('123SmartBMS', 'emoncsm_node',   fallback = emoncsm_node)



extendetChecks = True
USBDeviceName="123SmartBMS Controller"
ShowDebug = False
# ###########################



# ###########################
# Functions
# ###########################

def findSerialDevices(SearchPhrase="search phrase"):
    SearchPhrase = "(?i)" + SearchPhrase  # forces case insensitive
    USBPortId="NOT FOUND"
    for port in serial.tools.list_ports.grep(SearchPhrase):
        USBPortId = port[0]
    return USBPortId

# returns total mod 256 as checksum
# http://code.activestate.com/recipes/52251-simple-string-checksum/
def checksum256(the_bytes):
    return b'%02X' % (sum(the_bytes) & 0xFF)

def isCheckSumOK(rawdata):
    checksumCalc = checksum256(rawdata[:-1]).upper()
    checksumComp = binascii.hexlify(rawdata[-1:]).upper()
    checkRecordOK = checksumCalc == checksumComp

    if not checkRecordOK:
        logging.warning("INPUT CRC Error: Calc {} Compare {} - Ergebnis: {}".format(checksumCalc, checksumComp, checkRecordOK))
    #   print ("CHECKSUM: Calc {} Compare {} - Ergebnis: {}".format(checksumCalc, checksumComp, checkRecordOK))    
    elif extendetChecks == True:
        # check: postion1  = 00, da Battery Voltage < 128
        # check: postion26 = 4, da 4 Battery verbaut
        # check: postion5  <= 08, da CurrentIn Ampere < 288 
        # check: postion8  <= 08, da CurrentIn Ampere < 288
        # check: postion11  <= 08, da CurrentIn Ampere < 288
        # check: postion52  == 02, da V-MIN Setting > 2.48 and < 3.84
        # check: postion54  == 02, da V-MAX Setting > 2.48 and < 3.84
        # check: postion56  == 02, da V-Balancing Setting > 2.48 and < 3.84
        extendetCheckOK = True and (rawdata[0] == 0) and (rawdata[25] == 4)
        if not extendetCheckOK:
            logging.warning("INPUT Quality Error: Extended Quality Check failed Voltage {}, No Battery {}".format(rawdata[0] , rawdata[25]))
            checkRecordOK = False
        extendetCheckOK = True and (rawdata[5-1] <= 8) and (rawdata[8-1] <= 8) and (rawdata[11-1] <= 8)
        if not extendetCheckOK:
            logging.warning("INPUT Quality Error: Extended Quality Check failed Current values {}, {}, {}".format(rawdata[5-1], rawdata[8-1], rawdata[11-1]))
            checkRecordOK = False
        extendetCheckOK = True and (rawdata[52-1] == 2) and (rawdata[54-1] == 2) and (rawdata[56-1] == 2)
        if not extendetCheckOK:
            logging.warning("INPUT Quality Error: Extended Quality Check failed Voltage Nin/Max/Balaning values {}, {}, {}".format(rawdata[52-1], rawdata[54-1], rawdata[56-1]))
            checkRecordOK = False

    return checkRecordOK


def parse_value(inputstr, start, len, *args, **kwargs):
    factor = kwargs.get('factor', 1)
    offset = kwargs.get('offset', 0)
    signed = kwargs.get('signed', False)
    # for key, value in kwargs.items():
    #     print("{0} = {1}".format(key, value))
    return calc_numbers(inputstr, start, len, factor, offset, signed)


def calc_numbers(inputstr, start, len, factor=1, offset=0, signed=False):
    SignFactor = 1
    if signed:
        Sign = inputstr[start-1:start]
        if Sign == b"-":
            SignFactor = -1
        else:
            if Sign == b"X":
                SignFactor = 0
    TextStart = start-1+signed
    TextEnd = start-1+len
    # print ("{} {} {} {} {}".format(TextStart,TextEnd, factor, offset, signed))
    return round(int(binascii.hexlify(inputstr[TextStart:TextEnd]), 16)*factor-offset, 3)*SignFactor



def avgData(dictData):
    for key in dictData:
        if isinstance(dictData[key], list):
            dictData[key] = round( sum(dictData[key]) / len(dictData[key]), 3)
#    print (dictData)
    return dictData


def decodeAndAppendData(rawdata, dicData):
    dicData.setdefault("TotalVoltage", parse_value(rawdata, 1, 3, factor=0.005))
    dicData.setdefault("CurrentIN", []).append(parse_value(rawdata, 4, 3, factor=0.125, signed=True))
    dicData.setdefault("CurrentOUT", []).append(parse_value(rawdata, 7, 3, factor=0.125, signed=True))
    dicData.setdefault("CurrentDELTA", []).append(parse_value(rawdata, 10, 3, factor=0.125, signed=True))
    dicData.setdefault("Cell Vmin", parse_value(rawdata, 13, 2, factor=0.005))
    dicData.setdefault("Cell No Vmin", parse_value(rawdata, 15, 1))
    dicData.setdefault("Cell Vmax", parse_value(rawdata, 16, 2, factor=0.005))
    dicData.setdefault("Cell No Vmax", parse_value(rawdata, 18, 1))
    dicData.setdefault("Cell Tmin", parse_value(rawdata, 19, 2, offset=276))
    dicData.setdefault("Cell No Tmin", parse_value(rawdata, 21, 1))
    dicData.setdefault("Cell Tmax", parse_value(rawdata, 22, 2, offset=276))
    dicData.setdefault("Cell No Tmax", parse_value(rawdata, 24, 1))
    dicData.setdefault("No off cells", parse_value(rawdata, 26, 1))
    cellNo = str(parse_value(rawdata, 25, 1))
    dicData.setdefault("Cell"+cellNo+"Voltage", []).append(parse_value(rawdata, 27, 2, factor=0.005))
    dicData.setdefault("Cell"+cellNo+"Temp", []).append(parse_value(rawdata, 29, 2, offset=276))
    dicData.setdefault("TodayEnergy collected", parse_value(rawdata, 32, 3))
    dicData.setdefault("Energy stored", parse_value(rawdata, 35, 3))
    dicData.setdefault("Today Energy consumed", parse_value(rawdata, 38, 3))
    dicData.setdefault("SOC", parse_value(rawdata, 41, 1))
    dicData.setdefault("Total collected", parse_value(rawdata, 42, 3))
    dicData.setdefault("Total consumed", parse_value(rawdata, 45, 3))
    #print_time(raw_data, 48,2,"Device time MM:SS")
    # print (parse_value(rawdata, 48, 1))
    # print (parse_value(rawdata, 49, 1))
    #print_numbers(rawdata, 50,2,0.1, "")
    dicData.setdefault("V-MIN Setting", parse_value(rawdata, 52, 2, factor=0.005))
    dicData.setdefault("V-MAX Setting", parse_value(rawdata, 54, 2, factor=0.005))
    dicData.setdefault("V-Bypass Setting", parse_value(rawdata, 56, 2, factor=0.005))
    dicData.setdefault("Status", parse_value(rawdata, 31, 1))
    return dicData

def sendData2webservice(data123, node_name):
    data = json.dumps(data123)
    myurl = '{}{}'.format(
        emoncsm_url,
        urlencode({'node': node_name, 'time': int(time.time()), 'fulljson': data, 'apikey': emoncsm_apikey})
    )
    # print (myurl)
    try:
        r = requests.get(myurl)
        #print (r)
    except requests.exceptions.RequestException as e:  # This is the correct syntax
        logging.Error("Webservice Fehler URL:{} ERROR:{}".format(e, myurl))
        time.sleep(5)
    return

def readSerialData(SerialConsole):
    rawdata = b''
    SerialByte = b''
    ErrorCounter = 0
    NewRecord = 0

    while True:
        SerialByte = SerialConsole.read()
        #print(binascii.hexlify(SerialByte), end = '')
        if (SerialByte == b''):
            NewRecord += 1

        if (SerialByte == b''  and rawdata != b'') or (len(rawdata) == 58) or (len(rawdata) >= 1000):
#            logging.debug("Value as HEX [{:2d}, {:2d}]: {}".format(ErrorCounter, len(rawdata), binascii.hexlify(rawdata)))
#            print(rawdata[0])
#            print(rawdata[25])
            if (len(rawdata) == 58):
                if isCheckSumOK(rawdata):
                    logging.debug("INPUT OK [NEW:{:1d}, ERR:{:2d}, LEN:{:2d}]: {} " . format(NewRecord, ErrorCounter, len(rawdata), binascii.hexlify(rawdata)))
                    return rawdata
                else:
                    logging.warning(, "INPUT Error [NEW:{:1d}, ERR:{:2d}, LEN:{:2d}]: {} " . format(NewRecord, ErrorCounter, len(rawdata), binascii.hexlify(rawdata)))
                    rawdata = b''
                    SerialByte = b''
                    ErrorCounter += 1
                    if NewRecord < 2:
                        time.sleep(0.5)
            elif (len(rawdata) < 58):
                if ErrorCounter > 0:
                    logging.warning(,"INPUT too short[NEW:{:1d}, ERR:{:2d}, LEN:{:2d}]: {} " . format(NewRecord, ErrorCounter, len(rawdata), binascii.hexlify(rawdata)))
                rawdata = b''
                ErrorCounter += 1
            elif len(rawdata) > 1000: 
                SerialConsole.close()
                SerialConsole.open()  
                logging.warning(, "Serial Error: Starting Point not found after {} Bytes. Closing / Opening USB Device " . format(len(rawdata)))
                rawdata = b''
                SerialByte = b''
                ErrorCounter += 1                
            elif len(rawdata) > 58: 
                logging.warning("INPUT too long [NEW:{:1d}, ERR:{:2d}, LEN:{:2d}]: {} " . format(NewRecord, ErrorCounter, len(rawdata), binascii.hexlify(rawdata)))
                rawdata = b''
                ErrorCounter += 1
            else:
                logging.critical,"Error Unexpected ELSE Statement in readSerialData()")

            NewRecord=0

            if ErrorCounter == 10: 
                SerialConsole.close()
                SerialConsole.open()  
                logging.critical, "Serial Error: Too many Errors ({}). Closing / Opening USB Device " . format(ErrorCounter))
                rawdata = b''
                SerialByte = b''

            if ErrorCounter > 20: 
                logging.critical( "TOO MANY READ ERRORS - QUIT APP [NEW:{:1d}, ERR:{:2d}, LEN:{:2d}]: {} " . format(NewRecord, ErrorCounter, len(rawdata), binascii.hexlify(rawdata)))
                sys.exit(1)


        rawdata = rawdata + SerialByte

def openSerial(DevicePort):
    SerialCon = serial.Serial(
        port=DevicePort, baudrate=9600,
        parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS,
        timeout=0.1
    )
    return SerialCon

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
    #file_name_format = '{year:04d}{month:02d}{day:02d}-{hour:02d}{minute:02d}{second:02d}.log'
    file_name = '123smartbms.log'
    solar_logger.logger_setup(file_name, '/home/pi/')
    # logging.debug('Debug messages are only sent to the logfile.')
    # logging.info('Info messages are not shown on the console, too.')
    # logging.warning('Warnings appear both on the console and in the logfile.')
    # logging.error('Errors get the same treatment.')
    # logging.critical('And critical messages, of course.')
    SerialCon = openSerial(serialPort)
    joinedRecord = dict()
    singleRecord = b""
    collectcycle = 0
    fileout = open("/home/pi/123smartbms.log", "a")
    logging.info("Starting 123SmartBMS Monitoring")
    try:
        while True:
            singleRecord = readSerialData(SerialCon)
            collectcycle += 1
    #       print (collectcycle)
            if ShowDebug: print("New Record [{:2d}]: {} " . format(collectcycle, binascii.hexlify(singleRecord)))

            joinedRecord = decodeAndAppendData(singleRecord, joinedRecord)
            if collectcycle >= 1:
#            if collectcycle >= 12:
    #            print(joinedRecord)
                # Collect and aggregate 10 data records to get all cell infos (cell 1 -4))
                # and minimize webservice load
                joinedRecord = avgData(joinedRecord)
            #    print(joinedRecord)
                logging.Debug(, "DATA: {}".format(json.dumps(joinedRecord)))
                sendData2webservice(joinedRecord, emoncsm_node)
                collectcycle = 0
                joinedRecord.clear()
            # print ("DEBUG: Wait 0.5 sec")
            # time.sleep(0.5)
    except KeyboardInterrupt:
        # Programm wird beendet wenn CTRL+C gedrückt wird.
        print('Datensammlung wird beendet')
    except Exception as e:
        print(str(e))
        sys.exit(1)
    finally:
        # Das Programm wird hier beendet, sodass kein Fehler in die Console geschrieben wird.
        fileout.close()
        SerialCon.close()
        print('Programm wird beendet.')
        sys.exit(0)
