# Raspberry Pi Automatic Chicken Door controller software

## Features

* hardware interleave gravity lock mechanism
* instant-read photoresistor poll door actuation trigger
* photoresistor signal analog to digital conversion
* worm gear 12V DC motor controlled via L9110 motor driver chip
* dual hall-effect magnetic door position sensors
* fallback door status mitigating magnetic sensor failure
* night-vision wide-angle camera with motion-triggered video capture
* C + bash + python polyglot control code with standardized output convention
* offline operation with 2.4Ghz wifi for monitoring and maintenance

## This repository

This code is deployed onto the chicken coop raspberry pi computer.

Edit code, commit/push, then deploy with `./deploy`. The deploy script also documents summaries, source, and destination for all code deployed to the pi.

Use `tree Chicken bin` on the Pi to see all deployed code.

## Hardware

Raspberry Pi 3 Model B v1.2. Bought off Amazon.com.

* 1.2GHz 64-bit quad-core ARMv8 CPU
* 1 GB RAM
* 802.11n Wireless LAN, 10/100Mbps Lan Speed
* Bluetooth 4.1, Bluetooth Low Energy
* 4 USB ports, 40 GPIO pins, Full HDMI port, Combined 3.5mm audio jack and composite video
* Camera interface (CSI), Display interface (DSI), Micro SD card slot (now push-pull rather than push-push), VideoCore IV 3D graphics core
* 32 GB SD card

## Operating system

The operating system ([raspbian jesse with PIXEL desktop, v2017-04-10](https://www.raspberrypi.org/downloads/raspbian/)) was written to a 32GB SD card using [Etcher](https://etcher.io/) following [this install guide](https://www.raspberrypi.org/documentation/installation/installing-images/README.md). Something doesn't seem to work with 64GB SD cards... I bricked one before I got it to work on a 32GB SD card.

### `gpio`

The pre-installed `gpio` program can read and manipulate general purpose IO pins.

NOTE: `sudo` is not required to run `gpio` (`Adeept_Starter_Kit_for_RPi_User_Manual.pdf` is out of date in this regard).

    pi@raspberrypi:~ $ gpio -v
    gpio version: 2.44
    Copyright (c) 2012-2017 Gordon Henderson
    This is free software with ABSOLUTELY NO WARRANTY.
    For details type: gpio -warranty

    Raspberry Pi Details:
      Type: Pi 3, Revision: 02, Memory: 1024MB, Maker: Embest
      * Device tree is enabled.
      *--> Raspberry Pi 3 Model B Rev 1.2
      * This Raspberry Pi supports user-level GPIO access.

Watch GPIO pin status, highlighting cumulative differences (this is an undocumented feature of `watch`). 1-second resolution.

    watch -dc -n 1 gpio readall

NOTE: this didn't work for checking mag (hall effect) sensors, I had to use Python code for that. See ./src/scripts/hall-effect-sensor.py . Well, it sorta worked, just not reliably. During testing I noticed the mag sensor values reading incorrect values frequently.

### Other dependencies

Build-time dependencies:

* git v2.x
* GNU system / POSIX
* rsync
* ssh
* FIXME: complete this list (maybe containerize)

Runtime dependencies:

* Python v2.7.x
* Imgur client library: `sudo pip install imgurpython`
* FIXME: complete this list (maybe containerize)

## Forums

* [Raspberry Pi 3 - Not booting the second time](https://www.raspberrypi.org/forums/viewtopic.php?p=1039582#p1039582)

## EE basics

* [Ohm's law calculator](http://www.sengpielaudio.com/calculator-ohmslaw.htm)
* anodes and cathodes
    * Current enters a device via [anode](https://en.wikipedia.org/wiki/Anode). Mnemonic: ACID - anode current into device.
    * Current leaves a device via [cathode](https://en.wikipedia.org/wiki/Cathode). Mnemonic: CCD - cathode current departs.

## Video

During daylight hours when the door is open, Video is captured upon motion detection and uploaded to YouTube. There are several pieces making up this system:

* [motion](https://motion-project.github.io/) is run by systemd
    * stopped at night
* motion triggers the upload to YouTube
    * see the `on_movie_end` handler in `src/motion.conf`
    * `youtube-upload` wraps `youtube-upload.py` to handle errors
    * the YouTube ID is written to a file during upload to detect failed uploads
* youtube-flush is scheduled in pi's crontab
    * posts Slack notification on successful and failed video uploads
    * YouTube ID is flushed (deleted)

## More Links

* <http://adammonsen.com/talks>
* <https://github.com/meonkeys/seagl2017-rpi-talk>
* <https://sourceforge.net/p/raspberry-gpio-python/wiki/>
* <https://www.raspberrypi.org/documentation/usage/gpio/>
* <https://learn.sparkfun.com/tutorials/raspberry-gpio#hardware-setup>
* <https://learn.sparkfun.com/tutorials/raspberry-gpio/python-rpigpio-example>
* <https://pinout.xyz/>
* [Scratch Robot Antenna project](https://www.raspberrypi.org/learning/robot-antenna/)
* <http://davenaves.com/blog/interests-projects/chickens/chicken-coop/arduino-chicken-door/>
* <https://www.raspberrypi.org/blog/mechanise-your-chickens/> & <https://github.com/ericescobar/Chicken_Door/>
* <https://www.bananarobotics.com/shop/How-to-use-the-HG7881-(L9110)-Dual-Channel-Motor-Driver-Module>
* <http://www.petervis.com/Raspberry_PI/Breadboard_Power_Supply/YwRobot_Breadboard_Power_Supply.html>
* <https://circuitdigest.com/microcontroller-projects/controlling-dc-motor-using-raspberry-pi>
* <https://electronics.stackexchange.com/questions/59555/15v-3a-dc-motor-pwm-frequency-setting>
* <https://electronics.stackexchange.com/questions/207344/pwm-and-dc-motor-speed>
* <https://business.tutsplus.com/tutorials/controlling-dc-motors-using-python-with-a-raspberry-pi--cms-20051>
* <https://business.tutsplus.com/tutorials/controlling-dc-motors-using-python-with-a-raspberry-pi--cms-20051>
* <https://www.circuitlab.com>
* <https://www.digikey.com/schemeit/>
* <https://www.autodesk.com/products/eagle/>

## Secrets formats

### `chicken-secrets.json`

```json
{
  "imgur": {
    "album_id": "xxx",
    "client_id": "yyy",
    "client_secret": "zzz",
    "refresh_token": "mmm"
  },
  "slack": {
    "chickenbotWebhookUrl": "https://hooks.slack.com/services/nnn/rrr/sss" 
  }
}
```

### `client-secrets.json`

See <https://developers.google.com/youtube/v3/guides/uploading_a_video>.

### `youtube-upload.py-oauth2.json`

See <https://developers.google.com/youtube/v3/guides/uploading_a_video>.

## Bugs

### network interruption requires power cycle

My raspberry pi is connected via wifi. It still works offline, but it's best if it is on the network so it can send log messages, photos, and video clips. It usually works fine and stays online for weeks or months. If I reboot the wifi access point it is connected to, the pi is unable to reconnect and a power cycle is required.

I tried the `watchdog` package as well as this script from root's crontab:

    #!/bin/bash
    
    ping -c4 192.168.13.1 > /dev/null
    
    # neither ifup/ifdown nor `shutdown -r now` works
    if [[ $? != 0 ]]
    then
        logger "No network connection, rebooting"
        shutdown -r now
        # logger "No network connection, restarting wlan0"
        # ifdown wlan0
        # sleep 8
        # ifup wlan0
    fi

I also disabled wifi power save by adding `wireless-power off` to the interface in `/etc/network/interfaces`. This does disable wifi power save, but still doesn't help wifi automatically reconnect.

Only workaround is a power cycle.

Links:

* <https://www.raspberrypi.org/forums/viewtopic.php?p=537802>
* <https://weworkweplay.com/play/rebooting-the-raspberry-pi-when-it-loses-wireless-connection-wifi/>
* <https://superuser.com/questions/629039/disabling-power-save-option-on-wifi-device>
* <https://askubuntu.com/questions/85214/how-can-i-prevent-iwconfig-power-management-from-being-turned-on/754128#754128>

### imgurpython

[imgurpython](https://github.com/Imgur/imgurpython) is no longer maintained. One extant issue is with image uploading. As-is you'll get this error:

    Endpoint/3/upload does not exist

The fix:

```diff
--- /tmp/old.py	2018-12-09 21:14:43.057884838 -0800
+++ /usr/local/lib/python2.7/dist-packages/imgurpython/client.py	2018-12-09 21:14:01.298249141 -0800
@@ -593,7 +593,7 @@
         data.update({meta: config[meta] for meta in set(self.allowed_image_fields).intersection(config.keys())})
         fd.close()
         
-        return self.make_request('POST', 'upload', data, anon)
+        return self.make_request('POST', 'image', data, anon)
 
     def upload_from_url(self, url, config=None, anon=True):
         if not config:

```

You can do this manually with something like `sudo editor /usr/local/lib/python2.7/dist-packages/imgurpython/client.py`.

# YouTube terms

Some of the code in this respository (e.g. `youtube-upload.py`) interacts with YouTube. Refer to the [YouTube Terms of Service](https://www.youtube.com/t/terms) and the [Google Privacy Policy](https://policies.google.com/privacy).

# Copyleft and License

* Copyright ©2018 Adam Monsen &lt;haircut@gmail.com&gt;
* License: AGPL v3 or later (see COPYING)

All upstream code uses upstream licensing. See individual source files for details.
