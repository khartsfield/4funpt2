# Pump related functions below

from masterflex import MasterflexSerial

tot_vol = 0

def initializePort():
    for i in range(0, 100):
        port = "/dev/ttyUSB{i}".format(i=i) # this is for linux and raspberry pi; needs to change for PC: com.
        try:
            m = MasterflexSerial(1, port)
            return m
        except Exception:
            pass
              
def stopFlow(m):
    #function within masterflex is called halt
    m.halt()

def setFlowVol(m, vol, cap):
    #use setRevolutions--m.setRevolutions(0<vol<100)
    tot_vol = tot_vol + vol
    bigRedButton(m, cap)
    if vol > 0 & vol < 80 & bigRedButton(m, cap):
        x = volConvert(vol)
        m.setRevolutions(x)
    else:
        print("Invalid volume requested")
    
    #total volume dispensed should be tracked within main
def setFlowRate(m, rate, cap):
    #use setMotorSpeed--rpm values between -100<x<100 DOUBLE CHECK THIS
    tot_vol = tot_vol + rate
    
    if rate > 0 & rate < 100 & bigRedButton(m, cap):
        x = rateConvert(rate)
        m.setMotorSpeed(x)
    else:
        print("Invalid flow rate requested")
    
    #dispense time is tracked within main as well as total volume
    #should be able to 
def bigRedButton(m, cap):
    '''checks if total volume (tot_vol) is greater than beaker safety value (80%)
    if finds to be true then ends experiment
    stop represents boolean for if code needs to end
    if (vol > 80)
    stop = true'''
    if tot_vol > 0.8*cap:
        m.halt()
        return False
    else:
        return True

#returns global value of total volume
def get_Total():
    return tot_vol

#returns percent of beaker volume filled
def get_Percent(cap):
    return tot_vol/cap
    
#returns mL volume converted to revolutions    
def volConvert(vol):
    rev = vol/2.4
    return rev

#returns mL/s rate into RPM 
def rateConvert(rate):
    rpm = rate/0.04
    return rpm
