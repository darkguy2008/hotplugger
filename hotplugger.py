#!/usr/bin/python3
import re
import os
import ast
import fcntl
import sys
import yaml
import json
import time
import pprint
from pathlib import Path
from qemu import *

def printp(dict):
	pprint.pprint(dict, width=1)

def sanitizeDevpath(devpath):
	return devpath.replace('/', '_').replace(':', '_')


def loadConfig():
	path = Path(__file__).parent / "config.yaml"
	with open(path) as file:
		rv = yaml.load(file, Loader=yaml.FullLoader)
	return rv


def savePortDeviceMetadata(metadata, devpath):
	tmpFolderPath = Path(__file__).parent / "tmp"
	if not os.path.exists(tmpFolderPath):
		os.makedirs(tmpFolderPath)
	usbdefPath = Path(__file__).parent / f"tmp/{sanitizeDevpath(devpath)}"
	print(f"Saving port metadata to {usbdefPath} ...")
	f = open(usbdefPath, "w")
	f.write(json.dumps(metadata))
	f.close()


def updatePortDeviceMetadata(metadata, filename):
	tmpFolderPath = Path(__file__).parent / "tmp"
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

					tmpFolderPath = Path(__file__).parent / "tmp"
					if not os.path.exists(tmpFolderPath):
						os.makedirs(tmpFolderPath)
					metadataFiles = [f for f in os.listdir(tmpFolderPath) if os.path.isfile(os.path.join(tmpFolderPath, f))]
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
	is_usb_port = (os.getenv('TAGS') or '') == ':seat:'
	print(f"Is USB Port? {is_usb_port}")

	if is_usb_port == True:
		savePortDeviceMetadata(json.loads(json.dumps(dict(os.environ))), devpath)
	else:
		metadata = loadPortDeviceMetadata(config, devpath)
		print(metadata)

		qemu = QEMU()
		qemu.connect(metadata["SOCKET"])
		result = qemu.send({ "execute": "human-monitor-command", "arguments": { "command-line": "info usbhost" } })
		usbhost = result['return']
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

		if str(hostport) != "0":
			time.sleep(1)
			qemu.send({ "execute": "device_add", "arguments": { "driver": "usb-host", "hostbus": hostbus, "hostport": hostport, "id": f"device_BUS_{hostbus}_PORT_{hostport}_ADDR_{hostaddr}" } })
			print("Device plugged in")

		qemu.disconnect()


def unplug():

	print('==================================================================')
	print('UNPLUG')
	print('==================================================================')
	printp(dict(os.environ))
	print('==================================================================')
	config = loadConfig()
	devpath = os.environ['DEVPATH']
	metadata = loadPortDeviceMetadata(config, devpath)
	print(metadata)

	is_usb_port = (os.getenv('DEVNUM') or '') != ''
	print(f"Is USB Port? {is_usb_port}")

	if is_usb_port == True:
		qemu = QEMU()
		qemu.connect(metadata["SOCKET"])
		result = qemu.send({ "execute": "human-monitor-command", "arguments": { "command-line": "info usbhost" } })
		usbhost = result['return']
		print(usbhost)

		hostport = metadata['PORT']
		hostaddr = metadata['DEVNUM'].lstrip('0')
		hostbus = metadata['BUSNUM'].lstrip('0')		
		print(f"Found USB Bus: {hostbus}, Addr {hostaddr}, Port {hostport}")

		time.sleep(1)
		qemu.send({ "execute": "device_del", "arguments": { "id": f"device_BUS_{hostbus}_PORT_{hostport}_ADDR_{hostaddr}" } })
		os.remove(metadata["FILENAME"])
		print("Device unplugged")

		qemu.disconnect()

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
