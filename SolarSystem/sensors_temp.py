#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import json
import requests
from urllib.parse import urlencode, quote_plus
import time
import datetime
import configparser

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
emoncsm_node   = config.get('Sensors', 'emoncsm_node',   fallback = emoncsm_node)

extendetCheks = True
# ###########################

# ###########################
# Input Parameter
# ###########################
# Systempfad zum den Sensor, weitere Systempfade könnten über ein Array
# oder weiteren Variablen hier hinzugefügt werden.
# 28-02161f5a48ee müsst ihr durch die eures Sensors ersetzen!
sensor1 = '/sys/bus/w1/devices/28-011563ff9cff/w1_slave'
sensor2 = '/sys/bus/w1/devices/28-031563c316ff/w1_slave'
sensor3 = '/sys/bus/w1/devices/28-031563c350ff/w1_slave'
#tsensor4 = '/sys/bus/w1/devices/28-02161f5a48ee/w1_slave'


if len(sys.argv) < 2:
    print("Using default device /dev/ttyUSB0")
    Device = "/dev/ttyUSB0"
else:
    Device = sys.argv[1]
    print("Using device {}".format(Device))


# ###########################
# Functions
# ###########################

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



def decodeAndAppendData(rawdata, dicData):
    dicData.setdefault("TotalVoltage", parse_value(rawdata, 1, 3, factor=0.005))
    dicData.setdefault("CurrentIN", []).append(parse_value(rawdata, 4, 3, factor=0.125, signed=True))
    dicData.setdefault("CurrentOUT", []).append(parse_value(rawdata, 7, 3, factor=0.125, signed=True))
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
        logit(fileout,"Webservice Fehler URL:{} ERROR:{}".format(e, myurl))
        print("Webservice Fehler URL:{} ERROR:{}".format(e, myurl))
        time.sleep(5)
    return


def logit(filehandler, logvalue):
    filehandler.write(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ":" + logvalue + "\n")
    filehandler.flush()
    print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ":" + logvalue)

def readTempSensor(sensorName) :
    """Aus dem Systembus lese ich die Temperatur der DS18B20 aus."""
    f = open(sensorName, 'r')
    lines = f.readlines()
    f.close()
    return lines

def readTempLines(sensorName) :
    lines = readTempSensor(sensorName)
    # Solange nicht die Daten gelesen werden konnten, bin ich hier in einer Endlosschleife
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = readTempSensor(sensorName)
    temperaturStr = lines[1].find('t=')
    # Ich überprüfe ob die Temperatur gefunden wurde.
    if temperaturStr != -1 :
        tempData = lines[1][temperaturStr+2:]
        tempCelsius = float(tempData) / 1000.0
        tempKelvin = 273 + float(tempData) / 1000
        tempFahrenheit = float(tempData) / 1000 * 9.0 / 5.0 + 32.0
        # Rückgabe als Array - [0] tempCelsius => Celsius...
        return [tempCelsius, tempKelvin, tempFahrenheit]



# ###########################
# Main
# ###########################
if __name__ == '__main__':
    joinedRecord = dict()
    fileout = open("/home/pi/temp_sensors.log", "a")
    logit(fileout, "Starting Temeratur Sensor Monitoring")
    try:
        while True:
            joinedRecord.setdefault("Temp1", readTempLines(sensor1)[0])
            joinedRecord.setdefault("Temp2", readTempLines(sensor2)[0])
            joinedRecord.setdefault("Temp3", readTempLines(sensor3)[0])
            print(joinedRecord)
            logit(fileout, "DATA: {}".format(json.dumps(joinedRecord)))
            sendData2webservice(joinedRecord, emoncsm_node)
            joinedRecord.clear()
            # print ("DEBUG: Wait 0.5 sec")
            time.sleep(10)
    except KeyboardInterrupt:
        # Programm wird beendet wenn CTRL+C gedrückt wird.
        print('Datensammlung wird beendet')
    except Exception as e:
        print(str(e))
        sys.exit(1)
    finally:
        # Das Programm wird hier beendet, sodass kein Fehler in die Console geschrieben wird.
        fileout.close()
        print('Programm wird beendet.')
        sys.exit(0)
