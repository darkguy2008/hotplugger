#!/usr/bin/python3
import os
import signal
import subprocess

print("")
print("Using both an USB 3.0 and an USB 2.0 device (could be a thumb drive,")
print("an audio device or any other simple USB device), plug and unplug the")
print("device in the ports that you are interested for VM passthrough.")
print("")
print("Press Control + C when finished. The app will then print the device")
print("path of the USB ports. Also make sure that 'udevadm' is installed.")
print("")
input("Press ENTER to continue or abort with CTRL+C...")
print("")
print("Monitoring USB ports...")

###########################
# This gets the UDEV events
###########################

listout = []


def handle(sig, _):
    if sig == signal.SIGINT:
        print("")


signal.signal(signal.SIGINT, handle)
proc = subprocess.Popen(
    ["udevadm", "monitor", "-k", "-u", "-p", "-s", "usb"], stdout=subprocess.PIPE)

while True:
    line = proc.stdout.readline()
    if not line:
        break
    if line.startswith(b'DEVPATH'):
        listout.append(line)

proc.wait()
# print(listout)

######################################
# This gets an unique list of DEVPATHs
######################################

# function to get unique values


def unique(list1):

    # intilize a null list
    unique_list = []

    # traverse for all elements
    for x in list1:
        # check if exists in unique_list or not
        if x not in unique_list:
            unique_list.append(x)

    return unique_list


uniq = unique(listout)
stringlist = [x.decode('utf-8') for x in uniq]
print(*stringlist, sep='')
