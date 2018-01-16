#!/usr/bin/env python3

## Quellen:
# - http://abyz.me.uk/rpi/pigpio/python.html

import pigpio           # Verwendung: http://abyz.me.uk/rpi/pigpio/python.html#set_servo_pulsewidth

## --- Variablen-Definitionen ---

PWM_FREQ = 25               # PWM-Frequenz
PWM_RANGE = 100             # Dutycycle-Range
# (siehe http://abyz.me.uk/rpi/pigpio/python.html#set_PWM_range)

## Portdefinition:

EN = 17                 # Hauptmotor

IN1 = 27                # Motor Forwaerts: 0
IN2 = 22                # Motor Forwaerts: 1

## ------------------------------


## Funktionsdefinitionen:

# Hauptmotor:

def forward(speed):
    if speed >= 0 and speed <= PWM_RANGE:
        v.write(IN1, 0)
        v.write(IN2, 1)
        ret = v.set_PWM_dutycycle(EN,speed)
        if(ret): # Wenn ein Rückgabewert außer 0 zurück geliefert wird, ist ein Fehler aufgetreten.
            print("pigpio failed to set dutycycle with errorcode {}".format(ret))
            return False
        else:
            return True
    else:
        print("ERROR: speed out of range")
        return False

def backward(speed):
    if speed >= 0 and speed <= PWM_RANGE:
        v.write(IN1, 1)
        v.write(IN2, 0)
        ret = v.set_PWM_dutycycle(EN,speed)
        if(ret): # Wenn ein Rückgabewert außer 0 zurück geliefert wird, ist ein Fehler aufgetreten.
            print("pigpio failed to set dutycycle with errorcode {}".format(ret))
            return False
        else:
            return True   
    else:
        print("ERROR: speed out of range")
        return False

def roll():
    ret = v.set_PWM_dutycycle(EN,0)
    if(ret): # Wenn ein Rückgabewert außer 0 zurück geliefert wird, ist ein Fehler aufgetreten.
        print("pigpio failed to set dutycycle with errorcode {}".format(ret))
        return False
    else:
        return True 

def brake():
    """
    Bremst das Fahrzeug aus, indem der Motor kurzgeschlossen wird.
    """
    v.write(IN1, 1)
    v.write(IN2, 1)
    ret = v.set_PWM_dutycycle(EN,PWM_RANGE)
    if(ret): # Wenn ein Rückgabewert außer 0 zurück geliefert wird, ist ein Fehler aufgetreten.
        print("pigpio failed to set dutycycle with errorcode {}".format(ret))
        return False
    else:
        return True 
        
def setSpeed(speed):
    """
    Setzt die Geschwindigkeit auf den übergebenen Prozentwert.
    Bei einem negativen Wert fährt das Fahrzeug rückwärts.
    Der Übergabewert muss zwischen -100 und 100 liegen!
    """
    if speed < 0:
        return backward(0-speed)
    elif speed == 0:
        return roll()
    else:
        return forward(speed)
        
drive = setSpeed
        
def getSpeed():
    """
    Gibt die aktuell gesetzte Geschwindigkeit als Prozentwert zwischen -100 und 100 zurück.
    Ein negativer Wert bedeutet, dass sich das Fahrzeug rückwärts bewegt.
    """
    if v.read(IN1)==0 and v.read(IN2)==1:
        return v.get_PWM_dutycycle(EN)
    elif v.read(IN1)==1 and v.read(IN2)==0:
        return (0-v.get_PWM_dutycycle(EN))
    else:
        return 0
    

getDC = getSpeed

def close():
    """
    Gibt verwendete Ressourcen frei. Beim Beenden des Skripts ausführen!
    """
    roll()
    return v.stop()


## Initialisierungen:

v = pigpio.pi()          # pigpiod muss im Hintergrund laufen!
v.set_mode(EN, pigpio.OUTPUT)
v.set_mode(IN1, pigpio.OUTPUT)
v.set_mode(IN2, pigpio.OUTPUT)

# PWM Einstellungen für en übernehmen:
v.set_PWM_frequency(EN, PWM_FREQ)
v.set_PWM_range(EN, PWM_RANGE)

pigpio.exceptions = False
# Erlaubt es, Fehler von pigpiod anhand des Rückgabewerts zu behandeln
# (wenn kein Fehler auftritt ist der Rückgabewert 0.
# Falls z.B. ein Übergabe-Parameter außerhalb des erlaubten Bereichs ist -8)
