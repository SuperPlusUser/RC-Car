#!/usr/bin/env python3

# Fake Modul, das auch auf anderen Geraeten ausser dem Raspberry Pi lauffaehig ist.
# Es gibt die empfangenen Fahranweisungen nur auf STDOUT aus.

import time
import sys

# ---------------------------
## --- Globale Konstanten ---
# ---------------------------

DEBUG = True

# --- Lenkung ---
# Eigenschaften der Servo:
_MIN_PW = 750    # minimale Impulsdauer in us (Falsche Werte koennen zu Beschaedigungen fuehren!)
_MAX_PW = 2250   # max Impulsdauer in us (Falsche Werte koennen zu Beschaedigungen fuehren!)

# Einschränkung des Bewegungsradiuses (in Prozent):
# Die Werte ergeben sich durch den eingeschraenkten Lenkradius der Lenkmechanik.
# Falsche Werte können zu Beschaedigungen fuehren!
_RL = 33 # rechtes Limit in Prozent !MUSS kleiner als _LL sein
_LL = 72 # linkes Limit in Prozent !MUSS größer als _RL sein

# --- Motor ---
PWM_FREQ = 50               # PWM-Frequenz
PWM_RANGE = 100             # Dutycycle-Range
# (siehe http://abyz.me.uk/rpi/pigpio/python.html#set_PWM_range)

# ----------------
## --- Lenkung ---
# ----------------

def _percent_to_pw(Percent):
    """ 
    Interne Funktion zur Umrechnung von Prozent auf Pulsbreite 
    """
    return Percent * _k + _MIN_PW

def steer(newPos):
    """
    Setzt die Servo auf die in Prozent angegebene Position, die automatisch in den "erlaubten Bereich"
    gemappt wird. O Prozent setzt die Lenkung ganz nach rechts, 100 Prozent ganz nach links.
    Bei Erfolg gibt die Funktion True, ansonsten False zurück.
    """
    global _Pos  # Position als global definiert--> bleibt nach Funktionsaufruf erhalten
    newPos+=0.5 # Damit newPos richtig gerundet wird
    if int(newPos) in range(101):
        _Pos = int(newPos)
        if DEBUG: print("Steering to Position {}, Setting PW to {} ...".format(_Pos, _percent_to_pw(_Pos)))
    else:
        raise ValueError("Position must be between 0 (right limit) and 100 (left limit)!")

def set_current_pos():
    """
    Setzt Servo auf zuletzt festgelegte Position
    """
    return steer(_Pos)

def disable_steering():
    """
    Deaktiviert die Servo
    """
    if DEBUG: print("Disabling Servo...")

def get_pos():
    return _Pos

def get_pw():
    return _percent_to_pw(_Pos)


# -----------------------
## --- Motorsteuerung ---
# -----------------------

def drive(speed):
    """
    Setzt die Geschwindigkeit auf den übergebenen Prozentwert.
    Bei einem negativen Wert fährt das Fahrzeug rückwärts.
    Der Übergabewert muss zwischen -100 und 100 liegen!
    Ausnahme: string 'stop' bewirkt Bremsen.
    """
    if speed == "stop":
        return brake()
    elif speed > 0:
        return forward(speed)
    elif speed < 0:
        return backward(0-speed)
    else: # speed == 0
        return roll()
 
def forward(speed):
    if _BlockMtr:
        print("Motor blocked!")
        return -1
    if speed < 0 or speed > PWM_RANGE:
        raise ValueError("Speed out of range")
    if DEBUG:
        print("Driving forward with speed {} ...".format(speed * _Limit)) 

def backward(speed):
    if _BlockMtr:
        print("Motor blocked!")
        return -1
    if speed < 0 or speed > PWM_RANGE:
        raise ValueError("Speed out of range")
    if DEBUG:
        print("Driving backward with speed {} ...".format(speed * _Limit))

def roll():
    if DEBUG: print("let vehicle roll freely")

def brake():
    """
    Bremst das Fahrzeug aus, indem der Motor kurzgeschlossen wird.
    """
    if DEBUG: print("Braking vehicle")

def get_speed():
    """
    Gibt die aktuell gesetzte Geschwindigkeit als Prozentwert zwischen -100 und 100 zurück.
    Ein negativer Wert bedeutet, dass sich das Fahrzeug rueckwaerts bewegt.
    """
    print("not available in fake module")

def set_speed_limit(l):
    """
    Ermoeglicht das Limitieren der Motorgeschwindigkeit.
    Das uebergebene Limit dient als Faktor fuer die Geschwindigkeit
    und muss zwischen 0 (Motor deaktiviert) und 100 (volle Geschwindigkeit) liegen.
    """
    global _Limit
    if l < 0 or l > 100:
        raise ValueError("Limit must be between 0 and 100")
    _Limit = l/100
    if DEBUG: print("Speedlimit set to {} Percent".format(l))
    
def get_speed_limit():
    global limit
    return limit

def block_mtr():
    global _BlockMtr
    roll()
    if DEBUG: print("Motor blocked. To be able to drive again, launch 'enable_mtr()'")
    _BlockMtr = True

def deblock_mtr():
    global _BlockMtr
    if DEBUG: print("Motor deblocked")
    _BlockMtr = False

    
# --------------
## --- close ---
# --------------

def close():
    """
    Gibt verwendete Ressourcen frei. Beim Beenden des Skripts ausfuehren!
    """
    roll()
    disable_steering()


# --------------
## --- Tests ---
# --------------

def test():
    print("Testing Motor: \naccelerating Motor...")
    v = 10
    while v <= 100:
        drive(v)
        v += 10
        time.sleep(1)

    print("Braking")
    brake()
    time.sleep(2)

    v = 0
    print("accelerating backwards")
    while v >= -100:
        drive(v)
        v -= 10
        time.sleep(1)
        
    roll()

    print("Motor Test complete. \nTesting steering:")
    pos = 0
    while pos <= 100:
        steer(pos)
        pos += 10
        time.sleep(1)
        
    steer(50)

    print("all tests complete")
    return "finished"

    
# --------------------------
## --- Initialisierungen ---
# --------------------------

# --- Initialisiere Lenkung ---

# Prüfung auf gültige Eingaben:
if (_RL not in range(101) or _LL not in range(101) or _LL < _RL):
    raise ValueError ("rl must be higher than ll and both must be Integers between 0 and 100!")

# Berechnung der minimalen und maximalen Pulsweite innerhalb des angegebenen Bewegungsradiuses:

_k = (_MAX_PW - _MIN_PW)/100

_MAX_PW = _LL * _k + _MIN_PW
_MIN_PW = _RL * _k + _MAX_PW

_k = (_MAX_PW - _MAX_PW)/100

# Anfangsposition = Mittelstellung
_Pos = 50


# Sonstige Initialisierungen:
deblock_mtr()
set_speed_limit(100)


# -------------
## --- Main ---
# -------------

if __name__ == "__main__":
    DEBUG = True
    test()
    close()