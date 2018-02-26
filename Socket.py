#!/usr/bin/env python3

## Version 0.3 (XML alpha)

## Changelog:
#
# --- 0.3 ---
# - XML testweise integriert (nur empfangen und nur Befehle subscribe und drive)
# - Debugging Modus von Asyncio aktiviert (bei Parameter "-d")
#
# --- 0.2.7
# - Fehler beim subscriben mit Zeitangabe behoben
#
# --- 0.2.6 ---
# - Exception-Handling beim subscriben etwas verbessert
#
# --- 0.2.5 ---
# - asyncio.ensure_future statt loop.create_task
# 
# --- 0.2 ---
# - Sensorik und Steuerung in eigene Module ausgelagert
# - Sensoen als Klassen implementiert
# - Im Debugging-Modus starten bei Aufruf mit dem Parameter "-d"

## TODO:
# - Nachrichten im XML-Format schicken
# - restliche Befehle implementieren
# - Warum funktionieren manchmal keine KeyboardInterrupts?
# - Kommentierung und Exception-Handling verbessern
# - Uebersichtlichkeit verbessern
# - Ueberlegen, was passieren soll, falls ein Paket aufgeteilt wird


import asyncio
import sys
import xml.etree.ElementTree as ET

import Sensorik
import Steuerung

IP = "127.0.0.1"
PORT = 8889

DEBUG = True if "-d" in sys.argv else False

WELCOME_MSG = """
               Welcome to the TCP Socket of the
       
        _______  _______  _______  _______ _________
       (  ____ \(       )(  ___  )(  ____ )\__   __/
       | (    \/| () () || (   ) || (    )|   ) (   
       | (_____ | || || || (___) || (____)|   | |   
       (_____  )| |(_)| ||  ___  ||     __)   | |   
             ) || |   | || (   ) || (\ (      | |   
       /\____) || )   ( || )   ( || ) \ \__   | |   
       \_______)|/     \||/     \||/   \__/   )_(   
                                             
 _______  _______             _______  _______  _______ 
(  ____ )(  ____ \           (  ____ \(  ___  )(  ____ )
| (    )|| (    \/           | (    \/| (   ) || (    )|
| (____)|| |         _____   | |      | (___) || (____)|
|     __)| |        (_____)  | |      |  ___  ||     __)
| (\ (   | |                 | |      | (   ) || (\ (   
| ) \ \__| (____/\           | (____/\| )   ( || ) \ \__
|/   \__/(_______/           (_______/|/     \||/   \__/


"""

class ServerProtocol(asyncio.Protocol):
    """
    Implementierung eines eigenen Netzwerkprotokol, indem die Methoden der Basisklasse
    "asyncio.Protocol" ueberschrieben werden.
    weitere Infos: https://docs.python.org/3/library/asyncio-protocol.html?highlight=protocol#protocols
    """
    def __init__(self):
        self.subscribedSensors = {}

    def connection_made(self, transport):
        self.peername = transport.get_extra_info('peername')
        print("Connection from {}".format(self.peername))
        self.transport = transport
        self.transport.write(WELCOME_MSG.encode())

        # Subscribe Alerts from all Sensors:
        for Sen in Sensorik.Sensoren:
            Sensorik.Sensoren[Sen].SubscribeAlerts(self.SendAlert)

    def connection_lost(self, exc):
        print("Client {} closed the connection".format(self.peername))
        for sensor in list(self.subscribedSensors):
            print("cancel publishing value of sensor {} to {}".format(sensor,self.peername))
            self.subscribedSensors[sensor].desubscribe()
            del self.subscribedSensors[sensor]
        print("desubscribing Alerts from all Sensors...")
        for Sen in Sensorik.Sensoren:
            Sensorik.Sensoren[Sen].DesubscribeAlerts(self.SendAlert)

    def data_received(self, receivedData):
        print("Data received from Host {}: {!r}\nTrying to decode and parse...".format(self.peername, receivedData))

        readPos = 0
        while readPos < len(receivedData):
            
            received = receivedData[readPos : ]
            
            #gehe die empfangenen bytes solange durch bis "//SRCCP//" gefunden wird
            if received.startswith(b'//SRCCP//'):
                
                try:
                    headerEnd = received.find(b'\n---START---\n')
                    messageBegin = headerEnd + 13 # len(b'\n---START---\n')

                    header = received[0 : headerEnd].decode()
                                
                    lengthPos = header.find('length:')
                    length = int(header[lengthPos + len('length:') : header.find('\n', lengthPos)])
                    
                    messageEnd = messageBegin + length
                    
                    if not received[messageEnd : messageEnd + 11] == b'\n---END---\n':
                        readPos += 1
                        raise ValueError("invalid length or incomplete data received! Ignoring packet...")
                        
                    else:
                        message = received[messageBegin : messageEnd].decode()                    
                        readPos += messageEnd + 11
                        
                        print("----------------------")
                        print("Received SRCCP-Packet:")
                        print("header =\n", header)
                        print("---")
                        print("parsed length = ", length)
                        print("---")
                        print("message =\n", message)
                        print("---")
                        print("parsing XML...")
                        
                        root = ET.fromstring(message)
                        
                        if root.tag == "command":
                            print("command received:")
                            command = root.find("name").text
                            print(command)
                            
                            if command == "drive":
                                speed = root.find("speed").text
                                if DEBUG:
                                    print("Set speed to ", speed)
                                Steuerung.drive(int(speed))
                                
                            if command == "subscribe":
                                if root.find("type").text == "data":
                                    for Sen in root.findall("sensor"):
                                        self.subscribeSensor(Sen.text, Sen.get("interval"))
                                
                        elif root.tag == "message":
                            print("message received, nothing to do here...")
                            
                        elif root.tag == "ctlmsg":
                            print("controlmessage received")
                            # TODO
                            
                        else:
                            raise ValueError("unknown message")
                            
                        print("----------------------")
                        
                except ValueError as e:
                    print("ValueError:" + e.args[0])
                    self.transport.write("err({})\n".format(e.args[0]).encode())
                except KeyError as e:
                    print("KeyError:" + e.args[0])
                    self.transport.write("err({})\n".format(e.args[0]).encode())
                else:
                    self.transport.write("ack({})\n".format(command).encode())
            else:
                #print('unknown protocol!\n') # kann sehr Ressourcen-fressend werden, falls viele unbekannte Daten empfangen werden!
                readPos += 1

    def SendMsg(self, Type, Message, Unit):
        if DEBUG: print( "Sending Message of Type {} to Host {}: {}".format(Type, self.peername, Message))
        self.transport.write((str(Type) + "(" + str(Message) + " " + str(Unit) +")\n").encode())

    def SendAlert(self, Sensor, Message):
        if DEBUG: print( "Sending Alert of Sensor {} to Host {}: {}".format(Sensor, self.peername, Message))
        self.transport.write(("ALERT:" + str(Sensor) + "(" + str(Message) + ")\n").encode())
        
    def subscribeSensor(self, sensor, refreshtime = None):
        try:
            # if already subscribed desubscribe:
            if sensor in self.subscribedSensors:
                self.subscribedSensors[sensor].desubscribe()
            else:
                self.subscribedSensors[sensor] = Sensorik.Sensoren[sensor]()

            # Subscribe:
            if refreshtime:
                self.subscribedSensors[sensor].subscribe(self.SendMsg, True, refreshtime)
            else:
                self.subscribedSensors[sensor].subscribe(self.SendMsg)

        except KeyError:
            print("ERROR: Unknown sensor '{}'".format(sensor))
            self.transport.write("err(sub '{}', unknown sensor!)\n".format(sensor).encode())
        except ValueError as e:
            print("ValueError:" + e.args[0])
            self.transport.write("err(sub {}: {})\n".format(sensor, e.args[0]).encode())
        else:
            self.transport.write("ack(sub '{}')\n".format(sensor).encode())


loop = asyncio.get_event_loop()
# Each client connection will create a new protocol instance
coro = loop.create_server(ServerProtocol, IP, PORT)
server = loop.run_until_complete(coro)

Sensorik.init(loop)

# DEBUGGING:
async def printCurrentTasks(repeat = False):
    Tasks = asyncio.Task.all_tasks()
    print(Tasks)
    while repeat:
        newTasks = asyncio.Task.all_tasks()
        if Tasks != newTasks:
            Tasks = newTasks
            print(Tasks)
        await asyncio.sleep(repeat)
    return asyncio.Task.all_tasks()

if DEBUG:
    loop.create_task(printCurrentTasks(1))
    # Enable Debugging mode of asyncio:
    loop.set_debug(True)
    import logging
    logging.basicConfig(level=logging.DEBUG)

# Serve requests until Ctrl+C is pressed
print('Serving on {}'.format(server.sockets[0].getsockname()))

try:
    loop.run_forever()
except KeyboardInterrupt:
    print("Interrupted by user.")
finally:
    print("Cleaning up...")
    # Close the server:
    server.close()
    loop.run_until_complete(server.wait_closed())
    print("canceling all asyncio tasks...")
    for task in asyncio.Task.all_tasks():
        print("cancelling task {}".format(task))
        task.cancel()
    # Stop autorefreshing the sensors:
    Sensorik.close()
    Steuerung.close()
    loop.close()
