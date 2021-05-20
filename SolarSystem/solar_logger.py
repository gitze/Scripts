#!/usr/bin/python3
# -*- coding: utf-8 -*-
#import time
import gzip
import logging.handlers
import os
import sys

# Define the default logging message formats.
#file_msg_format = '%(asctime)s %(levelname)-8s: %(message)s'
#file_msg_format = '[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s'
file_msg_format = '%(asctime)s|%(levelname)s|%(threadName)s|%(name)s.%(funcName)s:%(lineno)d|%(message)s'
console_msg_format = '%(levelname)s - %(processName)s - %(threadName)s - %(message)s'
console_msg_format = '%(levelname)s: %(message)s'
logger = 0

# Define the log rotation criteria.
# max_bytes=1024**2
# max_bytes=2000
backup_count = 10


class GZipRotator:
    def __call__(self, source, dest):
        os.rename(source, dest)
        f_in = open(dest, 'rb')
        f_out = gzip.open("%s.gz" % dest, 'wb')
        f_out.writelines(f_in)
        f_out.close()
        f_in.close()
        os.remove(dest)


def logger_setup(dir='/var/log', LogFileLevel=logging.DEBUG, ErrorFileLevel=logging.ERROR, ConsoleLevel=logging.INFO):
    """ Set up dual logging to console and to logfile.
    When this function is called, it first creates the given logging output directory. 
    It then creates a logfile and passes all log messages to come to it. 
    The name of the logfile encodes the date and time when it was created, for example "20181115-153559.log". 
    All messages with a certain minimum log level are also forwarded to the console.
    Args:
        dir: path of the directory where to store the log files. Both a
            relative or an absolute path may be specified. If a relative path is
            specified, it is interpreted relative to the working directory.
            Defaults to "log".
        minLevel: defines the minimum level of the messages that will be shown on the console. Defaults to WARNING. 
    """

    # Create the root logger.
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    Formatter_Console = logging.Formatter(console_msg_format)
    Formatter_File = logging.Formatter(file_msg_format)

    # Validate the given directory.
    dir = os.path.normpath(dir)

    # Create a folder for the logfiles.
    if not os.path.exists(dir):
        os.makedirs(dir)

    # Construct the name of the logfile.
    # file_name = os.path.join(dir, file_name)
    script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
    file_name = os.path.join(dir, script_name + "_log.txt")
    file_name_error = os.path.join(dir, script_name + "_errorlog.txt")

    # Set up logging to the logfile.
    #file_handler = RotatingFileHandler(file_name, maxBytes=max_bytes, backupCount=backup_count)
    file_handler = logging.handlers.TimedRotatingFileHandler(
        file_name, when="midnight", backupCount=backup_count)
    file_handler.setLevel(LogFileLevel)
    file_handler.setFormatter(Formatter_File)
    file_handler.rotator = GZipRotator()
    logger.addHandler(file_handler)

    # Set up logging to the logfile.
    #file_handler = RotatingFileHandler(file_name, maxBytes=max_bytes, backupCount=backup_count)
    file_handlerError = logging.handlers.TimedRotatingFileHandler(
        file_name_error, when="midnight", backupCount=backup_count)
    file_handlerError.setLevel(ErrorFileLevel)
    file_handlerError.setFormatter(Formatter_File)
    file_handlerError.rotator = GZipRotator()
    logger.addHandler(file_handlerError)

    # Set up logging to the console.
    console = logging.StreamHandler()
    console.setLevel(ConsoleLevel)
    console.setFormatter(Formatter_Console)
    logger.addHandler(console)
