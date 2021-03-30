# sudo apt install python3-rpi.gpio
import time
from datetime import datetime
import sys
import RPi.GPIO as GPIO
import logging.handlers
import solar_logger


Power_state = False
LED_state = False   # Init = LED   is OFF
RELAY_state = False  # Init = Relay is OFF
MANUAL_state = False
AUTOMATIC_state = False
AUTOMATIC_duration = 15  # in Minutes
AUTOMATIC_run_range = range(32, 32 + AUTOMATIC_duration)
LOGMSG = ""

BUTTON_state = False
BUTTON_action = "wait"
cycles = 0

BUTTON_GPIO = 16
LED_GPIO = 24
RELAY_GPIO = 23

GPIO.setmode(GPIO.BCM)
# GPIO.setup(BUTTON_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Button to GPIO16
# Button to GPIO16
GPIO.setup(BUTTON_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
# ggf auf PUD_DOWN ändern
# GPIO.setup(BUTTON_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
# The pull_up_down parameter in the GPIO.setup call tells the Raspberry Pi which state
# the pin should be in when there is nothing connected to the pin. This is important
# since we want our program to read a low state when the button is not pushed and a
# high state when the button is pushed.

GPIO.setup(LED_GPIO, GPIO.OUT)  # LED to GPIO24
GPIO.setup(RELAY_GPIO, GPIO.OUT)  # LED to GPIO23
# INIT GPIO
GPIO.output(LED_GPIO, LED_state)
# Logic umgedreht, um True = An,m False = Aus zu haben
GPIO.output(RELAY_GPIO, not RELAY_state)


def switchState(bool):
    return not bool


def setLED(status):
    # print(f"LED Status: {status}")
    GPIO.output(LED_GPIO, status)
    return status


def switchLED(status):
    status = switchState(status)
    setLED(status)
    return status


def setPower(status):
    # print(f"Power Status: {status}")
    # Logic umgedreht, um True = An,m False = Aus zu haben
    GPIO.output(RELAY_GPIO, not status)
    return status


def switchPower(status):
    status = switchState(status)
    setPower(status)
    return status


# MAIN
try:
    solar_logger.logger_setup('powerbutton.log', '/home/pi/')
    logging.info("Starting Powerbutton Handling")
    logging.info(
        f"Automatic POWER Cycle: */{AUTOMATIC_run_range[0]} for {AUTOMATIC_duration} Min")

    while True:
        BUTTON_state_prev = BUTTON_state
        BUTTON_state = not GPIO.input(BUTTON_GPIO)
        # print(f"Button State {BUTTON_state}")

        if BUTTON_state == True and BUTTON_state_prev == False:
            # print("Button pushed")
            logging.info("Button pushed")
            (f"LOG: {datetime.now()} - {LOGMSG}")
            BUTTON_action = "push"
            LED_state = switchLED(LED_state)
            MANUAL_state = LED_state
#            MANUAL_state = switchState(MANUAL_state)
            if (AUTOMATIC_state == False):
                RELAY_state = switchPower(RELAY_state)

        if BUTTON_state == True and BUTTON_state_prev == True:
            BUTTON_action = "hold"
            cycles += 1
            # if BUTTON_action == "hold":
            #     # long hold ....
            #     # ggf Action bei langem halten?
            #     cycles += 1
            # else:
            #     BUTTON_action = "hold"

        if BUTTON_state == False and BUTTON_state_prev == True:
            # print("Button Released")
            logging.info("Button Released")
            BUTTON_action = "release"
            cycles = 0

        y, m, d, h, min, sec, wd, yd, i = datetime.now().timetuple()
        if (AUTOMATIC_state == False):
            if (min in AUTOMATIC_run_range):
                AUTOMATIC_StartTime = int(time.time())  # epoch seconds
                AUTOMATIC_state = True
                RELAY_state = setPower(True)
                # print("AUTOMATIC: ON")
        elif (AUTOMATIC_state == True):
            now = int(time.time())
            if (MANUAL_state == False):
                setLED(now % 2)
            if ((now - AUTOMATIC_StartTime) >= (AUTOMATIC_duration * 60)):
                AUTOMATIC_state = False
                if (MANUAL_state == False):
                    RELAY_state = setPower(False)
                    LED_state = setLED(False)
                # print("AUTOMATIC: OFF")

#        print(min, sec, RELAY_state, LED_state, AUTOMATIC_state)
        # if ((sec % 5) == 0):
        #     print(h, min, sec)

        LOGMSG_prev = LOGMSG
        LOGMSG = f"BUTTON Change:{BUTTON_state_prev}->{BUTTON_state} - Action:{BUTTON_action} - LED:{LED_state} - RELAY:{RELAY_state} - MANUAL:{MANUAL_state} - AUTOMATIC:{AUTOMATIC_state}"
        if (LOGMSG != LOGMSG_prev):
            logging.info(f"{LOGMSG}")

        time.sleep(0.05)

except:
    print(" end/error:", sys.exc_info()[0])
    GPIO.cleanup()
