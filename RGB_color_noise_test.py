import numpy as np
from rgbsensor import collect

#goal: run 3 individual RGB tests with either the oversaturated or pre-saturated solution to 
#determine which color LED would have the least amount of noise with the solution in use

#test the red LED 
print('Turn on the red LED')
#user turns on red LED
red_test = [0] * 100 #preallocate array for red LED
red_on = input('Type "DONE" when the red LED is on:')
if red_on == 'DONE':
    for i in len(red_test):
        Red1,Green1,Blue1,Red2,Green2,Blue2 = collect(Red1,Green1,Blue1,Red2,Green2,Blue2) #stand in variable
red_std = np.std(Red1) #calculate the standard deviation to measure the fluctuations from the mean,
print('Turn off red LED')
#essentially evaluating the amount of noise
print('Turn on the green LED')
#in reality, this will prompt the RGB sensor

#test the green LED 
green_test = [0] * 100  #preallocate array for green LED
green_on = input('Type "DONE" when the green LED is on:')
if green_on == 'DONE':
    for i in len(green_test):
        Red1,Green1,Blue1,Red2,Green2,Blue2 = collect(Red1,Green1,Blue1,Red2,Green2,Blue2)
green_std = np.std(Green1) #calculate the standard deviation to measure the fluctuations from the mean,
print('Turn off green LED')
#essentially evaluating the amount of noise
print('Turn on the blue LED')

#test the blue LED
blue_test = [0] * 100  #preallocate array for red LED
blue_on = input('Type "DONE" when the blue LED is on:')
if blue_on == 'DONE':
    for i in len(blue_test):
        Red1,Green1,Blue1,Red2,Green2,Blue2 = collect(Red1,Green1,Blue1,Red2,Green2,Blue2)
blue_std = np.std(Blue1) #calculate the standard deviation to measure the fluctuations from the mean,
print('Turn off red LED')
#essentially evaluating the amount of noise
print('Data collection for LED color choice complete') 

#concatenate standard deviation arrays for each color
std_LED = np.concatenate(red_std, green_std, blue_std)
#find the minimum standard
std_LED_min = min(std_LED)

#let user know which LED to use based on which LED outputs the smallest standard deviation
if std_LED_min == red_std:
    print('Please turn on the red LED and keep it on until the end of the experiment')
elif std_LED_min == green_std:
    print('Please turn on the green LED and keep it on until the end of the experiment')
elif std_LED_min == blue_std:
    print('Please turn on the blue LED and keep it on until the end of the experiment')







   