#!/usr/bin/env python3
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
import logging.handlers
import solar_logger
import csv
import subprocess


def get_script_path():
    return os.path.dirname(os.path.realpath(sys.argv[0]))

# ###########################
# Config Parameter
# ###########################
emoncsm_apikey = "apikey"
emoncsm_node = "node_name"
emoncsm_url = "https://url"

config = configparser.ConfigParser()
config.read(get_script_path()+'/emoncms.conf')
emoncsm_apikey = config.get('DEFAULT',     'emoncsm_apikey', fallback = emoncsm_apikey)
emoncsm_url    = config.get('DEFAULT',     'emoncsm_url',    fallback = emoncsm_url)
emoncsm_node   = config.get('Sensors',     'emoncsm_node',   fallback = emoncsm_node)
# ###########################

def formatnumber(stringnumber, recalc):
    a_float = float(stringnumber)/recalc
    formatted_float = "{:.2f}".format(a_float)
    return formatted_float

def sendData2webservice(datadict, node_name):
    datajson = json.dumps(datadict)
    # print(datajson)
    myurl = '{}{}'.format(
        emoncsm_url,
        urlencode({'node': node_name, 'time': int(time.time()), 'fulljson': datajson, 'apikey': emoncsm_apikey})
    )
    # print (myurl)
    try:
        r = requests.get(myurl)
        # print (r)
    except requests.exceptions.RequestException as e:  # This is the correct syntax
        logging.error("Webservice Fehler URL:{} ERROR:{}".format(e, myurl))
        time.sleep(5)
    return


# ###########################
# Main
# ###########################
if __name__ == '__main__':
    joinedRecord = dict()
 
    try:
        response = subprocess.run(['/usr/bin/speedtest-cli', '--json'], capture_output=True, encoding='utf-8')
        # if speedtest-cli exited with no errors / ran successfully
        if response.returncode == 0:
            # from the csv man page
            # "And while the module doesn’t directly support parsing strings, it can easily be done"
            # this will remove quotes and spaces vs doing a string split on ','
            # csv.reader returns an iterator, so we turn that into a list
            # cols = list(csv.reader([response.stdout]))[0]
            speed = json.loads(response.stdout)

            print (response.stdout)
            # turns 13.45 ping to 13
            ping = int(float((speed["ping"])))

            # speedtest-cli --csv returns speed in bits/s, convert to bytes
            download = formatnumber(speed["download"],1024*1024)
            upload = formatnumber(speed["upload"],1024*1024)
            joinedRecord.setdefault("Ping", ping)
            joinedRecord.setdefault("Download", download)
            joinedRecord.setdefault("Upload", upload)
            # print(joinedRecord)
            sendData2webservice(joinedRecord, emoncsm_node)
            joinedRecord.clear()
        else:
            print('speedtest-cli returned error: %s' % response.stderr)
    except KeyboardInterrupt:
        # Programm wird beendet wenn CTRL+C gedrückt wird.
        print('Datensammlung wird beendet')
    except Exception as e:
        print(str(e))
        sys.exit(1)
    finally:
        # Das Programm wird hier beendet, sodass kein Fehler in die Console geschrieben wird.
        # print('Programm wird beendet.')
        sys.exit(0)
