#!/usr/bin/python3
import re
import os
import ast
import sys
import yaml
import json
import time
import pprint
from pathlib import Path
from qemu import *

configFilename = Path(__file__).parent / "config.yaml"
tmpFolderPath = Path(__file__).parent / "tmp"


def printp(dict):
	pprint.pprint(dict, width=1)


def sanitizeDevpath(devpath):
	return devpath.replace('/', '_').replace(':', '_')


def loadConfig():
	with open(configFilename) as file:
		return yaml.load(file, Loader=yaml.FullLoader)


def savePortDeviceMetadata(metadata, devpath):
	if not os.path.exists(tmpFolderPath):
		os.makedirs(tmpFolderPath)
	usbdefPath = f"{tmpFolderPath}/{sanitizeDevpath(devpath)}"
	print(f"Saving port metadata to {usbdefPath} ...")
	f = open(usbdefPath, "w")
	f.write(json.dumps(metadata))
	f.close()


def updatePortDeviceMetadata(metadata, filename):
	if not os.path.exists(tmpFolderPath):
		os.makedirs(tmpFolderPath)
	print(f"Saving port metadata to {filename} ...")
	f = open(filename, "w")
	f.write(json.dumps(metadata))
	f.close()


def loadPortDeviceMetadata(config, devpath):
	for rootKey, rootValue in config.items():
		for k, v in rootValue.items():
			for port in v['ports']:
				if devpath.find(port) >= 0:
					print(f"Found {devpath} in port {port}")

					if not os.path.exists(tmpFolderPath):
						os.makedirs(tmpFolderPath)
					metadataFiles = [f for f in os.listdir(tmpFolderPath) if os.path.isfile(os.path.join(tmpFolderPath, f))]
					metadataFiles.sort(key=len, reverse=True)
					print(f"Metadata files:")
					printp(metadataFiles)

					usbDefPathFile = sanitizeDevpath(devpath)
					for f in metadataFiles:
						metadataFilename = os.path.join(tmpFolderPath, f)
						if usbDefPathFile.find(f) >= 0:
							print(f"Found {devpath} in {metadataFilename}")
							with open(metadataFilename) as metadataFile:
								rv = json.loads(metadataFile.read())
								rv["SOCKET"] = rootValue[k]['socket']
								rv["FILENAME"] = metadataFilename
								return rv


def plug():

	print('==================================================================')
	print('PLUG')
	print('==================================================================')
	printp(dict(os.environ))
	print('==================================================================')
	config = loadConfig()
	devpath = os.environ['DEVPATH'] 
	is_usb_port = (os.getenv('DEVNUM') or '') != '' and (os.getenv('BUSNUM') or '') != ''
	print(f"Is USB Port? {is_usb_port}")

	if is_usb_port == True:
		savePortDeviceMetadata(json.loads(json.dumps(dict(os.environ))), devpath)
	else:
		metadata = loadPortDeviceMetadata(config, devpath)
		if not metadata:
			print(f"Metadata file for {devpath} not found")
		else:
			print(metadata)

		print(f"Connecting to QEMU at {metadata['SOCKET']}...")
		with QEMU(metadata["SOCKET"]) as qemu:
			usbhost = qemu.hmp("info usbhost")
		print(usbhost)

		hostport = 0
		hostaddr = metadata['DEVNUM'].lstrip('0')
		hostbus = metadata['BUSNUM'].lstrip('0')
		print(f"Looking for USB Bus: {hostbus}, Addr {hostaddr} ...")

		for line in usbhost.splitlines():
			if line.find(f"Bus {hostbus}") >= 0:
				if line.find(f"Addr {hostaddr}") >= 0:
					print('FOUND IN', line)
					hostport_search = re.search(".*Port.*?([\d\.]*),", line, re.IGNORECASE)
					hostport = hostport_search.group(1)
					break
		print(f"Found USB Bus: {hostbus}, Addr {hostaddr}, Port {hostport}")

		metadata["PORT"] = hostport
		updatePortDeviceMetadata(metadata, metadata["FILENAME"])

		print(f"Plugging USB device in port {hostport}...")
		if hostport != '0':
			time.sleep(1)
			with QEMU(metadata["SOCKET"]) as qemu:
				qemu.hmp(f"device_add driver=usb-host,hostbus={hostbus},hostport={hostport},id={metadata['ID_PATH_TAG']}")
				print("Device plugged in. Current USB devices on guest:")
				print(qemu.hmp("info usb"))


def unplug():

	print('==================================================================')
	print('UNPLUG')
	print('==================================================================')
	printp(dict(os.environ))
	print('==================================================================')
	config = loadConfig()
	devpath = os.environ['DEVPATH']

	is_usb_port = (os.getenv('DEVNUM') or '') != ''
	print(f"Is USB Port? {is_usb_port}")

	if is_usb_port == True:

		for rootKey, rootValue in config.items():
			for k, v in rootValue.items():
				socket = rootValue[k]['socket']				
				socketFile = Path(socket)
				if socketFile.exists():
					print(f"Connecting to QEMU at {socket}...")
					with QEMU(socket) as qemu:
						usbhost = qemu.hmp("info usbhost")
					print(usbhost)

					time.sleep(1)
					with QEMU(socket) as qemu:
						qemu.hmp(f"device_del {os.environ['ID_PATH_TAG']}")
						print(f"Device unplugged from {k}. Current USB devices on guest:")
						time.sleep(1)
						print(qemu.hmp("info usb"))
						usbDefPathFile = os.path.join(tmpFolderPath, sanitizeDevpath(devpath))
						if Path(usbDefPathFile).exists():
							os.remove(usbDefPathFile)


action = os.environ['ACTION']
if action == 'add':
	plug()
elif action == 'remove':
	unplug()
else:
	print("")
	print("Device plug/unplug helper script")
	print("")
	print("This should be run by an udev rules file you create that will trigger on every")
	print("USB command. For more info have a look at the README file.")
