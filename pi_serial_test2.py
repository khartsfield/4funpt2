# Source: https://www.circuitbasics.com/raspberry-pi-ds18b20-temperature-sensor-tutorial/
# Cooperation: Jason Luk's Tech

import os
import glob
import datetime
# from openpyxl import Workbook

# setup connections with One-Wire Protocol
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')

base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'


# def excel_create(file_name, time_list, temp_list):  # change the input_list to specific data name later
#     workbook = Workbook()
#     sheet = workbook.active
#     sheet["A1"] = "Time (s)"
#     sheet["B1"] = "Temperature data (F)"
#
#     cell_number = 2
#     for input in time_list:  # for loop, change inputs later
#         cell_name = "A{}".format(cell_number)  # for horizontal column A
#         sheet[cell_name] = input
#         cell_number += 1
#     cell_number = 2
#
#     for input in temp_list:  # for loop, change inputs later
#         cell_name = "B{}".format(cell_number)  # for horizontal column B
#         sheet[cell_name] = input
#         cell_number += 1
#     workbook.save(filename=file_name)


def read_temp_raw():
    f = open(device_file, 'r')
    lines = f.readlines()
    f.close()
    return lines


def read_temp():
    lines = read_temp_raw()
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.5)
        lines = read_temp_raw()
    equals_position = lines[1].find('t=')
    if equals_position != -1:
        temp_string = lines[1][equals_position + 2:]
        now = datetime.datetime.now()
        current_time = now.strftime("%H:%M:%S")
        temp_celsius = float(temp_string) / 1000.0
        temp_fahrenheit = temp_celsius * 9.0 / 5.0 + 32.0
        return current_time, temp_celsius, temp_fahrenheit

# temp_list = []
# time_list = []
# start_time = time.time()
#
# try:
#     while True:
#         temp_fahrenheit = read_temp()[1]
#         temp_list.append(temp_fahrenheit)
#         times = int((time.time()-start_time)*1000)/1000
#         time_list.append(times)
#         print(times, "s", " , ", temp_fahrenheit, "F")
#         time.sleep(0.5)
# except KeyboardInterrupt:  # When enter ctrl + C
#     excel_create("test_temp.xlsx", time_list, temp_list)
#     print("Excel Filed Exported")