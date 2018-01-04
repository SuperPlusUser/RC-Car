#!/usr/bin/env python3

## Quellen:
# - http://abyz.me.uk/rpi/pigpio/python.html

## TODO:
# - Exception Handling, z.B. out-of-range Werte für speed abfangen...
# - Bools als Rückgabewerte?

import pigpio           # Verwendung: http://abyz.me.uk/rpi/pigpio/python.html#set_servo_pulsewidth

## Parameter:

freq = 50                  # PWM-Frequenz
range = 100             # PWM-Range

## Portdefinition:

en = 17                 # Hauptmotor

in1 = 27                # Motor Forwaerts: 0
in2 = 22                # Motor Forwaerts: 1



## Initialisierungen:

v = pigpio.pi()          # pigpiod muss im Hintergrund laufen!
v.set_mode(en, pigpio.OUTPUT)
v.set_mode(in1, pigpio.OUTPUT)
v.set_mode(in2, pigpio.OUTPUT)

# PWM Einstellungen für en übernehmen:
v.set_PWM_frequency(en, freq)
v.set_PWM_range(en, range)


## Funktionsdefinitionen:

# Hauptmotor:

def forward(speed):
    v.write(in1, 0)
    v.write(in2, 1)
    v.set_PWM_dutycycle(en,speed)

def backward(speed):
    v.write(in1, 1)
    v.write(in2, 0)
    v.set_PWM_dutycycle(en,speed)

def roll():
    v.set_PWM_dutycycle(en,0)

def brake():
    v.write(in1, 1)
    v.write(in2, 1)
    v.set_PWM_dutycycle(en,100)
        
def drive(speed):
    if speed < 0:
        backward(0-speed)
    elif speed == 0:
        roll()   
    else:
        forward(speed)
        
setSpeed = drive
        
def getDC():
    return v.get_PWM_dutycycle(en)

getSpeed = getDC