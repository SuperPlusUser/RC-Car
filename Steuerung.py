#!/usr/bin/env python3

## Version 0.1 (UNGETESTET!)

## TODO:
# - Testen!


import sys
import asyncio

sys.path.append('Python_Modules')       # Falls die Python-Module in einem eigenen Unterordner sind.
import Lenkung as Lnk
import Motorsteuerung as Mtr


DISABLE_MOTOR_DELAY = 5       # Nach dieser Anzahl an Sekunden wird der Motor automatisch deaktiviert, falls kein neuer Steuerungsbefehl empfangen wird

def init(loop):
    ## Initialisierungen (muss am Anfang aufgerufen werden!):
    global driveTask
    driveTask = loop.create_task(_driveForSec(0, 1))
    DisableMtr = False # Wenn True, werden keine Fahranweisungen angenommen
    Limit = 100

def driveForSec(loop, speed, time = DISABLE_MOTOR_DELAY):
    global driveTask
    if not DisableMtr:
        driveTask.cancel()
        driveTask = loop.create_task(_driveForSec(speed,time))
        return True
    else:
        return False

def brakeForSec(loop, time = DISABLE_MOTOR_DELAY):
    global driveTask
    driveTask.cancel()
    driveTask = loop.create_task(_brakeForSec(time))

def setLimit(l):
    """
    Ermöglicht das Limitieren der Motorgeschwindigkeit. 
    Das uebergebene Limit dient als Faktor für die Geschwindigkeit
    und muss zwischen 0 (Motor deaktiviert) und 100 (volle Geschwindigkeit) liegen.
    """
    global limit
    if l < 0 or l > 100:
        raise ValueError("Limit must be between 0 and 100")
    limit = l

def Disable():
    DisableMtr = True

def Enable():
    DisableMtr = False

async def _driveForSec(speed, time):
    global Limit
    print("Driving with speed {}".format(speed))
    Mtr.setSpeed(speed * Limit)
    await asyncio.sleep(time)
    Mtr.setSpeed(0)
    print("Motor disabled, because there was to long no new drive command")

async def _brakeForSec(time):
    global DisableMtr
    print("Braking for {}".format(time))
    DisableMtr = True
    Mtr.brake()
    await asyncio.sleep(time)
    DisableMtr = False
    Mtr.setSpeed(0)
    print("Motor disabled, because there was to long no new drive command")



if __name__ == "__main__":
    # Hier ergaenzen, was da Modul machen soll, wenn es direkt als skript gestartet wird.
    print("This Module is currently not intended to be started as a script! Exiting...")
