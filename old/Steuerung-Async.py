#!/usr/bin/env python3

## Version 0.2

## TODO:
# - Alle hier definierten Funktionen in Motorstrg. oder Lenkungs-Modul integrieren --> Dieses Modul ueberfluessig!
# - pigoio an anderer Stelle starten

## Changelog:
#
# --- Version 0.2 ---
# - Funktionen ergaenzt
# - Test-Fkt hinzufeguegt
# - ...

import sys
import asyncio

import Lenkung as Lnk # Lenkung immer zuerst, da hier pigpio gestartet wird
import Motorsteuerung as Mtr

# ------------------------------------------
## Globale Konstanten:
# ------------------------------------------

DEBUG = True if "-d" in sys.argv else False

# Nach dieser Anzahl an Sekunden wird der Motor automatisch deaktiviert, falls kein neuer Steuerungsbefehl empfangen wird
DISABLE_MOTOR_DELAY = 1

# Falls größer 0, wird die Servo automatisch nach so vielen Sekunden deaktiviert.
DISABLE_STEERING_DELAY = 60

# ------------------------------------------
## Initialisierungen:
# ------------------------------------------
def init():
    """Initialisierungen (muss am Anfang aufgerufen werden!)"""
    global driveTask, steerTask, limit, _DisableMtr
    # Speed Anfangs auf 0:
    driveTask = asyncio.ensure_future(_drive_for_sec(0, 1))
    # Lenkung anfangs in Mittelposition:
    steerTask = asyncio.ensure_future(_steer_for_sec(50, DISABLE_STEERING_DELAY))
    _DisableMtr = False  # Wenn True, werden keine Fahranweisungen angenommen
    set_limit(100)


# ------------------------------------------
## Motorsteuerung:
# ------------------------------------------
def drive(speed, time = DISABLE_MOTOR_DELAY):
    global driveTask, limit
    if not _DisableMtr:
        if time:
            driveTask.cancel()
            driveTask = asyncio.ensure_future(_drive_for_sec(speed * limit, time))
        else: # Falls time = 0 fuer immer fahren
            if DEBUG: print("Driving with speed {} forever!".format(speed))
            Mtr.setSpeed(speed * limit)
        return True
    else:
        return False

def brake(time = DISABLE_MOTOR_DELAY):
    global driveTask
    driveTask.cancel()
    driveTask = loop.create_task(_brake_for_sec(time))

def set_limit(l):
    """
    Ermoeglicht das Limitieren der Motorgeschwindigkeit.
    Das uebergebene Limit dient als Faktor für die Geschwindigkeit
    und muss zwischen 0 (Motor deaktiviert) und 100 (volle Geschwindigkeit) liegen.
    """
    global limit
    if l < 0 or l > 100:
        raise ValueError("Limit must be between 0 and 100")
    limit = l/100

def disable_mtr():
    _DisableMtr = True

def enable_mtr():
    _DisableMtr = False

async def _drive_for_sec(speed, time):
    if DEBUG:
        print("Driving with speed {} for {} sec".format(speed, time))
    Mtr.setSpeed(speed)
    await asyncio.sleep(time)
    Mtr.setSpeed(0)
    if DEBUG:
        print("Motor disabled, because there was to long no new drive command")

async def _brake_for_sec(time):
    if DEBUG:
        print("Braking for {} sec".format(time))
    Mtr.brake()
    await asyncio.sleep(time)
    Mtr.setSpeed(0)
    if DEBUG:
        print("Motor disabled, because there was to long no new drive command")


# ------------------------------------------
## Lenkung:
# ------------------------------------------
def steer(Pos, time = DISABLE_STEERING_DELAY):
    global steerTask
    if time:
        steerTask.cancel()
        steerTask = asyncio.ensure_future(_steer_for_sec(Pos, time))
    else: # falls time = 0 Lenkung nie deaktivieren
        if DEBUG: print("Steering to Position {} forever!".format(Pos))
        Lnk.setPos(Pos)

def disable_steering():
    return Lnk.Disable()

async def _steer_for_sec(Pos, time):
    if DEBUG:
        print("Steering to Position {} for {} sec".format(Pos, time))
    Lnk.setPos(Pos)
    await asyncio.sleep(time)
    Lnk.Disable()
    if DEBUG:
        print("Servo disabled, because there was to long no new steering command")


# ------------------------------------------
## Tests:
# ------------------------------------------
async def test():
    print("Testing Motor: \naccelerating Motor...")
    v = 10
    while v <= 100:
        drive(v)
        v += 10
        await asyncio.sleep(1)

    print("Braking")
    brake()
    await asyncio.sleep(2)

    v = 0
    print("accelerating backwards")
    while v >= -100:
        drive(v)
        v -= 10
        await asyncio.sleep(1)

    print("Motor Test complete. \nTesting steering:")
    pos = 0
    while pos <= 100:
        steer(pos)
        pos += 10
        await asyncio.sleep(1)

    print("all tests complete")

    return "finished"


# ------------------------------------------
## Main:
# ------------------------------------------
if __name__ == "__main__":
    # Hier ergaenzen, was da Modul machen soll, wenn es direkt als Skript gestartet wird.
    DEBUG = True
    loop = asyncio.get_event_loop()
    init()
    loop.run_until_complete(test())
    disable_steering()
