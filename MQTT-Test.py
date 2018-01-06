#!/usr/bin/env python3

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
    print(msg.topic + " " + str(int(msg.payload)))
    if msg.topic == "steer":
        Lnk.setPos(int(msg.payload))
    if msg.topic == "motor":
        Mtr.setSpeed(int(msg.payload))
    

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect("localhost", 1883, 60)

client.loop_forever()