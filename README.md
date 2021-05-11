# Hotplugger: Real USB Port Passthrough for VFIO/QEMU!

Welcome to Hotplugger! This app, as the name might tell you, is a combination of some scripts (python, yaml, udev rules and some QEMU args) to allow you to pass through an actual USB port into a VM. Instead of passing the USB root hub (which could have the side effect of passing *all the ports*, including the ones you didn't want to) or another PCIe hub or something, you can just pass a specific USB port to a VM and have the others free for anything else. Plus, it saves you from using the `vfio-pci` driver for the USB root hub, so you can keep using it for evdev or other things on the VM host.

# Requirements

* `monitor.py` and `hotplugger.py` require **Python 3**

* Only tested with QEMU 5.0.0. Untested with older or newer versions.

* Your QEMU machine must expose a QMP socket like this. The `path=` argument is important, we'll use that filename. It can be either relative or absolute, just make sure you can find and have access to it.

  ```
  -chardev socket,id=mon1,server=on,wait=off,path=./qmp-sock
  -mon chardev=mon1,mode=control,pretty=on
  ```

* Add one or more USB hubs to the guest VM. Using `nec-usb-xhci` is preferable for Win10 machines:

  ```
  -device nec-usb-xhci,id=xhci0
  -device nec-usb-xhci,id=xhci1
  ```

  This creates two hubs: `xhci0.0` and `xhci1.0`. Why? See caveat below:

### Important caveat with `nec-usb-xhci`:

It seems that `nec-usb-xhci` has 4 USB ports hardcoded and that cannot be changed. So, each time an USB device is added to the guest, QEMU will add the USB devices to the hub **until** it fills up, **BUT** it won't add the last device to the last available port. Instead, an USB 1.1 hub will be added to that port (to avoid running out of USB ports). This has the downside that if you are adding an USB 3.0 device, it will end up being connected to a **virtual** USB 1.1 hub, therefore slowing down its speed to 12Mb/s and if the device does not support that, Windows may fail to recognize or even use it.

So in the example above, two XHCI hubs are created manually. This gives us either 6 USB 3.0, or 8 USB 1.1-2.0 ports, depending on what's connected and if QEMU doesn't whine about a speed mismatch. If it does, the device will be connected to the next available XHCI hub.

# Quick start (Ubuntu 20.10)

1. `git clone https://github.com/darkguy2008/hotplugger.git`

2. (Optional) run `python3 monitor.py` and follow the prompts. Basically once you hit Enter you have to plug and unplug an USB device (a thumb drive or audio device preferred) into the USB ports that you want to know their `DEVPATH` route from. This will help you identify them so you can write them into `config.yaml` in the `ports` array. This array only accepts `DEVPATH` routes that `UDEV` generates.

3. Edit `config.yaml`. **It must stay in the same folder as `monitor.py` and `hotplugger.py`**. Using the following file as example:

   ```
   virtual_machines:
   
     windows:
       socket: /home/user/vm/windows/qmp-sock
       delay: 1
       hubs:
         - xhci0.0
         - xhci1.0
       ports:
         - /devices/pci0000:00/0000:00:14.0/usb3/3-3
         - /devices/pci0000:00/0000:00:14.0/usb3/3-4
   ```

   This is for a Windows VM where its UNIX QEMU QMP socket is located at `/home/user/vm/windows/qmp-sock`, with a 1-second delay after a device is plugged to actually do the hotplugging to QEMU, with two virtual XHCI hubs that will receive all the USB devices in the 2 USB ports denoted as `/devices/pci0000:00/0000:00:14.0/usb3/3-3` and `/devices/pci0000:00/0000:00:14.0/usb3/3-4` . To figure this out, I ran `monitor.py` and got this output:

   ```
   Monitoring USB ports...
   ^C
   DEVPATH=/devices/pci0000:00/0000:00:14.0/usb3/3-3
   DEVPATH=/devices/pci0000:00/0000:00:14.0/usb3/3-3/3-1:1.0
   DEVPATH=/devices/pci0000:00/0000:00:14.0/usb3/3-4
   DEVPATH=/devices/pci0000:00/0000:00:14.0/usb3/3-4/3-1:1.0
   DEVPATH=/devices/pci0000:00/0000:00:14.0/usb3/3-4/3-1:1.1
   ```

   So this means that I have to enter **only** the shortest entries: `/devices/pci0000:00/0000:00:14.0/usb3/3-3` and `/devices/pci0000:00/0000:00:14.0/usb3/3-4`

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

5. Have a coffee! ☕

# Libvirt setup

This is a work in progress, but here's some steps to get you started:

1. Edit your VM's XML config like this:

   1. ```xml
      <domain type='kvm' xmlns:qemu='http://libvirt.org/schemas/domain/qemu/1.0'>
        <name>QEMUGuest1</name>
        <uuid>c7a5fdbd-edaf-9455-926a-d65c16db1809</uuid>
        ...
        <qemu:commandline>
          <qemu:arg value='-chardev'/>
          <qemu:arg value='socket,id=mon1,server=on,wait=off,path=/tmp/my-vm-sock'/>
          <qemu:arg value='-mon'/>
          <qemu:arg value='chardev=mon1,mode=control,pretty=on'/>
        </qemu:commandline>
      </domain>
      ```

      Add the `xmlns` attribute and the QEMU commandline arguments like that. The `/tmp/my-vm-sock` is the name of an unix domain socket. You can use any, just make sure to also put the same path in the `config.yaml` file.

2. If you get a permissions issue, edit `/etc/libvirt/qemu.conf` and add `security_driver = "none"`to it to fix apparmor being annoying about it.

### How it works

1. The `udev` rule launches the script on *every* USB event. For each USB `add`/`remove` action there's around 3 to 5+ events. This allows the app to act at any step in the action lifecycle.
2. In the first step it gets the kernel environment variables from `udev` and stores them in a temp file. In those variables, the `DEVPATH`, the `DEVNUM` (host address in QEMU, it seems to change and is sequential...) and the `BUSNUM` (bus address in QEMU) are captured. For the subsequent events, the following steps are run:
   1. It requests QEMU through the Unix socket and the `info usbhost` QMP command the USB info from the host. This gives it an extra field: The host **port** where the device is also connected to. Since I got the `host` and `bus` addresses in the first event, I can use that to parse through the `info usbhost` command's output and find the **port** connected to the device.
   2. If the port is found, using the `device_add` command, a new `usb-host` device is added using the USB `bus` and `port` we got in the previous step, and assigns it a predictable ID that it can use to unplug the device afterwards.
   3. The temp file is cleared once the `device_add` command has run successfully.

Steps 2.1, 2.2 and 2.3 are run on every `udev` event. For instance, for an audio device it gets 3 or 4 events: One for the HID device, and two or so for the audio devices. My audio device (Corsair Void Elite Wireless) has both stereo audio and a communications device (mono audio, for mic) so for a single dongle like that I get those many events. Since these steps are ran on all the events, there's multiple chances to do the hotplug action. When one of them succeeds, the others will silently fail as QEMU will say that the same device ID is being used, so all is good.

## Troubleshooting

If for some reason the app doesn't seem to work, try these methods:

* Remove the `tmp` folder where `hotplugger.py` is located
* Reboot the computer
* Reboot `udev`: `sudo udevadm control --reload-rules && sudo udevadm trigger`
* View `udev`'s logfile: `sudo service udev restart && sudo udevadm control --log-priority=debug && journalctl -f | grep -i hotplugger`
* If you want to see what will be run when you plug a device, try with this command to simulate an `udev` event: `udevadm test $(udevadm info -a --path=/devices/pci0000:00/0000:00:14.0/usb3/3-1/3-1:1.0) --action=add` replacing `--path` with the path of the USB port down to the device itself (in this case, I had a device connected to the `usb3/3-1` port, identified as `3-1:1.0`.

## Thank you!

A lot of work and sleepless nights were involved in this procedure, so if this app helps you in any way or another, please consider sending a small donation, it helps a lot in these tough times! 

[<img src="https://www.paypalobjects.com/en_US/i/btn/btn_donate_LG.gif">](https://www.paypal.com/donate?hosted_button_id=H2YLSRHBQJ94G)

## Changelog

(2020-02-09)

* More python mad skillz were learned, and therefore used. 
* It seems the USB IDs for QEMU were duplicated so when you unplugged a device, others would do too because the first plug of the new device already matched the ID of the device that was already plugged in, so when you unplugged the new device, the one in the same hub was unplugged too. I know it's confusing but so it was when debugging it. You don't have to understand it, just be happy it's now fixed, lol!
* Figured out that `DEVNAME` is a valid unique ID per USB device per USB port, so I'm using that instead.
* The app will now cycle through the defined USB hubs for that VM (so you can have 1 or more XHCI hubs)  in the case that when plugging the device it would receive the warning "`Warning: speed mismatch trying to attach usb device "DEVICE" (high speed) to bus "xhci0.0", port "4.2" (full speed)`". In this case, it will remove it from the hub and attempt to plug it on the next one. Maybe some verification could be done here from `info usbhost` and check the device's USB speed, then checking with `info usb` the allocated ports and find out if a hub is full or has a `QEMU Root USB Hub` to decide the next hub to add the device to. It doesn't affect me much now, so I'm leaving that on the backburner for now.

(2020-02-05)

* Initial changelog writing
* App was refactored a bit with improved python mad skillz. It also seems to be a bit more stable and robust, it doesn't hang much anymore and USB detection seems to work better. This is due to the fact that I added a stupid 1-second delay after all the USB UDEV events have gone through. Since there's no way to know when UDEV has "finished" sending all the events (and there could be a lot more) the commands being sent to QEMU to add the device will have to wait 1 second now. While it's not ideal, it should be enough to avoid a VM hanging up and I can live with that.
