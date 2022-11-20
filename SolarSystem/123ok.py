#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import signal
import serial
import serial.tools.list_ports
import sys
import binascii
import json
import time
import datetime
import configparser
import logging
import solar_logger
import solar_threadhandler


# ###########################
# Config Parameter
# ###########################
emoncsm_apikey = "apikey"
emoncsm_node = "node_name"
emoncsm_url = "https://url"

config = configparser.ConfigParser()
config.read('/opt/solar/emoncms.conf')
emoncsm_apikey = config.get(
    'DEFAULT',     'emoncsm_apikey', fallback=emoncsm_apikey)
emoncsm_url = config.get('DEFAULT',     'emoncsm_url',    fallback=emoncsm_url)
emoncsm_node = config.get(
    '123SmartBMS', 'emoncsm_node',   fallback=emoncsm_node)

extendetChecks = True
USBDeviceName = ["123SmartBMS Controller"]

ShowDebug = False

# ###########################
# Functions
# ###########################


# ###########################


def findSerialDevices(SearchPhraseArray=["VE Direct cable"]):
    # SearchTerms = len(SearchPhraseArray)
    for SearchPhrase in SearchPhraseArray:
        #        print(SearchPhrase)
        SearchPhrase = "(?i)" + SearchPhrase  # forces case insensitive
#        lines = len(list(serial.tools.list_ports.grep(SearchPhrase)))
#        print (lines)
        for port in serial.tools.list_ports.grep(SearchPhrase):
            USBPortId = port[0]
            return USBPortId
    return None


def jprint(obj):
    # create a formatted string of the Python JSON object
    text = json.dumps(obj, sort_keys=True, indent=4)
    print(text)


# returns total mod 256 as checksum
# http://code.activestate.com/recipes/52251-simple-string-checksum/
def checksum256(the_bytes):
    return b'%02X' % (sum(the_bytes) & 0xFF)


def isCheckSumOK(rawdata):
    checksumCalc = checksum256(rawdata[:-1]).upper()
    checksumComp = binascii.hexlify(rawdata[-1:]).upper()
    checkRecordOK = checksumCalc == checksumComp

    if not checkRecordOK:
        logger.warning("INPUT CRC Error: Calc {} Compare {} - Ergebnis: {}".format(
            checksumCalc, checksumComp, checkRecordOK))
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
            logger.warning("INPUT Quality Error: Extended Quality Check failed Voltage {}, No Battery {}".format(
                rawdata[0], rawdata[25]))
            checkRecordOK = False
        extendetCheckOK = True and (
            # rawdata[5-1] <= 8) and (rawdata[8-1] <= 8) and (rawdata[11-1] <= 8)
            rawdata[5-1] <= 8) and (rawdata[11-1] <= 8)
        if not extendetCheckOK:
            logger.warning("INPUT Quality Error: Extended Quality Check failed Current values {}, {}, {}".format(
                rawdata[5-1], rawdata[8-1], rawdata[11-1]))
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
    RawNumber = int(binascii.hexlify(inputstr[TextStart:TextEnd]), 16)
    if signed:
        if RawNumber > 32767:
            RawNumber = 65535 - RawNumber + 1 
            SignFactor = SignFactor * (-1)
    return round(RawNumber*factor-offset, 3)*SignFactor


def avgData(dictData):
    for key in dictData:
        if isinstance(dictData[key], list):
            dictData[key] = round(sum(dictData[key]) / len(dictData[key]), 3)
    return dictData


def isKthBitSet(number, searchBit, testValue=1):
    new_num = number >> (searchBit)  # K: 0 .. 7
    # new_num = n >> (k - 1)  : K = 1 .. 8
    # if it results to '1' then bit is set,
    # else it results to '0' bit is unset
    return (new_num & testValue)


def decodeAndAppendData(rawdata, dicData):
    dicData.setdefault("TotalVoltage", parse_value(
        rawdata, 1, 3, factor=0.005))
    dicData.setdefault("CurrentIN", []).append(parse_value(rawdata, 4, 3, factor=0.125, signed=True))
    dicData.setdefault("CurrentOUT", []).append(parse_value(rawdata, 7, 3, factor=0.125, signed=True))
    dicData.setdefault("CurrentDELTA", []).append(parse_value(rawdata, 10, 3, factor=0.125, signed=True))
    dicData.setdefault("Cell Vmin", parse_value(rawdata, 13, 2, factor=0.005))
    dicData.setdefault("Cell No Vmin", parse_value(rawdata, 15, 1))
    dicData.setdefault("Cell Vmax", parse_value(rawdata, 16, 2, factor=0.005))
    dicData.setdefault("Cell No Vmax", parse_value(rawdata, 18, 1))
    dicData.setdefault("Cell Tmin", parse_value(rawdata, 19, 2, factor=0.857, offset=232))
    dicData.setdefault("Cell No Tmin", parse_value(rawdata, 21, 1))
    dicData.setdefault("Cell Tmax", parse_value(rawdata, 22, 2, factor=0.857, offset=232))
    dicData.setdefault("Cell No Tmax", parse_value(rawdata, 24, 1))
    dicData.setdefault("No off cells", parse_value(rawdata, 26, 1))
    cellNo = str(parse_value(rawdata, 25, 1))
    dicData.setdefault("Cell"+cellNo+"Voltage", []).append(parse_value(rawdata, 27, 2, factor=0.005))
    dicData.setdefault("Cell"+cellNo+"Temp", []).append(parse_value(rawdata, 29, 2, factor=0.857, offset=232))
    dicData.setdefault("TodayEnergy collected", parse_value(rawdata, 32, 3))
    dicData.setdefault("Energy stored", parse_value(rawdata, 35, 3))
    dicData.setdefault("Today Energy consumed", parse_value(rawdata, 38, 3))
    dicData.setdefault("SOC", parse_value(rawdata, 41, 1))
    dicData.setdefault("Total collected", parse_value(rawdata, 42, 3))
    dicData.setdefault("Total consumed", parse_value(rawdata, 45, 3))
    # print_time(raw_data, 48,2,"Device time MM:SS")
    # print (parse_value(rawdata, 48, 1))
    # print (parse_value(rawdata, 49, 1))
    # print_numbers(rawdata, 50,2,0.1, "")
    dicData.setdefault(
        "V-MIN Setting", parse_value(rawdata, 52, 2, factor=0.005))
    dicData.setdefault(
        "V-MAX Setting", parse_value(rawdata, 54, 2, factor=0.005))
    dicData.setdefault("V-Bypass Setting",
                       parse_value(rawdata, 56, 2, factor=0.005))
    dicData.setdefault("Status", parse_value(rawdata, 31, 1))

    dicData.setdefault("Status Charge", isKthBitSet(dicData.get("Status"), 0))
    dicData.setdefault("Status Discharge",
                       isKthBitSet(dicData.get("Status"), 1))
    dicData.setdefault("Communication Error",
                       isKthBitSet(dicData.get("Status"), 2))
    dicData.setdefault("Status Voltage MIN",
                       isKthBitSet(dicData.get("Status"), 3))
    dicData.setdefault("Status Voltage MAX",
                       isKthBitSet(dicData.get("Status"), 4))
    dicData.setdefault("Status Temp MIN",
                       isKthBitSet(dicData.get("Status"), 5))
    dicData.setdefault("Status Temp MAX",
                       isKthBitSet(dicData.get("Status"), 6))
    dicData.setdefault("SOC not calibrated",
                       isKthBitSet(dicData.get("Status"), 7))

    return dicData


def readSerialData(SerialConsole):
    rawdata = b''
    SerialByte = b''
    ErrorCounter = 0
    NewRecord = 0

    while True:
        SerialByte = SerialConsole.read()
        if (SerialByte == b'' and NewRecord > 10):
            print(f"readSerialData is empty - try{NewRecord}")
        # print(binascii.hexlify(SerialByte), end = '')
        if (SerialByte == b''):
            NewRecord += 1
        if (SerialByte == b'' and rawdata != b'') or (len(rawdata) == 58) or (len(rawdata) >= 1000):
            #            logger.debug("Value as HEX [{:2d}, {:2d}]: {}".format(ErrorCounter, len(rawdata), binascii.hexlify(rawdata)))
            #            print(rawdata[0])
            #            print(rawdata[25])
            if (len(rawdata) == 58):
                if isCheckSumOK(rawdata):
                    logger.debug("INPUT OK [NEW:{:1d}, ERR:{:2d}, LEN:{:2d}]: {} " . format(
                        NewRecord, ErrorCounter, len(rawdata), binascii.hexlify(rawdata)))
                    return rawdata
                else:
                    logger.warning("INPUT Error [NEW:{:1d}, ERR:{:2d}, LEN:{:2d}]: {} " . format(
                        NewRecord, ErrorCounter, len(rawdata), binascii.hexlify(rawdata)))
                    rawdata = b''
                    SerialByte = b''
                    ErrorCounter += 1
                    if NewRecord < 2:
                        time.sleep(0.5)
            else:
                ErrorCounter += 1
                errortext = "too short" if (
                    (len(rawdata) < 58) and (ErrorCounter > 1)) else "too long"
                logger.warning("INPUT {:10}[NEW:{:1d}, ERR:{:2d}, LEN:{:2d}]: {} " . format(
                    errortext, NewRecord, ErrorCounter, len(rawdata), binascii.hexlify(rawdata)))
                if len(rawdata) > 1000:
                    SerialConsole.close()
                    SerialConsole.open()
                rawdata = b''
                SerialByte = b''

            NewRecord = 0

            if ErrorCounter == 10:
                SerialConsole.close()
                SerialConsole.open()
                logger.critical(
                    "Serial Error: Too many Errors ({}). Closing / Opening USB Device " . format(ErrorCounter))
                rawdata = b''
                SerialByte = b''

            if ErrorCounter > 20:
                logger.critical("TOO MANY READ ERRORS - QUIT APP [NEW:{:1d}, ERR:{:2d}, LEN:{:2d}]: {} " . format(
                    NewRecord, ErrorCounter, len(rawdata), binascii.hexlify(rawdata)))
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


def handle_exit(sig, frame):
    raise(SystemExit)


signal.signal(signal.SIGTERM, handle_exit)
# ###########################
# Main
# ###########################
if __name__ == '__main__':
    # create logger
    logger = logging.getLogger(__name__)
    solar_logger.logger_setup('/home/pi/', LogFileLevel=logging.DEBUG, ErrorFileLevel=logging.ERROR, ConsoleLevel=logging.INFO)
    # 'application' code
    logger.info("Starting 123SmartBMS Monitoring")
    serialPort = getSerialPort()
    SerialCon = openSerial(serialPort)
    joinedRecord = dict()
    singleRecord = b""
    collectcycle = 0
#    fileout = open("/home/pi/123smartbms.log", "a")
    EmonCMS = solar_threadhandler.DataLoggerQueue("123smartbms", emoncsm_url, emoncsm_apikey)
    EmonCMS.StartQueue()
    try:
        while True:
            if EmonCMS.isAlive() is False:
                logger.error("ERROR: solar_threadhandler is not running anymore")
                raise (SystemExit)
            # if EmonCMS.queueSize() > 1000:
            #     printvars()
#            logger.debug("Record Sammeln: Start")
            singleRecord = readSerialData(SerialCon)
#            logger.debug("Record Sammeln: ENDE")
            collectcycle += 1
            # print(collectcycle)
            if ShowDebug:
                print("New Record [{:2d}]: {} " . format(collectcycle, binascii.hexlify(singleRecord)))
            joinedRecord = decodeAndAppendData(singleRecord, joinedRecord)
            if collectcycle >= 4:
                # Collect and aggregate 10 data records to get all cell infos (cell 1 -4))
                # and minimize webservice load
                joinedRecord = avgData(joinedRecord)
#                logger.debug("DATA: {}".format(json.dumps(joinedRecord)))
                EmonCMS.addDataQueue(joinedRecord, emoncsm_node)
                collectcycle = 0
                joinedRecord.clear()
    except KeyboardInterrupt:
        # Programm wird beendet wenn CTRL+C gedrückt wird.
        logger.info('Warte auf Ende von DataLoggerQueueProcessing')
        EmonCMS.StopQueue()
        logger.info('Datensammlung wird beendet')
    except Exception as e:
        logger.critical(f'Unerwarteter Abbruch: {str(e)}')
        EmonCMS.StopQueue(forceStop=True)
        sys.exit(1)
    except (KeyboardInterrupt, SystemExit):
        logger.info('Programm Abbruch wird eingeleitet')
    finally:
        # Das Programm wird hier beendet, sodass kein Fehler in die Console geschrieben wird.
        EmonCMS.StopQueue(forceStop=True)
        SerialCon.close()
        logger.info('Programm wurde beendet.')
        sys.exit(0)
