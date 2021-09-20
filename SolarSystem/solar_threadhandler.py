#!/usr/bin/python3
# -*- coding: utf-8 -*-
# import time
# import sys
import os
import json
import requests
from urllib.parse import urlencode, quote_plus
import time
import threading
from pympler import asizeof
import dill

import logging
# logger = logging.getLogger("solarlogger")
logger = logging.getLogger(__name__)

logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


def HandleThreadingException(args):
    logger.error(f'ERROR, Threading died unexpected. Caught {args.exc_type} with value {args.exc_value} in thread {args.thread}\n')
    raise(SystemExit)
threading.excepthook = HandleThreadingException


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
        self.DataLoggerQueueMaxSize = 500*1024*1024
        self.DataLoggerQueueReduction = 0.2
        self.DataLoggerQueueReductionStep = 2
        self.QueueMgmt = 0
        self.lock = threading.Lock()

    def queueAddItem(self, QueueItem):
        self.lock.acquire()
        try:
            self.DataLoggerQueue.append(QueueItem)
        finally:
            self.lock.release()        

    def queueRetrieveItem(self):
        self.lock.acquire()
        try:
            currentItem = self.DataLoggerQueue.pop()
        finally:
            self.lock.release()        
            return currentItem

    def addDataQueue(self, inputdata, node_name):
        QueueItem = []
        QueueItem.append(json.dumps(inputdata))
        QueueItem.append(int(time.time()))
        QueueItem.append(node_name)
        self.queueAddItem(QueueItem)
        # self.DataLoggerQueue.append(QueueItem)
        QueueSize = asizeof.asizeof(self.DataLoggerQueue)
        QueueLength = len(self.DataLoggerQueue)
        logger.debug(
            f"addDataQueue: New Queue Length: {QueueLength} ({QueueSize}/{self.DataLoggerQueueMaxSize} bytes)")
        # print(getouterframes(sys._getframe(1), 1))
        if (QueueSize > self.DataLoggerQueueMaxSize):
            QueueReduction = round(
                QueueLength * self.DataLoggerQueueReduction) * self.DataLoggerQueueReductionStep
            logger.info(
                f"addDataQueue: Warning: Queue too long - Length: {QueueLength} ({QueueSize}/{self.DataLoggerQueueMaxSize} bytes)")
            logger.info(
                f"addDataQueue: Queue cleanup {QueueReduction} items")

            # del self.DataLoggerQueue[:(
            #     round(QueueLength*self.DataLoggerQueueReduction))]
            del self.DataLoggerQueue[:QueueReduction:
                                     self.DataLoggerQueueReductionStep]

            QueueSize = asizeof.asizeof(self.DataLoggerQueue)
            QueueLength = len(self.DataLoggerQueue)
            logger.warning(
                f"addDataQueue: New Queue Length: {QueueLength} ({QueueSize}/{self.DataLoggerQueueMaxSize} bytes)")
        logger.debug("addDataQueue: END")

    def sendDataQueue(self):
        logger.debug("sendDataQueue: Start")
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

        logger.debug(
            f"sendDataQueue: Send Data - Length: {len(self.DataLoggerQueue)}")
        currentItem = self.queueRetrieveItem()
        inputdata = currentItem[0].encode("utf-8")
        inputtime = currentItem[1]
        inputnode = currentItem[2]

        myurl = '{}{}'.format(
            self.url,
            urlencode({'node': inputnode, 'apikey': self.apikey,
                       'time': inputtime, 'fulljson': inputdata})
        )
        try:
            r = requests.get(myurl, timeout=5)
            logger.debug(f"sendDataQueue: Request: {myurl}")
            logger.debug(f"sendDataQueue: Request Response: {r.text}")
            r.raise_for_status()
        # except requests.exceptions.Timeout as e:
        #     logger.error(
        #         f"sendDataQueue: Webservice Timeout URL:{myurl} ERROR:{e}")
        #     self.queueAddItem(QueueItem)
        #     time.sleep(10)            
        # except requests.exceptions.RequestException as e:  # This is the correct syntax
        #     logger.error(
        #         f"sendDataQueue: Webservice Fehler URL:{myurl} ERROR:{e}")
        #     self.queueAddItem(QueueItem)
        #     time.sleep(10)            
        except Exception as e:
            self.queueAddItem(currentItem)
            logger.error(f"sendDataQueue: Fehler Code: {e}")
            logger.error(f"sendDataQueue: Fehler URL : {myurl}")
#            time.sleep(10)
        logger.debug("sendDataQueue: END")

    def backgroudDataQueue(self):
        logger.debug("backgroudDataQueue: Start")
        while (self.DataLoggerQueueProcessing > 0):
            QueueLength = len(self.DataLoggerQueue)
            if ((QueueLength > 5) and (QueueLength % 10) == 0):
                # self.dumpDataQueue()
                logger.info(
                    f"Report Queue - Length: {QueueLength} ({asizeof.asizeof(self.DataLoggerQueue)}bytes)")
            if (QueueLength > 0):
                self.sendDataQueue()
                if(self.DataLoggerQueueProcessing == 1):
                    logger.info(
                        f"backgroudDataQueue: Flush Queue - Length: {QueueLength} ({asizeof.asizeof(self.DataLoggerQueue)}bytes)")
            elif(self.DataLoggerQueueProcessing == 1):
                return
        logger.warning(
            f"backgroudDataQueue: ended unexpected DataLoggerQueueProcessing:{self.DataLoggerQueueProcessing}")
        logger.debug("backgroudDataQueue: END")

    def StartQueue(self):
        self.startDataQueue()

    def startDataQueue(self):
        self.DataLoggerQueueProcessing = 2
        self.reloadQueue()
        self.QueueMgmt = threading.Thread(
            name="DataQueue", target=self.backgroudDataQueue, daemon=True)
        self.QueueMgmt.start()

    def FlushQueue(self):
        self.flushDataQueue()

    def flushDataQueue(self):
        self.DataLoggerQueueProcessing = 1
        self.QueueMgmt.join(timeout=60)
        self.dumpDataQueue()

    def dumpDataQueue(self):
        if len(self.DataLoggerQueue) > 0:
            filename = f"/opt/solar/{self.name}-DataLoggerQueue.txt"
            dill.dump(self.DataLoggerQueue, file=open(filename, "wb"))
            logger.info(
                f"Save Data: Dumped {len(self.DataLoggerQueue)} remaining records to file'{filename}'")

    def reloadQueue(self):
        filename = f"/opt/solar/{self.name}-DataLoggerQueue.txt"
        if os.path.exists(filename):
            self.DataLoggerQueue = dill.load(open(filename, "rb"))
            os.remove(filename)
            logger.info(f"Reload {len(self.DataLoggerQueue)} records from file'{filename}'")

        else:
            logger.info(
                f"Reload Data: Nothing to reload - file'{filename}' does not exist")

    def isAlive(self):
        return self.QueueMgmt.is_alive()

    def queueLength(self):
        # print(len(self.DataLoggerQueue))
        return len(self.DataLoggerQueue)
