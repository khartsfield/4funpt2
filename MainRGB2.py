#import sensors
import rgbsensor as rgb
import time
import board
import busio
import digitalio
import adafruit_tcs34725 as TCS #install this dependency
import os # used for running different .py scripts

#imports for conductivity 
import serial_conductivity_rev1 as Conduct

#include imports for main file
import pi_serial_test2 as temp_s

#imports for information input section (might not need to be here)
from datetime import date, datetime

#import pump
import pumpstuff as pumps

# Import libraries and modules for magnetic stirrer 
from ika.magnetic_stirrer import MagneticStirrer
import stirrer_control as stir

# Import email and information input files
import info_input5 as info
import python_code_email2 as email
import alert_email as alert
import alert_with_attachment as alert_attach

# imports for stepper motor (and LED light?)
import dispense_solid1 as solid

# import for color to noise ratio
import RGB_color_noise_test

# User inputs the experiment setup information
data_log = info.info_input()
info.data_check1(data_log)
print(data_log)

# User inputs the email information
sender = input("Email address of the sender: ")
receiver = input("Email address of the receiver: ")
email_password = input("Enter the sender's email password: ")
email_info = [sender, receiver, email_password]

email.email_info_check(email_info)
print(email_info)

#initialize sensors
#put integration time and the other thing
i2c1 = board.I2C()  # uses board.SCL and board.SDA
i2c2 = busio.I2C(board.D0,board.D1) #pin = D5 setup in config.txt (in bookmarks)
sensor1 = TCS.TCS34725(i2c1)
sensor2 = TCS.TCS34725(i2c2)

Red1 = []
Green1 = []
Blue1 = []
Red2 = []
Green2 = []
Blue2 = []
Gray1 = []
Gray2 = []
time2 = []
time3 = []
#ask user about calibration (check to see if works lol)
g = True
while g == True:
    Message = input("Would you like to calibrate?") 
    if Message.lower() == "yes":
        calibration = True 
	rgb.CalibrateSensor()
        g = False
    elif Message.lower() == "no":
        calibration = False
        g = False
    elif:
        print('Please retype input and try again')
        g = True

#do signal to noise ratio stuff
os.system('RGB_color_noise_test.py')

# Create empty lists for the time data and sensor data to fill in
time1 = []
temp = []
time2 = []
time3 = []
time4 = []
conductivity_list = []
pump_list = []



#initialize the pump
pump = pumps.initializePort()

## End of definitions & setup

### Begining of coding sequence 


# This function brings over all the data that the user input - and the
# variable names are the exact same as in info_input5.py.

# These variable names are as follows:
# capacity        beaker capacity, in mL
# density         solvent density, in g/mL
# v_solvent       final volume of solvent, in mL
# m_solvent       final mass of solvent, in g

# turning off incedent light measurement for both sensors
gpio.setup(17, gpio.OUT, initial=gpio.LOW)
gpio.setup(25, gpio.OUT, initial=gpio.LOW)

# Re-initialize array so that calibrated readings are erased
Red1 = []
Green1 = []
Blue1 = []
Red2 = []
Green2 = []
Blue2 = []
Gray1 = []
Gray2 = []

#run this function a couple times so that getGrAvg
Red1,Green1,Blue1,Red2,Green2,Blue2,time2,time3 = rgb.collect(Red1,Green1,Blue1,Red2,Green2,Blue2)
# take last 10ish values & average them for the our goal point and store that number for Goal 
# (could be added to getRGB.collect? for below)
#rgb are arrays of all past values
Base_Gr = rgb.getGrAvg(Red1,Green1,Blue1)


# set magnetic stirrer speed and stirring time
# the two values below are subject to change
stirring_rpm_1 = 100 # rpm
stirring_time_1 = 10 # in seconds
Cur_Gr = Base_Gr

#initialize conductivity sensor 
ser = Conduct.initialize_conductivity()

## add mass using the stepper motor. Add salt, stir, then measure. Should be oversaturated afterwards
while Cur_Gr < 1.1*Base_Gr:
    #check on imports and function calls
    #change temp when cindy is done 
    time1.append(temp_s.read_temp(time1)[0])
    temp.append(temp_s.read_temp(time1)[2])
    conductivity_list.append(Conduct.conductivity(ser,time4))
    solid.dispense_solid()
    stir.stirring_start(stirring_rpm_1)
    stir.stirring_wait(stirring_time_1)
    stir.stirring_stop()
    Red1,Green1,Blue1,Red2,Green2,Blue2,time2,time3 = rgb.collect(Red1,Green1,Blue1,Red2,Green2,Blue2,time2,time3)
    #update (using sensor 1 to detect solids)
    Cur_gr = rgb.getGrAvg(Red1,Green1,Blue1)
    
## solution should now be over-saturated 
# sensor 2 is top sensor 
Red1,Green1,Blue1,Red2,Green2,Blue2,time2,time3 = rgb.collect(Red1,Green1,Blue1,Red2,Green2,Blue2,time2,time3)
Goal_Gr = rgb.getGr(Red2,Green2,Blue2)
###same thing from above using sensor 2. Middle of the glass view

# this while loop should continue until the solution has reached the desired G value in the desired range 

#set magnetic stirrer speed and stirring time


difference = Cur_Gr - Goal_Gr

#dispense liquid function from pump.py file 
#units for pump stuff are in mL
capacity = data_log[2]
pumps.setFlowVol(pump, 20, capacity) #placeholder value of 20 mL

#initialize total volume- Brandon? i am confusion
tot_disp = 0 # total volume dispensed over time 
beaker_vol = capacity # Total beaker capacity, will probably be hard coded
disp_vol = 20 # discrete volume that will be dispensed into the solution

while difference > 5 & pumps.bigRedButton(pump, beaker_vol): #where range values will go 
    #general controller that we can tweak values for
    if difference > 5 & difference < 10:
        disp_vol = 1
        pumps.setFlowVol(pump,disp_vol,beaker_vol)
    elif difference > 10 & difference < 15:
        disp_vol = 5
        pumps.setFlowVol(pump,disp_vol,beaker_vol)
    elif difference > 15:
        disp_vol = 10
        pumps.setflowVol(pump,disp_vol,beaker_vol)
    pump_list.append(disp_vol)
    tot_disp = tot_disp + disp_vol    #increments total volume with the dispensed volume

    stir.stirring_start(stirring_rpm_1)
    stir.stirring_wait(stirring_time_1) #stirring_stop function sleeps the code so it will pause here to let the stirrer
    # to keep stirring
    stir.stirring_stop()
    Red1,Green1,Blue1,Red2,Green2,Blue2,time2,time3 = rgb.collect(Red1,Green1,Blue1,Red2,Green2,Blue2,time2,time3)
    Cur_Gr = rgb.getGr(Red1,Green1,Blue1)
    difference = Cur_Gr - Goal_Gr
else:
    # email prof that experiment has failed and must be done again
    # we can choose which one we want
    # email with text alert only
    alert.send_email(email_info[0], email_info[1], email_info[2])
    # save data in the user's desired filepath
    path = info.excel_placement()
    info.excel_create(path, data_log, time1, temp, time2, Red1, Green1, Blue1, time3, Red2,Green2,Blue2,
                             time4, conductivity_list, pump_list)
    # email with Excel file that contains data
    alert_attach.send_email(path, email_info[0], email_info[1], email_info[2])

# The name of the Excel file and the file location where the user wants to save the file
# to copy path name:
# Windows - in File Explorer, left-click the file tree bar and type control-C
# Mac - in Finder, type option-command-C
path = info.excel_placement()

# Create the Excel file and save the data
info.excel_create(path, data_log, time1, temp, time2, Red1, Green1, Blue1, time3, Red2,Green2,Blue2,
                             time4, conductivity_list, pump_list)

density = data_log[3]

v_solvent = float(sum(pump_list))
print(v_solvent, "mL")

m_solvent = density*v_solvent
print("Mass of solvent")
print(m_solvent, "g")

while True:
    m_solute = input("Enter final mass of solute (unit in g): ")
    if info.is_number(m_solute):
        m_solute = float(m_solute)
        print(m_solute, "g")
        if m_solute < 0:
            print("Error: mass of final solute cannot be negative")
        elif m_solute > 1000:
            print("Error: mass of final solute is too large")
        else:
            break
    else:
        print("Error: Input data needs to be number")

while True:
    mass_solution = input("Enter final mass of solution (unit in g): ")
    if info.is_number(mass_solution):
        mass_solution = float(mass_solution)
        print(mass_solution, "g")
        if mass_solution < 0:
            print("Error: mass of final solution cannot be negative")
        elif mass_solution > 1000:
            print("Error: mass of final solution is too large")
        else:
            break
    else:
        print("Error: Input data needs to be number")

# do math to calculate the concentration and save it in the file
# Equation reference: https://www.chem.purdue.edu/gchelp/howtosolveit/Solutions/concentrations.html
# concentration (percent by mass)
concentration = m_solute/mass_solution * 100

data_log2 = [m_solute, mass_solution, concentration]
info.data_check2(data_log2)
print(data_log2)

# add the information above into the Excel
info.excel_add(path, v_solvent, m_solvent, data_log2[1], data_log2[2])

## handy dandy emailing thing to Prof Liu to go here
email.send_email_attachment(path, email_info[0], email_info[1], email_info[2])

