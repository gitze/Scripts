#!/usr/bin/python3
# -*- coding: utf-8 -*-
# import time
# import sys
import os
import enum
import json
import requests
from urllib.parse import urlencode, quote_plus
import time
import threading
from pympler import asizeof

import logging
# logger = logging.getLogger("solarlogger")
logger = logging.getLogger(__name__)

logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


def HandleThreadingException(args):
    logger.error(f'ERROR, Threading died unexpected. Caught {args.exc_type} with value {args.exc_value} in thread {args.thread}\n')
    raise(SystemExit)
threading.excepthook = HandleThreadingException


class status(enum.Enum):
   NONE = 0
   OK = 1
   RUN = 10
   FORCE = 12
   END = 98
   ERROR = 99

# ###########################
# Define a class
class DataLoggerQueue:
    def __init__(self, queue_name, api_url, api_key):
        self.name = queue_name
        self.url = api_url
        self.apikey = api_key
        self.DataLoggerQueue = []
        self.DataLoggerQueuelength = 0
        self.DataLoggerAPIStatus = status.OK
        self.DataLoggerAPINextRetry = 0
        self.DataLoggerQueueProcessing = status.RUN
        self.DataLoggerQueueMaxSize = 500*1024*1024
        self.BackgroundQueueManager = 0
        self.lock = threading.Lock()

    # def _text2string(inputtext):
    #     outputstring = inputtext.replace('\n', ' ').replace('\r', '') 
    #     return outputstring

    def _queueAddItem(self, QueueItem):
        self.lock.acquire()
        try:
            self.DataLoggerQueue.append(QueueItem)
            self.DataLoggerQueuelength = len(self.DataLoggerQueue)
        finally:
            self.lock.release()        

    def _queueRetrieveItem(self):
        self.lock.acquire()
        try:
            currentItem = self.DataLoggerQueue.pop()
            self.DataLoggerQueuelength = len(self.DataLoggerQueue)
        finally:
            self.lock.release()
            return currentItem

    def _addDataQueue(self, inputdata, node_name):
        QueueItemDict = {}
        QueueItemDict['table'] = node_name
        QueueItemDict['timestamp'] = int(time.time())
        QueueItemDict['data'] = json.dumps(inputdata)
        self._queueAddItem(QueueItemDict)

        QueueSize = asizeof.asizeof(self.DataLoggerQueue)
        QueueLength = len(self.DataLoggerQueue)
        logger.debug(f"addDataQueue: New Queue Length: {QueueLength} ({QueueSize}/{self.DataLoggerQueueMaxSize} bytes)")
        if (QueueSize > self.DataLoggerQueueMaxSize):
            # A = [1,2,3,4,5,6,7]
            # B = A[:len(A)//2] ==> [1, 2, 3]
            # C = A[len(A)//2:] ==> [4, 5, 6, 7]
            # del A[:len(A)//2] ==> [4, 5, 6, 7]
            # QueueReduction = round(QueueLength * self.DataLoggerQueueReduction) * self.DataLoggerQueueReductionStep
            logger.info(f"addDataQueue: Warning: Queue too long - Length: {QueueLength} ({QueueSize}/{self.DataLoggerQueueMaxSize} bytes)")
            # logger.info(f"addDataQueue: Queue cleanup {QueueReduction} items")
            # del self.DataLoggerQueue[:QueueReduction: self.DataLoggerQueueReductionStep]

            QueueSize = asizeof.asizeof(self.DataLoggerQueue)
            QueueLength = len(self.DataLoggerQueue)
            logger.warning(f"addDataQueue: New Queue Length: {QueueLength} ({QueueSize}/{self.DataLoggerQueueMaxSize} bytes)")
#        logger.debug("addDataQueue: END")

    def _sendDataQueue(self):
#        logger.debug(f"sendDataQueue: Start")
        # If last WEB Call was not successful, don't try until nextRetry time is reached
        if (self.DataLoggerAPIStatus == status.ERROR):            
            logger.debug(f"sendDataQueue: Status: ERROR Next Retry {self.DataLoggerAPINextRetry} Current {int(time.time())}")                
            if (self.DataLoggerAPINextRetry < int(time.time())): self.DataLoggerAPINextRetry = 0
            else: return
        QueueItemDict = self._queueRetrieveItem()
        inputnode = QueueItemDict['table']
        inputtime = QueueItemDict['timestamp']
        inputdata = QueueItemDict['data'].encode("utf-8")

        myurl = '{}{}'.format(
            self.url, urlencode({'node': inputnode, 'apikey': self.apikey, 'time': inputtime, 'fulljson': inputdata})
        )
        try:
            r = requests.get(myurl, timeout=5) # Timeout in "sec"
#            logger.debug(f"sendDataQueue: Request: {myurl}")
            logger.debug(f"sendDataQueue: Timestamp: {inputtime} - Request StatusCode: {r.status_code} - New QueueSize {self.DataLoggerQueuelength }")
            r.raise_for_status()
            self.DataLoggerAPIStatus=status.OK
            self.DataLoggerAPINextRetry = 0
        # except requests.exceptions.Timeout as e:
        # except requests.exceptions.RequestException as e:  # This is the correct syntax
        except Exception as e:
            self._queueAddItem(QueueItemDict)
            logger.error(f"sendDataQueue: Fehler: {e}")
            self.DataLoggerAPIStatus=status.ERROR
            self.DataLoggerAPINextRetry = int(time.time())+30
            logger.debug(f"sendDataQueue: Status: API ERROR - Next Retry {self.DataLoggerAPINextRetry} Current {int(time.time())}")                


    def backgroudDataQueue(self):
        # Background Job
        logger.debug("backgroudDataQueue: Start")
        while True:
            if ((self.DataLoggerQueuelength > 5) and (self.DataLoggerQueuelength % 10) == 0):
                logger.info(f"Report Queue - Length: {self.DataLoggerQueuelength} ({asizeof.asizeof(self.DataLoggerQueue)}bytes)")
            if (self.DataLoggerQueuelength > 0): 
                self._sendDataQueue()
                if (self.DataLoggerAPIStatus == status.ERROR):time.sleep(10)
            if (self.DataLoggerQueuelength == 0):
                if (self.DataLoggerQueueProcessing == status.RUN): time.sleep(10)
                if (self.DataLoggerQueueProcessing == status.END): return


    def _startDataQueue(self):
        self.DataLoggerQueueProcessing = status.RUN
        self._reloadQueue()
        self.BackgroundQueueManager = threading.Thread(name="DataQueue", target=self.backgroudDataQueue, daemon=True)
        self.BackgroundQueueManager.start()


    def _flushDataQueue(self, forceStop):
        if (forceStop == False):
            self.DataLoggerQueueProcessing = status.END # Send 
            self.BackgroundQueueManager.join(timeout=60) # Wait for 60 to settle, then abort
        self._dumpDataQueue() # save remaining items


    def _reloadQueue(self):
        filename = f"/opt/solar/{self.name}-DataLoggerQueue.txt"
        if os.path.exists(filename):
            currentDict = []
            with open(filename) as fp:
                for line in fp:
                    currentDict = json.loads(line)
                    self._queueAddItem(currentDict)
            os.remove(filename)
            logger.info(f"Reload {len(self.DataLoggerQueue)} records from file'{filename}'")
        else:
            logger.info(f"Reload Data: Nothing to reload - file'{filename}' does not exist")


    def _dumpDataQueue(self):
        if len(self.DataLoggerQueue) > 0:
            filename = f"/opt/solar/{self.name}-DataLoggerQueue.txt"
            with open(filename, 'w') as fp:
                for Record in self.DataLoggerQueue:
                    json.dump(Record, fp)
                    fp.write('\n')
            logger.info(f"Save Data: Dumped {len(self.DataLoggerQueue)} remaining records to file'{filename}'")


    def _writeQueueToDisk(self, QueueDataDict):
        with open('/opt/solar/result.json', 'w') as fp:
            for Record in QueueDataDict:
                json.dump(Record, fp)
                logger.debug(f"_writeQueueToDisk: {json.dumps(Record)}")
                fp.write('\n')

    def _readQueueFromDisk(self):
        with open('/opt/solar/result.json') as fp:
            count=0
            currentDict = []
            for line in fp:
                count += 1
                print("Line{}: {}".format(count, line.strip()))            
                # for QueueData in self.DataLoggerQueue:
                #     json.dump(QueueData, fp)
                #     fp.write('\n')


###################
# Public Functions
    def addDataQueue(self, inputdata, node_name):
        self._addDataQueue(inputdata, node_name)

    def StartQueue(self):
        self._startDataQueue()

    def StopQueue(self, forceStop = False):
        self._flushDataQueue(forceStop)
        self.DataLoggerQueue = []
        self.DataLoggerQueuelength = 0


    def isAlive(self):
        return self.BackgroundQueueManager.is_alive()
