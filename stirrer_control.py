# Import libraries and modules
import time
from ika.magnetic_stirrer import MagneticStirrer
import numpy as np


ika_magnetic_stirrer_port = 'COM8'  # todo
ika_magnetic_stirrer = MagneticStirrer(device_port=ika_magnetic_stirrer_port)

# functions to control stirrer behavior

def stirring_start(a):
    #input a equal to the value of the rpm that you want to mix at
    rpm = a
    ika_magnetic_stirrer.target_stir_rate = a
    ika_magnetic_stirrer.start_stirring() #ika function that starts stirrer
    print(f'Starting IKA at {rpm} rpm')

def stirring_wait(b):
    #input b equal to the value to the time that you want to keep mixing
    time_mix = b
    print(f'Waiting {time_mix} seconds')
    time.sleep(time_mix)


def stirring_stop():
    #function to make the magnetic stirrer stop
    ika_magnetic_stirrer.stop_stirring()
    print(f"Stopping stirrer")
