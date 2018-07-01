#!/usr/bin/env python3

## Version 0.4
    
## Changelog:
#
# --- Version 0.4 ---
# - Steuerung mit XBox-Controller (wieder) eingebaut (benoetigt "xbox_modified").
# - Fehlerkorrekturen beim setzen des Speedlimits.
#
# --- Version 0.3 ---
# - Moeglichkeit eingebaut IR-Beleuchtung der Kamera an und aus zu schalten.
# - Kommentierung erweitert.
# - Moeglichkeit eingebaut speedlimits nur fuer eine Richtung zu setzen
#   (Benoetigt fuer Bremsassistent, sodass man immernoch rueckwaerts vom Objekt wegfahren kann)
#
# --- Version 0.2 ---
# - Tests durchgefuehrt
# - Fehler bei Berechnung der minimalen und maximalen PW behoben
#
# --- Version 0.1 ---
# - 1. Version aus Lenkungs- und Motorsteuerungsmodul zusammengesetzt

import time
import sys
import os               # wird verwendet, um pigpiod automatisch zu starten
import subprocess
import threading
import xbox_modified as xbox
import pigpio
# Verwendung: http://abyz.me.uk/rpi/pigpio/python.html#set_servo_pulsewidth
# Beachten: bevor mittels l = pigpio.pi() eine Instanz der pigpio.pi Klasse
# erstellt werden kann, muss der Daemon "pigpiod" mittels "sudo pigpiod" gestartet werden!

EN_LIGHT = True
if EN_LIGHT:
    import light



# ---------------------------
## --- Globale Konstanten ---
# ---------------------------

DEBUG = True if "-d" in sys.argv else False

# --- Enable / Disable XBox-Controller ---
# Das Skript muss mit Root-Rechten ausgeführt werden, 
# falls eine Steuerung mit XBox-Controller ermoeglicht werden soll!
EN_XBOX_CONTROLLER = True


# --- Lenkung ---
# Eigenschaften der Servo:
SIG_PIN = 18  # GPIO-Pin der Servo
_MIN_PW = 750    # minimale Impulsdauer in us (Falsche Werte koennen zu Beschaedigungen fuehren!)
_MAX_PW = 2250   # max Impulsdauer in us (Falsche Werte koennen zu Beschaedigungen fuehren!)

# Einschraenkung des Bewegungsradiuses (in Prozent):
# Die Werte ergeben sich durch den eingeschraenkten Lenkradius der Lenkmechanik.
# Falsche Werte koennen zu Beschaedigungen fuehren!
_RL = 0 # rechtes Limit in Prozent !MUSS kleiner als _LL sein
_LL = 33 # linkes Limit in Prozent !MUSS groeßer als _RL sein

# --- Motor ---
PWM_FREQ = 50               # PWM-Frequenz
PWM_RANGE = 100             # Dutycycle-Range
# (siehe http://abyz.me.uk/rpi/pigpio/python.html#set_PWM_range)

# Portdefinition:
EN = 17                 # Hauptmotor
IN1 = 27                # Motor Forwaerts: 0
IN2 = 22                # Motor Forwaerts: 1


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
    """
    global _Pos  # Position als global definiert--> bleibt nach Funktionsaufruf erhalten
    newPos+=0.5 # Damit newPos richtig gerundet wird
    if int(newPos) in range(101):
        _Pos = int(newPos)
        if DEBUG: print("Steering to Position {} ...".format(_Pos))
        return l.set_servo_pulsewidth(SIG_PIN, _percent_to_pw(_Pos))
    else:
        raise ValueError("Position must be between 0 (right limit) and 100 (left limit)!")

def set_current_pos():
    """
    Setzt Servo auf zuletzt festgelegte Position.
    """
    return steer(_Pos)

def disable_steering():
    """
    Deaktiviert die Servo
    """
    if DEBUG: print("Disabling Servo...")
    return l.set_servo_pulsewidth(SIG_PIN, 0)

def get_pos():
    """
    Gibt die zuletzt festgelegte Position des Servos (zwischen 0 und 100) zurueck.
    """
    return _Pos

def get_pw():
    """
    Gibt die Pulsweite am Signal-Pin des Servos zurueck.
    """
    return l.get_servo_pulsewidth(SIG_PIN)


# -----------------------
## --- Motorsteuerung ---
# -----------------------

def drive(speed):
    """
    Setzt die Geschwindigkeit auf den uebergebenen Prozentwert.
    Bei einem negativen Wert faehrt das Fahrzeug rueckwaerts.
    Der uebergabewert muss zwischen -100 und 100 liegen!
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
    # Richtung festlegen:
    v.write(IN1, 0)
    v.write(IN2, 1)
    if DEBUG:
        print("Driving forward with speed {} ...".format(int(speed * _Limit_F)))
    if EN_LIGHT:
        light.brake_light(0)
        light.reverse_light(0)
    # Geschwindigkeit ueber PWM festlegen:
    return v.set_PWM_dutycycle(EN,int(speed * _Limit_F))   

def backward(speed):
    if _BlockMtr:
        print("Motor blocked!")
        return -1
    if speed < 0 or speed > PWM_RANGE:
        raise ValueError("Speed out of range")
    # Richtung festlegen
    v.write(IN1, 1)
    v.write(IN2, 0)
    if DEBUG:
        print("Driving backward with speed {} ...".format(int(speed * _Limit_B)))
    if EN_LIGHT:
        light.brake_light(0)
        light.reverse_light(1)
    # Geschwindigkeit ueber PWM festlegen:
    return v.set_PWM_dutycycle(EN,int(speed * _Limit_B))


def roll():
    if DEBUG: print("let vehicle roll free")
    if EN_LIGHT:
        light.brake_light(0)
        light.reverse_light(0)
    return v.set_PWM_dutycycle(EN,0)

def brake():
    """
    Bremst das Fahrzeug aus, indem der Motor kurzgeschlossen wird.
    """
    v.write(IN1, 1)
    v.write(IN2, 1)
    if DEBUG: print("Braking vehicle")
    if EN_LIGHT:
        light.brake_light(1)
        light.reverse_light(0)
    return v.set_PWM_dutycycle(EN,PWM_RANGE)

def get_speed():
    """
    Gibt die aktuell gesetzte Geschwindigkeit als Prozentwert zwischen -100 und 100 zurueck.
    Ein negativer Wert bedeutet, dass sich das Fahrzeug rueckwaerts bewegt.
    """
    if v.read(IN1)==0 and v.read(IN2)==1:
        return v.get_PWM_dutycycle(EN)
    elif v.read(IN1)==1 and v.read(IN2)==0:
        return 0 - v.get_PWM_dutycycle(EN)
    else:
        return 0

def set_speed_limit(l, dir = "all"):
    """
    Ermoeglicht das Limitieren der Motorgeschwindigkeit.
    Das uebergebene Limit dient als Faktor fuer die Geschwindigkeit
    und muss zwischen 0 (Motor deaktiviert) und 100 (volle Geschwindigkeit) liegen.
    mit dir = "forward"/"backward" kann festgelegt werden, dass das Limit nur beim
    vorwaerts/rueckwaerts fahren angewendet wird.
    """
    global _Limit_F, _Limit_B
    if l < 0 or l > 100:
        raise ValueError("Limit must be between 0 and 100")
    if dir == "all":
        _Limit_F = _Limit_B = l/100
    elif dir == "forward":
        _Limit_F = l/100
    elif dir == "backward":
        _Limit_B = l/100
    if DEBUG: print("Speedlimit set to {} Percent for direction {}".format(l, dir))
    

def block_mtr():
    """
    Blockiert den Motor und verhindert, dass neue Fahranweisungen ausgefuehrt werden.
    """
    global _BlockMtr
    roll()
    if DEBUG: print("Motor blocked. To be able to drive again, launch 'enable_mtr()'")
    _BlockMtr = True

def deblock_mtr():
    """
    Loest die Blockade des Motors wieder, wenn diese zuvor durch die Funktion "block_mtr" aktiviert wurde.
    """
    global _BlockMtr
    if DEBUG: print("Motor deblocked")
    _BlockMtr = False

    
# --------------
# --- IR-LED ---
# --------------

def enable_ir():
    """
    Aktiviert die IR-LEDs, die an der Kamera angebracht sind, um eine Nachtsichtfunktion zu ermoeglichen
    """
    return light.change_mode(mode = 10)

def disable_ir():
    """
    Deaktiviert die IR-LEDs am Kamera-Modul, um Energie zu sparen.
    """
    return light.change_mode(mode = 0)

# --------------
## --- close ---
# --------------

def close():
    """
    Gibt verwendete Ressourcen frei. Beim Beenden des Skripts ausfuehren!
    """
    global EN_XBOX_CONTROLLER
    roll()
    v.stop()
    disable_steering()
    l.stop()
    if EN_LIGHT:
        light.Pixels.clear()
        light.Pixels.show()
    EN_XBOX_CONTROLLER = False


# --------------
## --- Tests ---
# --------------

def test():
    """
    Ermoeglicht einen einfachen Test aller Fahrfunktionen.
    Wird ausgefuehrt, falls das Modul direkt als Skript aufgerufen wird.
    """
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

    steer(0)
    time.sleep(1)
    steer(100)
    time.sleep(1)
    steer(50)
    time.sleep(1)

    print("all tests complete")
    return "finished"


# ----------------------------------------------
## --- control vehicle with XBox-controller ---
# ----------------------------------------------

def control_with_joystick():
    joy = None
    
    print("Trying to connect to xbox controller... Press any button!")
    try:
        while not joy and EN_XBOX_CONTROLLER:
            try:
                joy = xbox.Joystick()
                print("Connection to xbox controller established successfully")
            except IOError as e:
                if DEBUG:
                    print("Could not connect to xbox controller.\nError: {}\nTrying again...".format(e))

        while EN_XBOX_CONTROLLER:
            joy.refresh()
            # blockiert solange, bis eine Taste gedrückt wird bzw. der Controller erneut aktualisiert wird
            
            if joy.connected():
                # Motorsteuerung:
                if joy.B():
                    brake() # Bremsen mit B
                else:
                    drive((joy.rightTrigger()-joy.leftTrigger())*100)

                # Lenkung:
                steer((-1+joy.leftX())*-50)
                
                #Licht an/aus
                if EN_LIGHT and joy.dpadUp():
                    light.front_light(on = "toggle")
                    
                #change Light Mode
                if EN_LIGHT and joy.dpadDown():
                    light.change_mode(mode = "toggle")
                
                # Raspberry Pi herunterfahren mit Start und Back:
                if joy.Back() and joy.Start():
                    print("calling shutdown.sh and shutdown pi...")
                    subprocess.call("/home/pi/RC-Car/shutdown.sh", shell = True)
                    
            else:
                roll()
                print("Connection to controller lost. Trying to reconnect...")
                while not joy.connected() and EN_XBOX_CONTROLLER:
                    time.sleep(1)
                    joy.refresh()
                if joy.connected():
                    print("Controller successfully reconnected")
    except Exception as e:
        print("Joystick Thread exited with Exception: ", e)
        
    finally:
        if joy:
            joy.close()
            print("connection to xbox controller closed")
    
# --------------------------
## --- Initialisierungen ---
# --------------------------

executor = None

# --- Initialisiere Lenkung ---

# Pruefung auf gueltige Eingaben:
if (_RL not in range(101) or _LL not in range(101) or _LL < _RL):
    raise ValueError ("rl must be higher than ll and both must be Integers between 0 and 100!")

# Berechnung der minimalen und maximalen Pulsweite innerhalb des angegebenen Bewegungsradiuses:

_k = (_MAX_PW - _MIN_PW)/100

_MAX_PW = _LL * _k + _MIN_PW
_MIN_PW = _RL * _k + _MIN_PW

_k = (_MAX_PW - _MIN_PW)/100

# Anfangsposition = Mittelstellung
_Pos = 50


print("trying to connect to pigpio daemon")
# mit pigpio-Daemon verbinden und ein Objekt der Klasse pigpio.pi erstellen:
l = pigpio.pi()
i=0
# Versuchen pigpiod zu starten, falls notwendig:
while not l.connected and i<5:
    os.system("sudo pigpiod")
    time.sleep(5)     # pigpiod needs some time to startup...
    l = pigpio.pi()
    i+=1
if l.connected:
    print("Successfully connected to pigpio daemon")
else:
    raise OSError("Could not connect to pigpiod after {} tries\n".format(i+1))
        
# --- Initialisiere Motor ---

v = pigpio.pi()          # pigpiod muss im Hintergrund laufen!
v.set_mode(EN, pigpio.OUTPUT)
v.set_mode(IN1, pigpio.OUTPUT)
v.set_mode(IN2, pigpio.OUTPUT)

# PWM Einstellungen fuer en uebernehmen:
v.set_PWM_frequency(EN, PWM_FREQ)
v.set_PWM_range(EN, PWM_RANGE)

# Sonstige Initialisierungen:
deblock_mtr()
set_speed_limit(100)


# -------------
## --- Main ---
# -------------

if __name__ == "__main__":
    try:
        if EN_XBOX_CONTROLLER:
            control_with_joystick()
        else:
            DEBUG = True
            test()
    finally:
        close()
else:
    # Steuerung mit xbox controller in eigenem Thread:
    if EN_XBOX_CONTROLLER:
        controller_thread = threading.Thread(target=control_with_joystick)
        controller_thread.start()
