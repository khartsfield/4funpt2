### LED THINGS BELOW
# Turn backlight off
#lcd.backlight = False

#user input to switch this variable 
from datetime import datetime


calibration = False

def CalibrateSensor():
    if calibration == True:
        print('Calibrating Black...')
        CalibState = 0
    else:
        minR = minG = minB = 0
        maxR = maxG = maxB = 255

## Prompt user to turn off all lights. change to person input, 
# do right after CalibrateSensor. Run this program again but 
# also prompt the user to turn on all the lights.
def ButtonPressed():
    if CalibState == 0 :
        minR = R_one
        minG = G_one
        minB = B_one
        print('Calibrating White...')
        CalibState = 1
    elif CalibState == 1:
        maxR = R_one
        maxG = G_one
        maxB = B_one
        calibState = 2
        print('Calibration Complete')
        
def constrain(val, min_val, max_val):
    return min(max_val, max(min_val, val))

def map(value, minVal, maxVal, newMin, newMax):
    return (((value - minVal) * (newMax - newMin)) / (maxVal - minVal)) + newMin
      
        
def collect(Red1,Green1,Blue1,Red2,Green2,Blue2,time2,time3):
    #turn off LED light using pin low for led light 

    minR = minG = minB = 0
    maxR = maxG = maxB = 255
    R_one = sensor1.color_rgb_bytes[0]
    G_one = sensor1.color_rgb_bytes[1]
    B_one = sensor1.color_rgb_bytes[2]
    time2.append(datetime.now())

    R_two = sensor2.color_rgb_bytes[0]
    G_two = sensor2.color_rgb_bytes[1]
    B_two = sensor2.color_rgb_bytes[2]
    time3.append(datetime.now())

    #Re-Map values
    R_one_m = map(R_one, minR, maxR, 0, 255)
    G_one_m = map(G_one, minG, maxG, 0, 255)
    B_one_m = map(B_one, minB, maxB, 0, 255)
    
    R_two_m = map(R_two, minR, maxR, 0, 255)
    G_two_m = map(G_two, minG, maxG, 0, 255)
    B_two_m = map(B_two, minB, maxB, 0, 255)
    
    #constrain values 
    R_one = constrain(R_one_m, 0, 255)
    G_one = constrain(G_one_m, 0, 255)
    B_one = constrain(B_one_m, 0, 255)
    
    R_two = constrain(R_two_m, 0, 255)
    G_two = constrain(G_two_m, 0, 255)
    B_two = constrain(B_two_m, 0, 255) 

    #Gr_one = (0.3 * R_one) + (0.59 * G_one) + (0.11 * B_one)
    #Gr_two = (0.3 * R_two) + (0.59 * G_two) + (0.11 * B_two)

    # print values on screen/store values in array

    print("RGB_1 ", R_one, G_one, B_one)
    Red1.append(R_one)
    Green1.append(G_one)
    Blue1.append(B_one)
    

    #collect.Gray1.append(Gr_one)

    
    print("RGB_2 ", R_two, G_two, B_two)
    Red2.append(R_two)
    Green2.append(G_two)
    Blue2.append(B_two)
    
    #collect.Gray2.append(Gr_two)
    # time sleep?
    return Red1,Green1,Blue1,Red2,Green2,Blue2,time2,time3

def getGrAvg(r,g,b):
    SumR = sum(r[-10:])
    SumG = sum(g[-10:])
    SumB = sum(b[-10:])
    AvgR = SumR/len(r)
    AvgG = SumG/len(g)
    AvgB = SumB/len(b)
    Gr = (0.3 * AvgR) + (0.59 * AvgG) + (0.11 * AvgB)
    return Gr

def getGr(r,g,b):
    Gr = (0.3 * r[-1]) + (0.59 * g[-1]) + (0.11 * b[-1])
    return Gr

def check_rgb(R_one, G_one, B_one):
    if calibration = True:
        if CalibState << 2:
            print("RGB_1 ", R_one, G_one, B_one)
            break 