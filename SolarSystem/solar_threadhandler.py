#!/usr/bin/python3
# -*- coding: utf-8 -*-
#import time
#import sys
import os
import json
import requests
from urllib.parse import urlencode, quote_plus
import time
import logging.handlers
import threading


# Define a class
class DataLoggerQueue:
    def __init__(self, collector_url, collector_apikey):
        self.url = collector_url
        self.apikey = collector_apikey
        self.DataLoggerQueue = []
        self.DataLoggerQueueProcessing = 1
        self.DataLoggerTestRun = 1
        self.DataLoggerQueueMaxSize = 2*1024*1024
        self.DataLoggerQueueReduction = 0.1
        self.QueueMgmt

    def tell_me_about_the_octopus(self):
        print("This octopus is " + self.color + ".")
        print(self.name + " is the octopus's name.")

    def addDataQueue(self, inputdata, node_name):
        QueueItem = []
        QueueItem.append(json.dumps(inputdata))
        QueueItem.append(int(time.time()))
        QueueItem.append(node_name)
        self.DataLoggerQueue.append(QueueItem)
        QueueSize = asizeof.asizeof(self.DataLoggerQueue)
        QueueLength = len(self.DataLoggerQueue)
    #    print(f"Add Queue Length: {QueueLength} ({QueueSize} bytes)")
        if (QueueSize > self.DataLoggerQueueMaxSize):
            del DataLoggerQueue[:(
                round(QueueLength*self.DataLoggerQueueReduction))]
            QueueSize = asizeof.asizeof(Dself.ataLoggerQueue)
            QueueLength = len(self.DataLoggerQueue)
            logging.warning(
                f"New Queue Length: {QueueLength} ({QueueSize} bytes)")

    def sendDataQueue(self):
        currentItem = []

        # if (DataLoggerTestRun == 0):
        #     if (len(DataLoggerQueue) < 5):
        #         DataLoggerTestRun = 1
        # if (DataLoggerQueueProcessing < 2):
        #     DataLoggerTestRun = 0
        # if (DataLoggerTestRun == 1):
        #     if (len(DataLoggerQueue) < 20):
        #         return
        #     else:
        #         DataLoggerTestRun = 0

        currentItem = self.DataLoggerQueue.pop()
        # print(f"POP Queue Length: {len(DataLoggerQueue)}")
        inputdata = currentItem[0]
        inputtime = currentItem[1]
        inputnode = currentItem[2]

        myurl = '{}{}'.format(
            self.url,
            urlencode({'node': inputnode, 'apikey': self.apikey,
                       'time': inputtime, 'fulljson': inputdata})
        )
        # print(myurl)
        try:
            r = requests.get(myurl)
    #        print(f"Rerquest Response: {r.status_code} {r.text}")
            r.raise_for_status()
        except requests.exceptions.RequestException as e:  # This is the correct syntax
            logging.error(f"Webservice Fehler URL:{myurl} ERROR:{e}")
            self.DataLoggerQueue.append(currentItem)
            time.sleep(10)

    def backgroudDataQueue():
        while (self.DataLoggerQueueProcessing > 0):
            if (len(self.DataLoggerQueue) > 0):
                sendDataQueue()
                if(self.DataLoggerQueueProcessing == 1):
                    logging.warning(
                        f"EXIT Queue - Length: {len(self.DataLoggerQueue)} ({asizeof.asizeof(self.DataLoggerQueue)}bytes)")
            elif(self.DataLoggerQueueProcessing == 1):

    def StartQueue(self):
        self.DataLoggerQueueProcessing = 2
        self.QueueMgmt = threading.Thread(
            name="Queue", target=backgroudDataQueue, daemon=True)
        QueueMgmt.start()

    def FlushQueue(slef):
        self.DataLoggerQueueProcessing = 1
        self.QueueMgmt.join()
