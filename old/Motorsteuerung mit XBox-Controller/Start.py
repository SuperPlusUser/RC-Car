#!/usr/bin/env python3

# -------------  Ferngesteuertes Auto mit XBox Controller ---------------------

import time
import RPi.GPIO as GPIO # Verwendung: https://sourceforge.net/p/raspberry-gpio-python/wiki/PWM/
import xbox             # Installation siehe https://github.com/FRC4564/Xbox
import subprocess       # Ermöglicht das aufrufen von Subprozessen wie Shell-Skripten
import os.path

## Parameter:

f = 25
dir = os.path.dirname(os.path.abspath(__file__))

## Portdefinition:

GPIO.setmode(GPIO.BCM)  # Bezeichnungsweise der GPIO Port. BCM: z.B. GPIO 21 etc. (nicht PIN/PORT)

ENA = 17                # Hauptmotor
ENB = 18                # Lenkung

In1 = 27                # Motor Forwaerts: 0
In2 = 22                # Motor Forwaerts: 1
In3 = 23                # Lenkung Links: 1
In4 = 24                # Lenkung Links: 0

GPIO.setup(ENA, GPIO.OUT)
GPIO.setup(ENB, GPIO.OUT)
GPIO.setup(In1, GPIO.OUT)
GPIO.setup(In2, GPIO.OUT)
GPIO.setup(In3, GPIO.OUT)
GPIO.setup(In4, GPIO.OUT)


## Initialisierungen:

# PWM:
v = GPIO.PWM(ENA, f)      # Motorgeschwindigkeitssteuerung mit PWM und der Frequenz f
v.start(0)                # Mit Geschwindigkeit 0% (--> DC 0) starten


# Joystick:
joy = 0                 # Startwert, damit das exception-Handling unten funktioniert

try:
        joy = xbox.Joystick()

except IOError:
        print("Could not connect to xbox wireless dongle. Trying again...")
        while not (joy):
                # Starte ein Skript, welches "xboxdrv" neu startet (Hilft bei Verbindungsproblemen):
                subprocess.run(dir+"/detach_xboxdrv.sh")
                try:
                        joy = xbox.Joystick()
                except IOError:
                        print("Connection failed! Trying again...")


## Funktionsdefinitionen:

# Hauptmotor:

def forward(x):
        GPIO.output(In1, 0)
        GPIO.output(In2, 1)
        v.ChangeDutyCycle(x)

def backward(x):
        GPIO.output(In1, 1)
        GPIO.output(In2, 0)
        v.ChangeDutyCycle(x)

def roll():
        v.ChangeDutyCycle(0)

def brake():
        GPIO.output(In1, 1)
        GPIO.output(In2, 1)
        v.ChangeDutyCycle(100)


# Lenkung

def straight():
        GPIO.output(ENB, 0)

def right():
        GPIO.output(In3, 0)
        GPIO.output(In4, 1)
        GPIO.output(ENB, 1)

def left():
        GPIO.output(In3, 1)
        GPIO.output(In4, 0)
        GPIO.output(ENB, 1)

try:
        ## Verbindungsaufbau XBox Controller:

        print ("Please connect the XBox Controller and press any Button.")
        while not joy.connected():
                time.sleep(0.5)

        print ("Controller successfully connected")


    ## Endlosschleife:

        while True:
                if joy.connected():

                # Motorsteuerung:

                        # Vorwaertsfahren mit rechtem Trigger (hat immer Vorrang!)
                        if joy.rightTrigger()>0.05:
                                forward(joy.rightTrigger()*100)

                        # Rueckwaertsfahren mit linkem Trigger
                        elif joy.leftTrigger()>0.05:
                                backward(joy.leftTrigger()*100)

                        # Bremsen mit B (evtl. keine gute Idee, da hoher Strom!)
                        elif joy.B():
                                brake()

                        else:
                                roll()

                # Lenkung:

                        # Lenken mit rechtem Analogstick
                        if joy.leftX()<-0.5:
                                left()

                        elif joy.leftX()>0.5:
                                right()

                        else:
                                straight()

                # Programm beenden mit Start und Back:

                        if joy.Back() and joy.Start():
                                raise KeyboardInterrupt


                else:
                        print(" Connection to controller lost. trying to reconnect...")

                        while not joy.connected():
                                time.sleep(1)

                        print ("Controller successfully reconnected")

                time.sleep(0.05)        # Waretezeit in Sekunden einfuegen um zu hohe Prozessorauslastung zu vermeiden

except KeyboardInterrupt:
        print("Skript inerrupted by User. Cleaning up and shutting down Pi...")
        v.stop()
        GPIO.cleanup()
        joy.close()
        subprocess.call("sudo shutdown --poweroff", shell=True)
