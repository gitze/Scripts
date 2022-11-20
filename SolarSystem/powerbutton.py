#!/usr/bin/python3
# -*- coding: utf-8 -*-

# sudo apt install python3-rpi.gpio
import time
import signal
from datetime import datetime
import sys
import solar_logger
import logging
import solar_cron
import RPi.GPIO as GPIO

Power_state = False
LED_state = False   # Init = LED   is OFF
RELAY_state = False  # Init = Relay is OFF
MANUAL_state = False
AUTOMATIC_state = False
AUTOMATIC_duration = 10  # in Minutes
#AUTOMATIC_run_range = range(32, 32 + AUTOMATIC_duration)
LOGMSG = ""

BUTTON_state = False
BUTTON_action = "wait"
cycles = 0

BUTTON_GPIO = 13
LED_GPIO = 5
RELAY2_GPIO = 18
RELAY_GPIO = 18


def switchState(bool):
    return not bool


def setLED(status):
#    print(f"LED Status: {status}")
    GPIO.output(LED_GPIO, status)
    return status


def switchLED(status):
    status = switchState(status)
    setLED(status)
    return status


def setPower(status):
#    print(f"Power Status: {status}")
    # Logic umgedreht, um True = An,m False = Aus zu haben
    GPIO.output(RELAY_GPIO, not status)
    return status


def switchPower(status):
    status = switchState(status)
    setPower(status)
    return status

def getButton(BUTTON_GPIO):
#    status = False
    status = not GPIO.input(BUTTON_GPIO)
    return status

def getGPIOstatus(GPIO_PIN):
#    status = False
    status = GPIO.input(GPIO_PIN)
    return status



class buttonAction:
    def __init__(self, gpio, name = "Button"):
        self.name = name
        self.gpio = gpio
        self.duration = 0
        self.action = ""
        self.state_prev = False
        self.state = False
        self.pressed_last=time.time()
        #DO / TEST INITIAL SETUP

    def getButtonAction(self):
        self.action="WAIT"

        self.state_prev = self.state
        self.state = getButton(self.gpio)

        now = time.time()
        last = self.pressed_last
        self.pressed_last=now

        if (self.state_prev != self.state):
            print(f"Button State {self.state}")

        if self.state == True and self.state_prev == False:
#            logger.info("Button pushed")
#            logger.info(f"LOG: {datetime.now()} - {LOGMSG}")
            self.action = "PUSH"

        if self.state == True and self.state_prev == True:
#            logger.info("Button hold")
#            logger.info(f"LOG: {datetime.now()} - {LOGMSG}")
            self.action = "HOLD"
            self.pressed_last=last

        if self.state == False and self.state_prev == True:
 #           logger.info("Button Released")
 #           logger.info(f"LOG: {datetime.now()} - {LOGMSG}")
            self.action = "RELEASE"
            self.pressed_last=last

        self.duration = int((now - self.pressed_last)*1000)
#        print(f"Button State Result:{self.action} State:{self.state} LastState:{self.state_prev}")
        return self.action


try:
    ###############
    ## SETUP 
    ###############
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LED_GPIO, GPIO.OUT)      # LED is Output device
    GPIO.setup(RELAY_GPIO, GPIO.OUT)    # RELAY is Output device
    GPIO.setup(BUTTON_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP) # BUTTON is INPUT device
    # ggf auf PUD_DOWN ändern
    # GPIO.setup(BUTTON_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    # The pull_up_down parameter in the GPIO.setup call tells the Raspberry Pi which state
    # the pin should be in when there is nothing connected to the pin. This is important
    # since we want our program to read a low state when the button is not pushed and a
    # high state when the button is pushed.

    # INIT LED & RELAY
    setLED(LED_state)
    setPower(RELAY_state)


    def handle_exit(sig, frame):
        raise(SystemExit)
    signal.signal(signal.SIGTERM, handle_exit)

    ###############
    # MAIN
    ###############

    # create logger
    logger = logging.getLogger(__name__)
#    solar_logger.logger_setup('/home/pi/')
    solar_logger.logger_setup('/home/pi/', LogFileLevel=logging.DEBUG, ErrorFileLevel=logging.ERROR, ConsoleLevel=logging.INFO)
#    solar_logger.logger_setup('/Users/itze/', LogFileLevel=logging.DEBUG, ErrorFileLevel=logging.ERROR, ConsoleLevel=logging.DEBUG)
    logger.info("Starting Powerbutton Handling")
    

    BUTTON01 = buttonAction(BUTTON_GPIO,"Button01")
    # RELAY_CRON = solar_cron.solarcron('0/2 * * * *', "AUTO RELAY")
    # RELAY_CRON = solar_cron.solarcron('20 6,9,12,15,18 * * *', "RELAY01")
    RELAY_CRON = solar_cron.solarcron('15,45 8-22/2 * 3-10 *', "RELAY01")

    while True:
        BUTTON_action = BUTTON01.getButtonAction()
        if (BUTTON_action == "PUSH"):
            LED_state = switchLED(LED_state)
            MANUAL_state = LED_state
#            MANUAL_state = switchState(MANUAL_state)
            if (AUTOMATIC_state == False):
                RELAY_state = switchPower(RELAY_state)

        if (BUTTON_action == "HOLD"):
            #cycles += 1
            # if BUTTON_action == "hold":
            #     # long hold ....
            #     # ggf Action bei langem halten?
            #     cycles += 1
            # else:
            #     BUTTON_action = "hold"
            logger.info(f"BUTTON hold over 10000ms - rebooting")
            time.sleep(1.00)
            if (Button01.duration > 10000):
                os.system("/usr/sbin/reboot")

        if (BUTTON_action == "RELEASE"):
            #cycles = 0
            pass


        if (AUTOMATIC_state == False):
            if (RELAY_CRON.trigger()):
                AUTOMATIC_StartTime = int(time.time())  # epoch seconds
                AUTOMATIC_state = True
                RELAY_state = setPower(True)
 #               print("AUTOMATIC: ON")
        elif (AUTOMATIC_state == True):
            now = int(time.time())
            if (MANUAL_state == False):
                setLED(now % 2)
            if ((now - AUTOMATIC_StartTime) >= (AUTOMATIC_duration * 60)):
                AUTOMATIC_state = False
                if (MANUAL_state == False):
                    RELAY_state = setPower(False)
                    LED_state = setLED(False)
#                print("AUTOMATIC: OFF")

#        print(min, sec, RELAY_state, LED_state, AUTOMATIC_state)
        # if ((sec % 5) == 0):
        #     print(h, min, sec)
        LOGMSG_prev = LOGMSG
        LOGMSG = f"BUTTON Change:{BUTTON01.state_prev}->{BUTTON01.state} - Action:{BUTTON01.action, BUTTON01.duration}ms - LED:{LED_state} - RELAY:{RELAY_state}({getGPIOstatus(RELAY_GPIO)}) - MANUAL:{MANUAL_state} - AUTOMATIC:{AUTOMATIC_state}"
        if (LOGMSG != LOGMSG_prev):
            logger.info(f"{LOGMSG}")

        time.sleep(0.05)

except KeyboardInterrupt:
    # Programm wird beendet wenn CTRL+C gedrückt wird.
    logger.info('Programm wird beendet wenn CTRL+C gedrückt wird.')
except (KeyboardInterrupt, SystemExit):
    # Programm wird beendet wenn CTRL+C gedrückt wird.
    logger.info('Programm manuell unterbrochen')
except Exception as e:
    logger.critical(f'Unerwarteter Abbruch: {str(e)}')
    GPIO.cleanup()
    logger.critical('GPIO.cleanup')
    sys.exit(1)
finally:
    # Das Programm wird hier beendet, sodass kein Fehler in die Console geschrieben wird.
    GPIO.cleanup()
    logger.info('Programm wurde beendet.')
    sys.exit(0)
