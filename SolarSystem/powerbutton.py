# sudo apt install python3-rpi.gpio
import time
import sys
import RPi.GPIO as GPIO


Power_state = False
LED_state = False
RELAY_state = True

input_state = 1
button_state = "waiting"
cycles = 0

BUTTON_GPIO = 16
LED_GPIO = 24
RELAY_GPIO = 23

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Button to GPIO16
GPIO.setup(LED_GPIO, GPIO.OUT)  # LED to GPIO24
GPIO.setup(RELAY_GPIO, GPIO.OUT)  # LED to GPIO23
# INIT GPIO
GPIO.output(LED_GPIO, LED_state)
GPIO.output(RELAY_GPIO, RELAY_state)


def toggleBool(bool):
    return not bool


def setLED(status):
    print(f"LED Status: {status}")
    GPIO.output(LED_GPIO, status)


def toggleLED(status):
    status = toggleBool(status)
    setLED(status)
    return status


def setPower(status):
    print(f"Power Status: {status}")


def togglePower(status):
    status = toggleBool(status)
    setPower(status)
    return status


# MAIN
try:
    while True:
        input_state_prev = input_state
        input_state = GPIO.input(BUTTON_GPIO)
#        print(f"input_state {input_state} input_state_prev {input_state_prev} button_state {button_state}")
        if input_state == False and input_state_prev == True:
            print("Unknown status - potentially first press")

        if input_state == False and input_state_prev == False:
            if button_state == "pressing":
                cycles += 1
            else:
                button_state = "pressing"
                LED_state = toggleLED(LED_state)
                Power_state = togglePower(Power_state)

        if input_state == True and input_state_prev == False:
            print("Button Released")
            button_state = "waiting"
            cycles = 0

        # if button_state == "waiting":
        #     print(f"Waiting... Button {button_state} LED {Power_state}")

        time.sleep(0.05)
except:
    print(" end/error:", sys.exc_info()[0])
    GPIO.cleanup()
