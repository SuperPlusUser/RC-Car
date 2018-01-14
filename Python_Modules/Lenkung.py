#!/usr/bin/env python3

## Quellen:
# - http://abyz.me.uk/rpi/pigpio/index.html
# - https://github.com/joan2937/pigpio

import pigpio
# Verwendung: http://abyz.me.uk/rpi/pigpio/python.html#set_servo_pulsewidth
# Beachten: bevor mittels l = pigpio.pi() eine Instanz der pigpio.pi Klasse
# erstellt werden kann, muss der Daemon "pigpiod" mittels "sudo pigpiod" gestartet werden!

import os               # wird verwendet, um pigpiod automatisch zu starten
import time
from threading import Timer # Ermöglicht es, die Servo nach einer gewissen Zeit automatisch zu deaktivieren

## --- Variablen-Definitionen ---

timeAutoDisable = 60
# Falls größer 0, wird die Servo automatisch nach so vielen Sekunden deaktiviert.

## Eigenschaften der Servo:

SignalPin = 18  # GPIO-Pin der Servo
_minPW = 750    # minimale Impulsdauer in µs (Falsche Werte können zu Beschädigungen führen!)
_maxPW = 2250   # max Impulsdauer in µs (Falsche Werte können zu Beschädigungen führen!)

## Einschränkung des Bewegungsradiuses (in Prozent):

# Die Werte ergeben sich durch den eingeschränkten Lenkradius der Lenkmechanik.
# Falsche Werte können zu Beschädigungen führen!

_RL = 33 # rechtes Limit in Prozent !MUSS kleiner als _LL sein
_LL = 72 # linkes Limit in Prozent !MUSS größer als _RL sein

## ------------------------------


## Funktionsdefinitionen
    
def PercentToPW(Percent):
    return Percent * _k + _minPW


def setPosition(newPos):
    """
    Setzt die Servo auf die in Prozent angegebene Position, die automatisch in den "erlaubten Bereich"
    gemappt wird. O Prozent setzt die Lenkung ganz nach rechts, 100 Prozent ganz nach links.
    Bei Erfolg gibt die Funktion True, ansonsten False zurück.
    """
    global _Pos  # Position als global definiert--> bleibt nach Funktionsaufruf erhalten
    
    newPos+=0.5 # Damit newPos richtig gerundet wird
    if int(newPos) in range(101):
        _Pos = int(newPos)
        
        global tmr
        if tmr:
            if tmr.isAlive():
                tmr.cancel()
            tmr = Timer(timeAutoDisable, Disable)
            tmr.start()
            
        ret = l.set_servo_pulsewidth(SignalPin, PercentToPW(_Pos))
        if(ret): # Wenn ein Rückgabewert außer 0 zurück geliefert wird, ist ein Fehler aufgetreten.
            print("pigpio failed to set pulsewidth with errorcode {}".format(ret))
            return False
        else:
            return True
    
    else:
        print("ERROR: Position must be between 0 (left limit) and 100 (right limit)!")
        return False
    
setPos = setPosition # shortcut für weniger Schreibarbeit
    
def setCurrentPos():
    """
    Setzt Servo auf zuletzt festgelegte Position
    """
    return setPosition(_Pos)
   
def Disable():
    """
    Deaktiviert die Servo
    """
    global tmr
    if tmr:
        if tmr.isAlive():
            tmr.cancel()
            
    ret = l.set_servo_pulsewidth(SignalPin, 0)
    if(ret): # Wenn ein Rückgabewert außer 0 zurück geliefert wird, ist ein Fehler aufgetreten.
        print("pigpio failed to disable servo with errorcode {}".format(ret))
        return False
    else:
        print("Servo Disabled")
        return True
    
def setCenter():
    return setPosition(50)
    
def getPos():
    return _Pos

def getPW():
    return l.get_servo_pulsewidth(SignalPin)

def close():
    """
    Gibt verwendete Ressourcen frei. Beim Beenden des Skripts ausführen!
    """
    Disable()
    return l.stop()
    


## Initialisierungen:

# Prüfung auf gültige Eingaben:
if (_RL not in range(101) or _LL not in range(101) or _LL < _RL):
    raise ValueError ("rl must be higher than ll and both must be Integers between 0 and 100!")

# Berechnung der minimalen und maximalen Pulsweite innerhalb des angegebenen Bewegungsradiuses:

_k = (_maxPW - _minPW)/100

_maxPW = _LL * _k + _minPW
_minPW = _RL * _k + _minPW

_k = (_maxPW - _minPW)/100

# Anfangsposition = Mittelstellung
_Pos = 50


if timeAutoDisable > 0:
    tmr = Timer(timeAutoDisable, Disable)
else:
    tmr = False

print("trying to connect to pigpio daemon")
l = pigpio.pi()       # mit pigpio-Daemon verbinden und ein Objekt der Klasse pigpio.pi erstellen


## Sicherstellen, dass pigpiod läuft:

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
    

pigpio.exceptions = False
# Erlaubt es, Fehler von pigpiod anhand des Rückgabewerts zu behandeln
# (wenn kein Fehler auftritt ist der Rückgabewert 0.
# Falls z.B. ein Übergabe-Parameter außerhalb des erlaubten Bereichs ist -8)