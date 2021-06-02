#Creat By Jason Luk's Tech
#coding=utf-8
import serial
import time
import subprocess
import re
import datetime

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        pass
    try:
        import unicodedata
        unicodedata.numeric(s)
        return True
    except (TypeError, ValueError):
        pass
    return False

# Establish connection with Arduino board

#usb_result = subprocess.check_output("ls /dev/*USB*", shell=True).decode("utf-8").rep$
# For Linux only
def initialize_conductivity():
    usb_result = "/dev/ttyACM0" #For PC user, needs to find the Port from Device Manager o$
    # ser = serial.Serial('/dev/tty.usbmodem141301', 9600, timeout=1)  # COM number depend$
    ser = serial.Serial(usb_result, 9600, timeout=1)
    ser.flush() 
    return ser

def conductivity(ser,time4):
    # print(" in the while loop")
    # if ser.in_waiting > 0:
    #    # result = str(ser.readline(), encoding='utf-8')
    #    result = str(ser.readline())
    #    print("in the inner if statement")
    #    if is_number(result):
    #        conductivity = float(result)
    #        print(conductivity)
    
    result = str(ser.readline())
    #print(result)
    result_float = re.findall("\d+.\d+", result)
    time4.append(datetime.now())
    if len(result_float)>0:
        result_float = result_float[0]
        time4.append(datetime.now())
        print(result_float)
    # conductivity = float(result)
    # print(conductivity)
    return result_float