#!/usr/bin/env python3

## Quellen:
# - http://abyz.me.uk/rpi/pigpio/index.html
# - https://github.com/joan2937/pigpio


import pigpio           # Verwendung: http://abyz.me.uk/rpi/pigpio/python.html#set_servo_pulsewidth
                        # Beachten: bevor mittels l = pigpio.pi() eine Instanz der pigpio.pi Klasse erstellt werden kann, muss der Daemon "pigpiod" mittels "sudo pigpiod" gestartet werden!
import os               # wird verwendet, um pigpiod automatisch zu starten
import time

## Eigenschaften der Servo:

SignalPin = 18 # GPIO-Pin
_minPW = 750    # minimale Impulsdauer in µs
_maxPW = 2250   # max Impulsdauer in µs

## Einschränkung des Bewegungsradiuses (in Prozent):

# Die Werte ergeben sich durch den eingeschränkten Lenkradius der Lenkmechanik.
# Falsche Werte können zu Beschädigungen führen!

_ll = 33 # linkes Limit in Prozent !MUSS kleiner als rl sein
_rl = 72 # rechtes Limit in Prozent !MUSS größer als ll sein

## ----------------------



## interne Variablen und Berechnungen:

# Prüfung auf gültige Eingaben:
if (_ll not in range(101) or _rl not in range(101) or _rl < _ll):
    raise ValueError ("rl must be higher than ll and both must be Integers between 0 and 100!")

# Berechnung der minimalen und maximalen Pulsweite innerhalb des angegebenen Bewegungsradiuses:

_k= (_maxPW - _minPW)/100

_maxPW = _rl * _k + _minPW
_minPW = _ll * _k + _minPW

_k = (_maxPW - _minPW)/100


## Funktionsdefinitionen
    
def PercentToPW(Percent):
    return Percent * _k + _minPW


def setPosition(newPos):
    """
    Setzt die Servo auf die in Prozent angegebene Position, die automatisch in den "erlaubten Bereich"
    gemappt wird.
    Bei Erfolg gibt die Funktion True, ansonsten False zurück.
    """
    global Pos  # Position als global definiert--> bleibt nach Funktionsaufruf erhalten
    newPos+=0.5 # Damit newPos richtig gerundet wird
    if int(newPos) in range(101):
        Pos = int(newPos)
        l.set_servo_pulsewidth(SignalPin, PercentToPW(Pos))
        return True
    else:
        print("ERROR: Position must be between 0 (left limit) and 100 (right limit)!")
        return False
    
setPos = setPosition # shortcut für weniger Schreibarbeit
    
def setCurrentPos():
    """
    Setzt Servo auf zuletzt festgelegte Position
    """
    if Pos in range(101):
        l.set_servo_pulsewidth(SignalPin, PercentToPW(Pos))
        return True
    else:
        print("ERROR: Position out of Range")
        return False
              
    
def Disable(): # Deaktiviert die Servo
    l.set_servo_pulsewidth(SignalPin, 0)
    
def setCenter():
    setPosition(50)
    
def getPos():
    return Pos

def getPW():
    return l.get_servo_pulsewidth(SignalPin)


    
## Initialisierungen:
    
Pos = 50              # Anfangsposition = Mittelstellung       

print("trying to connect to pigpio daemon")
l = pigpio.pi()       # mit pigpio-Daemon verbinden und ein Objekt der Klasse pigpio.pi erstellen

i=0
while not l.connected and i<5:
    os.system("sudo pigpiod")
    time.sleep(5)     # pigpiod needs some time to startup...
    l = pigpio.pi()
    i+=1
if l.connected:
    print("\nsuccessfully connected to pigpio daemon\n")
else:
    print("\ncould not connect to pigpiod after {} tries\n".format(i+1))