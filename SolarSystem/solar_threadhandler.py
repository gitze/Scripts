#!/usr/bin/python3
# -*- coding: utf-8 -*-
#import time
#import sys
import os
import logging.handlers
import threading


# ###########################
DataLoggerQueue = []
DataLoggerQueueProcessing = 1
DataLoggerTestRun = 1
DataLoggerQueueMaxSize = 2*1024*1024
DataLoggerQueueReduction = 0.1


def addDataQueue(inputdata, node_name):
    global DataLoggerQueue
    global DataLoggerQueueProcessing

    QueueItem = []
    QueueItem.append(json.dumps(inputdata))
    QueueItem.append(int(time.time()))
    QueueItem.append(node_name)
    DataLoggerQueue.append(QueueItem)
    QueueSize = asizeof.asizeof(DataLoggerQueue)
    QueueLength = len(DataLoggerQueue)
#    print(f"Add Queue Length: {QueueLength} ({QueueSize} bytes)")
    if (QueueSize > DataLoggerQueueMaxSize):
        del DataLoggerQueue[:(round(QueueLength*DataLoggerQueueReduction))]
        QueueSize = asizeof.asizeof(DataLoggerQueue)
        QueueLength = len(DataLoggerQueue)
        logging.warning(f"New Queue Length: {QueueLength} ({QueueSize} bytes)")


def sendDataQueue():
    global DataLoggerQueue
    global DataLoggerQueueProcessing
    global DataLoggerTestRun

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

    currentItem = DataLoggerQueue.pop()
    # print(f"POP Queue Length: {len(DataLoggerQueue)}")
    inputdata = currentItem[0]
    inputtime = currentItem[1]
    inputnode = currentItem[2]

    myurl = '{}{}'.format(
        emoncsm_url,
        urlencode({'node': inputnode, 'apikey': emoncsm_apikey,
                   'time': inputtime, 'fulljson': inputdata})
    )
    # print(myurl)
    try:
        r = requests.get(myurl)
#        print(f"Rerquest Response: {r.status_code} {r.text}")
        r.raise_for_status()
    except requests.exceptions.RequestException as e:  # This is the correct syntax
        logging.error(f"Webservice Fehler URL:{myurl} ERROR:{e}")
        DataLoggerQueue.append(currentItem)
        time.sleep(10)
    return


def backgroudDataQueue():
    global DataLoggerQueue
    global DataLoggerQueueProcessing

    while (DataLoggerQueueProcessing > 0):
        if (len(DataLoggerQueue) > 0):
            sendDataQueue()
            if(DataLoggerQueueProcessing == 1):
                logging.warning(
                    f"EXIT Queue - Length: {len(DataLoggerQueue)} ({str(sys.getsizeof(DataLoggerQueue))} bytes) {asizeof.asizeof(DataLoggerQueue)}")
        elif(DataLoggerQueueProcessing == 1):
            return


# ###########################
