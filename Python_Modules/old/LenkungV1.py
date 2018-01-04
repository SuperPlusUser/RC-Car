#!/usr/bin/env python3

## Quellen:
#  - https://tutorials-raspberrypi.de/raspberry-pi-servo-motor-steuerung/

## TODO:
# - Pos darf nicht direkt von außen verändert werden! --> wie auf Private setzen?
# - private und öffentliche Funktionen

import RPi.GPIO as GPIO # Verwendung: https://sourceforge.net/p/raspberry-gpio-python/wiki/PWM/

## Eigenschaften der Servo:

SignalPin = 21 # GPIO-Pin
TServo = 20 # Periodendauer in ms
minImp = 0.75  # minimale Impulsdauer in ms
maxImp = 2.25  # max Impulsdauer in ms

## Einschränkung des Bewegungsradiuses (in Prozent):

ll = 0 # linkes Limit in Prozent !MUSS kleiner als rl sein
rl = 100 # rechtes Limit in Prozent !MUSS größer als ll sein

MS =  int((rl-ll)/2 + ll) # Mittelstellung in Prozent !MUSS zwischen ll und rl liegen

## ----------------------


## interne Variablen:

freq = 1000/TServo

minDC = 100 * (minImp/TServo)
maxDC = 100 * (maxImp/TServo)
rangeDC = maxDC - minDC

## Funktionsdefinitionen

def PercentToRange(Percent):
    return Percent/100 * (rl-ll) + ll
    
def rPercentToDC(rPercent):
    return rPercent/100 * rangeDC + minDC

def PercentToDC(Percent):
    return rPercentToDC(PercentToRange(Percent))


def setPosition(newPos):
    """
    Setzt die Servo auf die in Prozent angegebene Position, die automatisch in den "erlaubten Bereich"
    gemappt wird
    """
    global Pos  # Position als global definiert--> bleibt nach Funktionsaufruf erhalten
    newPos+=0.5 # Damit newPos richtig gerundet wird
    if int(newPos) in range(101):
        Pos = int(newPos)
        l.ChangeDutyCycle(PercentToDC(Pos))
        return True
    else:
        print("ERROR: Position must be between 0 (left limit) and 100 (right limit)!")
        return False
    
    
setPos = setPosition
    
def setCurrentPos():
    """
    Setzt Servo auf zuletzt festgelegte Position
    """
    if Pos in range(101):
        l.ChangeDutyCycle(PercentToDC(Pos))
        return True
    else:
        print("ERROR: Position out of Range")
        return False
              
    
def Disable(): # Deaktiviert die Servo
    l.ChangeDutyCycle(0)
    
def setCenter():
    setPosition(MS)
    
def getPos():
    return Pos

def getDC():
    return PercentToDC(Pos)

    
## Initialisierungen:
    
# Prüfung auf gültige Eingaben:
if (ll not in range(101) or rl not in range(101) or rl < ll):
    raise ValueError ("rl must be higher than ll and both must be Integers between 0 and 100!")
    
if MS in range(ll,rl):
    Pos = MS # Anfangsposition = Mittelstellung MS
else:
    raise ValueError ("MS must be an Integer between rl and ll!")
        

GPIO.setmode(GPIO.BCM)
GPIO.setup(SignalPin, GPIO.OUT)

l = GPIO.PWM(SignalPin, freq)         # PWM Frequenz festlegen
l.start(PercentToDC(Pos))             # In Mittelstellung initialisieren
