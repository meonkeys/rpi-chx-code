# This is a library for controlling the 12V DC motor.

# chxmotor.py
# Copyright (C) 2018 Adam Monsen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import RPi.GPIO as GPIO
import time

MotorPin_A         = 38
MotorPin_B         = 40

def _motorStop():
    GPIO.output(MotorPin_A, GPIO.LOW)
    GPIO.output(MotorPin_B, GPIO.LOW)

def setup(magPin):
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)
    # L9110 motor driver
    GPIO.setup(MotorPin_A, GPIO.OUT)
    GPIO.setup(MotorPin_B, GPIO.OUT)
    GPIO.output(MotorPin_A, GPIO.LOW)
    GPIO.output(MotorPin_B, GPIO.LOW)
    # hall effect sensor (hopefully!)
    GPIO.setup(magPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def _motor(direction):
    if direction == 'forward':
        GPIO.output(MotorPin_A, GPIO.HIGH)
        GPIO.output(MotorPin_B, GPIO.LOW)
    else:
        GPIO.output(MotorPin_A, GPIO.LOW)
        GPIO.output(MotorPin_B, GPIO.HIGH)

def _destroy():
    _motorStop()
    GPIO.cleanup()             # Release resource

def _hit_mag_sensor(magPin):
    return GPIO.input(magPin) == 0

def actuate(direction, magPin, timeout):
    rv = {}
    start_time = time.time()
    setup(magPin)
    try:
        _motor(direction)
        while True:
            rv['elapsed'] = (time.time() - start_time)
            if (rv['elapsed'] > timeout):
                rv['result'] = 'timeout'
                break
            if _hit_mag_sensor(magPin):
                rv['result'] = 'hit_mag_sensor'
                break
            # loop delay
            time.sleep(0.25)
        _motorStop()
    except KeyboardInterrupt:
        pass
    finally:
        _destroy()

    return rv
