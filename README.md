# Hotplugger: Real USB Port Passthrough for VFIO/QEMU!

Welcome to Hotplugger! This app, as the name might tell you, is a combination of some scripts (python, yaml, udev rules and some QEMU args) to allow you to pass through an actual USB port into a VM. Instead of passing the USB root hub (which could have the side effect of passing *all the ports*, including the ones you didn't want to) or another PCIe hub or something, you can just pass a specific USB port to a VM and have the others free for anything else. Plus, it saves you from using the `vfio-pci` driver for the USB root hub, so you can keep using it for evdev or other things on the VM host.

## Requirements

* `monitor.py` and `hotplugger.py` require **Python 3**
* Only tested with QEMU 5.0.0. Untested with older or newer versions.

## Quick start (Ubuntu 20.10)

1. `git clone https://github.com/darkguy2008/hotplugger.git`

2. (Optional) run `python3 monitor.py` and follow the prompts. Basically once you hit Enter you have to plug and unplug an USB device (a thumbdrive or audio device preferred) into the USB ports that you want to know their `DEVPATH` route from. This will help you identify them so you can write them into `config.yaml` in the `ports` array. This array only accepts `DEVPATH` routes that `UDEV` generates.

3. Edit `config.yaml`. **It must stay in the same folder as `monitor.py` and `hotplugger.py`**. Look at the current example: It's set for a Windows VM (the name doesn't matter, as long as it's unique within the entries of the same file). Make sure the `socket` property matches the file path of the QEMU `chardev` device pointing to an Unix domain socket file and in the `ports` array put the list of the `udev` `DEVPATH` of the USB ports you want to pass through to that VM:

   ```
   virtual_machines:
   
     windows:
       socket: /home/dragon/vm/test/qmp-sock
       ports:
         - /devices/pci0000:00/0000:00:14.0/usb3/3-1
         - /devices/pci0000:00/0000:00:14.0/usb3/3-2
         - /devices/pci0000:00/0000:00:14.0/usb4/4-1
         - /devices/pci0000:00/0000:00:14.0/usb4/4-2
   ```

4. Create an `/etc/udev/rules.d/99-zzz-local.rules` file with the following content:

   ```
   SUBSYSTEM=="usb", ACTION=="add", RUN+="/bin/bash -c 'python3 /path-to-hotplugger/hotplugger.py >> /tmp/hotplugger.log' 2>&1"
   SUBSYSTEM=="usb", ACTION=="remove", RUN+="/bin/bash -c 'python3 /path-to-hotplugger/hotplugger.py >> /tmp/hotplugger.log' 2>&1"
   ```

   Make sure to change `path-to-hotplugger` with the path where you cloned the repo to, or installed the package. It can be simplified, but this one is useful in case you want to debug and see what's going on. Otherwise, proceed with a simpler file:

   ```
   SUBSYSTEM=="usb", ACTION=="add", RUN+="/bin/bash -c 'python3 /path-to-hotplugger/hotplugger.py'"
   SUBSYSTEM=="usb", ACTION=="remove", RUN+="/bin/bash -c 'python3 /path-to-hotplugger/hotplugger.py'"
   ```

5. Create the QMP monitor Unix domain socket if you haven't already in your QEMU args. I use this:

   ```
   -chardev socket,id=mon1,server,nowait,path=./qmp-sock
   -mon chardev=mon1,mode=control,pretty=on
   ```

6. Have a coffee! ☕

## Troubleshooting

If for some reason the app doesn't seem to work, try these methods:

* Reboot the computer
* Reboot udev: `sudo udevadm control --reload-rules && sudo udevadm trigger`
* View udev's logfile: `sudo service udev restart && sudo udevadm control --log-priority=debug && journalctl -f | grep -i hotplugger`
* If you want to see what will be run when you plug a device, try with this command to simulate an udev event: `udevadm test $(udevadm info -a --path=/devices/pci0000:00/0000:00:14.0/usb3/3-1/3-1:1.0) --action=add` replacing `--path` with the path of the USB port down to the device itself (in this case, I had a device connected to the `usb3/3-1` port, identified as `3-1:1.0`.

## Thank you!

A lot of work and sleepless nights were involved in this procedure, so if this app helps you in any way or another, please consider sending a small donation, it helps a lot in these tough times! 

[<img src="https://www.paypalobjects.com/en_US/i/btn/btn_donate_LG.gif">](https://www.paypal.com/donate?hosted_button_id=H2YLSRHBQJ94G)
