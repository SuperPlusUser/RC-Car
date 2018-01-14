#!/usr/bin/env python3

## Quellen:
# - https://www.dinotools.de/2015/04/12/mqtt-mit-python-nutzen/

import sys
sys.path.append('Python_Modules')
import Lenkung as Lnk
import Motorsteuerung as Mtr

Mtr.setSpeed(0)
Lnk.setPos(50)

import paho.mqtt.client as mqtt

def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))

    client.subscribe([("steer",0), ("motor",0)])

def on_message(client, userdata, msg):
    print(msg.topic + " " + str(msg.payload))
    if msg.topic == "steer":
        Lnk.setPos(100-int(msg.payload))
    if msg.topic == "motor":
        if msg.payload == b'stop':
            Mtr.brake()
        elif int(msg.payload) in range(-100,101):
            Mtr.setSpeed(int(msg.payload))
    

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect("localhost", 1883, 60)

try:
    client.loop_forever()
finally:
    client.disconnect()
    Lnk.close()
    Mtr.close()