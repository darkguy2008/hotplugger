#!/usr/bin/python3
import re
import os
import ast
import fcntl
import sys
import yaml
import json
import socket
import pprint
from pathlib import Path


def help():
    print("")
    print("Device plug/unplug helper script")
    print("")
    print("This should be run by an udev rules file you create that will trigger on every")
    print("USB command. A sample rules file may be alongside this python script or in the")
    print("README file, where you can find extra instructions.")
    print("")
    print("To test, run it with an environment variable (ACTION) as either 'add' or 'remove'")


def read(socket):
    f = ''
    while True:
        try:
            obj = json.loads(f)
            print('RECV <-', obj)
            return obj
        except:
            f += socket.recv(1).decode()


def send(socket, message):
    print('SEND ->', message.strip())
    socket.send(str.encode(message))


def plug():

    print('==================================================================')
    print('PLUG')
    print('==================================================================')
    pprint.pprint(dict(os.environ), width=1)
    print('==================================================================')
    path = Path(__file__).parent / "config.yaml"
    with open(path) as file:
        vms = yaml.load(file, Loader=yaml.FullLoader)
        devpath = os.environ['DEVPATH']
        is_seat = os.getenv('TAGS') or ''
        if is_seat == ':seat:':
            is_seat = True
        else:
            is_seat = False

        if is_seat:
            tmpFolderPath = Path(__file__).parent / "tmp"
            if not os.path.exists(tmpFolderPath):
                os.makedirs(tmpFolderPath)
            usbdefPath = Path(__file__).parent / \
                f"tmp/{devpath.replace('/', '-')}"
            f = open(usbdefPath, "w")
            f.write(json.dumps(dict(os.environ)))
            f.close()
        else:
            for rootKey, rootValue in vms.items():
                for k, v in rootValue.items():
                    for port in v['ports']:
                        if devpath.find(port) >= 0:

                            tmpFolderPath = Path(__file__).parent / "tmp"
                            if not os.path.exists(tmpFolderPath):
                                os.makedirs(tmpFolderPath)
                            onlyfiles = [f for f in os.listdir(
                                tmpFolderPath) if os.path.isfile(os.path.join(tmpFolderPath, f))]

                            for f in onlyfiles:
                                currentFile = f
                                usbDefPathFile = devpath.replace('/', '-')
                                if usbDefPathFile.find(f) >= 0:
                                    envFilename = os.path.join(
                                        tmpFolderPath, f)

                                    with open(envFilename) as input_file:
                                        contents = input_file.read()
                                        udevEnv = json.loads(contents)
                                        print(udevEnv)
                                    os.remove(envFilename)

                                    client = socket.socket(
                                        socket.AF_UNIX, socket.SOCK_STREAM)
                                    client.settimeout(.2)
                                    client.connect(rootValue[k]['socket'])
                                    data = read(client)

                                    send(
                                        client, "{ \"execute\": \"qmp_capabilities\" }\n")
                                    data = read(client)

                                    send(
                                        client, "{ \"execute\": \"human-monitor-command\", \"arguments\": { \"command-line\": \"info usbhost\" } }")
                                    data = read(client)
                                    usbhost = data['return']
                                    print(usbhost)

                                    hostport = 0
                                    hostaddr = udevEnv['DEVNUM'].lstrip('0')
                                    hostbus = udevEnv['BUSNUM'].lstrip('0')
                                    print('BUSNUM', hostbus)
                                    print('HOSTADDR (DEVNUM)', hostaddr)

                                    for line in usbhost.splitlines():
                                        print('LINE', line)
                                        if line.find(f"Bus {hostbus}") >= 0:
                                            if line.find(f"Addr {hostaddr}") >= 0:
                                                print('FOUND IN', line)
                                                hostport_search = re.search(
                                                    ".*Port.*?([\d\.]*),", line, re.IGNORECASE)
                                                hostport = hostport_search.group(
                                                    1)
                                                break
                                    print(hostbus, hostaddr, hostport)

                                    # TODO: Don't do anything if hostport == 0. Somehow I couldn't get it working
                                    cmd = f'{{ "execute": "device_add", "arguments": {{ "driver": "usb-host", "hostbus": "{hostbus}", "hostport": "{hostport}", "id": "device{hostbus}{hostport}" }} }}'
                                    send(client, cmd)
                                    data = read(client)
                                    print("Device plugged in")

                                    client.close()
                                    break

                            break


def unplug():

    print('UNPLUG')
    path = Path(__file__).parent / "config.yaml"
    with open(path) as file:
        vms = yaml.load(file, Loader=yaml.FullLoader)
        devpath = os.environ['DEVPATH']

        for rootKey, rootValue in vms.items():
            for k, v in rootValue.items():
                for port in v['ports']:
                    if devpath.find(port) >= 0:

                        client = socket.socket(
                            socket.AF_UNIX, socket.SOCK_STREAM)
                        client.settimeout(.2)
                        client.connect(rootValue[k]['socket'])
                        data = read(client)

                        send(client, "{ \"execute\": \"qmp_capabilities\" }\n")
                        data = read(client)

                        send(
                            client, "{ \"execute\": \"human-monitor-command\", \"arguments\": { \"command-line\": \"info usbhost\" } }")
                        data = read(client)
                        usbhost = data['return']
                        print(usbhost)

                        hostport = 0
                        hostaddr = udevEnv['DEVNUM'].lstrip('0')
                        hostbus = udevEnv['BUSNUM'].lstrip('0')
                        print('BUSNUM', hostbus)
                        print('HOSTADDR (DEVNUM)', hostaddr)

                        for line in usbhost.splitlines():
                            print('LINE', line)
                            if line.find(f"Bus {hostbus}") >= 0:
                                if line.find(f"Addr {hostaddr}") >= 0:
                                    print('FOUND IN', line)
                                    hostport_search = re.search(
                                        ".*Port.*?([\d\.]*),", line, re.IGNORECASE)
                                    hostport = hostport_search.group(
                                        1)
                                    break

                        print(hostbus, hostaddr, hostport)

                        # TODO: Don't do anything if hostport == 0. Somehow I couldn't get it working
                        # NOTE: For devices without ID see QOM path https://qemu.readthedocs.io/en/latest/interop/qemu-qmp-ref.html#qapidoc-1953
                        # Can be retrieved with (qemu) qom-list /machine/peripheral-anon/device[0], etc...
                        cmd = f'{{ "execute": "device_del", "arguments": {{ "id": "device{hostbus}{hostport}" }} }}'
                        send(client, cmd)
                        data = read(client)

                        client.close()
                        print("Device unplugged")

                        break


action = os.environ['ACTION']
if action == 'add':
    plug()
elif action == 'remove':
    unplug()
else:
    help()
