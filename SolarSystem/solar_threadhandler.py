#!/usr/bin/python3
# -*- coding: utf-8 -*-
# import time
# import sys
import os
import json
import requests
from urllib.parse import urlencode, quote_plus
import time
import logging.handlers
import threading
from pympler import asizeof
import dill


# ###########################
# Define a class
class DataLoggerQueue:
    def __init__(self, collector_name, collector_url, collector_apikey):
        self.name = collector_name
        self.url = collector_url
        self.apikey = collector_apikey
        self.DataLoggerQueue = []
        self.DataLoggerQueueProcessing = 1
        self.DataLoggerTestRun = 1
        self.DataLoggerQueueMaxSize = 2*1024*1024
        self.DataLoggerQueueReduction = 0.2
        self.DataLoggerQueueReductionStep = 2
        self.QueueMgmt = 0

    def addDataQueue(self, inputdata, node_name):
        QueueItem = []
        QueueItem.append(json.dumps(inputdata))
        QueueItem.append(int(time.time()))
        QueueItem.append(node_name)
        self.DataLoggerQueue.append(QueueItem)
        QueueSize = asizeof.asizeof(self.DataLoggerQueue)
        QueueLength = len(self.DataLoggerQueue)
        QueueReduction = round(
            QueueLength * self.DataLoggerQueueReduction) * self.DataLoggerQueueReductionStep
        # print(f"Add Queue Length: {QueueLength} ({QueueSize} bytes)")
        if (QueueSize > self.DataLoggerQueueMaxSize):
            # del self.DataLoggerQueue[:(
            #     round(QueueLength*self.DataLoggerQueueReduction))]
            del self.DataLoggerQueue[:QueueReduction:
                                     self.DataLoggerQueueReductionStep]

            QueueSize = asizeof.asizeof(self.DataLoggerQueue)
            QueueLength = len(self.DataLoggerQueue)
            logging.warning(
                f"New Queue Length: {QueueLength} ({QueueSize} bytes)")

    def sendDataQueue(self):
        currentItem = []

        # if (self.DataLoggerTestRun == 0):
        #     if (len(self.DataLoggerQueue) < 5):
        #         self.DataLoggerTestRun = 1
        # if (self.DataLoggerQueueProcessing < 2):
        #     self.DataLoggerTestRun = 0
        # if (self.DataLoggerTestRun == 1):
        #     if (len(self.DataLoggerQueue) < 20):
        #         return
        #     else:
        #         self.DataLoggerTestRun = 0

        currentItem = self.DataLoggerQueue.pop()
        # print(f"POP Queue Length: {len(DataLoggerQueue)}")
        inputdata = currentItem[0].encode("utf-8")
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

    def backgroudDataQueue(self):
        while (self.DataLoggerQueueProcessing > 0):
            QueueLength = len(self.DataLoggerQueue)
            if ((QueueLength > 5) and (QueueLength % 10) == 0):
                self.dumpDataQueue()
                logging.warning(
                    f"Queue - Length: {QueueLength} ({asizeof.asizeof(self.DataLoggerQueue)}bytes)")
            if (QueueLength > 0):
                self.sendDataQueue()
                if(self.DataLoggerQueueProcessing == 1):
                    logging.warning(
                        f"EXIT Queue - Length: {QueueLength} ({asizeof.asizeof(self.DataLoggerQueue)}bytes)")
            elif(self.DataLoggerQueueProcessing == 1):
                return

    def StartQueue(self):
        self.startDataQueue()

    def startDataQueue(self):
        self.DataLoggerQueueProcessing = 2
        self.QueueMgmt = threading.Thread(
            name="Queue", target=self.backgroudDataQueue, daemon=True)
        self.QueueMgmt.start()

    def FlushQueue(self):
        self.flushDataQueue()

    def flushDataQueue(self):
        self.DataLoggerQueueProcessing = 1
        self.QueueMgmt.join()

    def dumpDataQueue(self):
        if len(self.DataLoggerQueue) > 0:
            i = 0
            filename = f"/opt/solar/{self.name}-DataLoggerQueue%s.dump"
            while os.path.exists(filename % i):
                i += 1
            dill.dump(self.DataLoggerQueue, file=open(filename % i, "wb"))

    def reloadQueue(self):
        # self.DataLoggerQueue = dill.load(open("DataLoggerQueue.pickle", "rb"))
        pass
