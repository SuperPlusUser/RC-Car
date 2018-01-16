#!/usr/bin/env python3

## Quellen:
# - https://www.dinotools.de/2015/04/12/mqtt-mit-python-nutzen/

import sys
sys.path.append('Python_Modules')       # Falls die Python-Module in einem eigenen Unterordner sind.
import Lenkung as Lnk
import Motorsteuerung as Mtr
import paho.mqtt.client as mqtt         # Infos unter https://pypi.python.org/pypi/paho-mqtt/1.3.1

# Lenkung anfangs auf Mittelposition und Geschwindigkeit auf 0 setzen:
Mtr.setSpeed(0)
Lnk.setPos(50)

# Meldung ausgeben, wenn Verbindung zum MQTT-Broker hergestellt wurde:
def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    # Topics mit QoS 0 abbonieren:
    client.subscribe([("steer",0), ("motor",0)])

# Diese Funktion wird aufgerufen, wenn in einem abonnierten Topic etwas empfangen wird:
def on_message(client, userdata, msg):
    print(msg.topic + " " + str(msg.payload))
    if msg.topic == "steer":
        Lnk.setPos(100-int(msg.payload))    # Lenkung auf empfangenen Zahlenwert im Topic "steer" setzen
    if msg.topic == "motor":
        if msg.payload == b'stop':          # Bremsen, wenn "stop" im Topic "motor" empfangen wird
            Mtr.brake()
        elif int(msg.payload) in range(-100,101):
            Mtr.setSpeed(int(msg.payload))  # Motorgeschwindigkeit auf empfangene Zahl im Topic "motor" setzen
    
# Initialisierungen:
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

# username_pw_set(username, password=None)  # Hiermit kann optional ein Passwort und Benutzername gesetzt werden

# Verbindung zum MQTT-Broker auf "localhost", Port 1883, mit 60 Sek. "keepalive"-Zeit herstellen:
client.connect("localhost", 1883, 60)

try:
    client.loop_forever()
except KeyboardInterrupt:
    print("Execution interrupted by user. Cleaning up...")
finally:
    client.disconnect()
    Lnk.close()
    Mtr.close()
