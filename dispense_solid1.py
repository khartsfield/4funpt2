from time import sleep
import RPi.GPIO as gpio

DIR = 27 #direction pin
STEP = 22 #step pin
CW = 1 #clockwise
CCW = 0 #counterclockwise
SPR = 200 #steps per revolution 

gpio.setmode(gpio.BCM)
gpio.setup(DIR, gpio.OUT)
gpio.setup(STEP, gpio.OUT)
gpio.output(DIR,CW)

# one full revolution. Scale SPR up or down here to change how far the nut will travel.
step_count = SPR
delay = .005

# moving forward
for x in range(step_count):
    gpio.output(STEP, gpio.HIGH)
    sleep(delay)
    gpio.output(STEP, gpio.LOW)
    sleep(delay)

sleep(delay*3) # maybe also .5s. Pauses before moving forward again 
gpio.output(DIR, CCW)

# moving backward
for x in range(step_count):
    gpio.output(STEP, gpio.HIGH)
    sleep(delay)
    gpio.output(STEP, gpio.LOW)
    sleep(delay)    