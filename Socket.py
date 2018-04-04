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
# - Error-Messages (NACK) spezifiezeieren uns festlegen, was bei einem NACK unternommen wird
# - Warum funktionieren manchmal keine KeyboardInterrupts?
# - Kommentierung und Exception-Handling verbessern
# - Uebersichtlichkeit verbessern
# - Ueberlegen, was passieren soll, falls ein Paket aufgeteilt wird


import asyncio
import sys
import xml.etree.ElementTree as ET

import Sensorik_fake as Sensorik
import Steuerung_fake as Steuerung

IP = ""
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
        #self.transport.write(WELCOME_MSG.encode())

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
            
            #gehe die empfangenen bytes solange durch bis "//SRCCP//" gefunden wird
            if receivedData[readPos+2 : readPos+9] == b'/SRCCP/':
                
                try:
                    length = int.from_bytes(receivedData[readPos : readPos+2], "big")
        
                    frame = receivedData[readPos : readPos+length+2]
                    
                    if not frame.endswith(b'#/'):
                        print("ERROR: Wrong length or incomplete data received!")
                        self.SendNACK("incomplete packet received")
                        # suche weiter nach einem Paket...
                        readPos += 1
                        continue
                    
                    
                    readPos += (length + 2) 
                    
                    
                    headerEnd = frame.find(b'/#', 7)

                    header = frame[ : headerEnd]       
                    
                    message = frame[headerEnd+2 : -2].decode()
                    
                    if DEBUG:    
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
                        
                    if root.tag == "cmd":
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
                                
                    elif root.tag == "msg":
                        print("message received, nothing to do here...")
                            
                    elif root.tag == "ctlmsg":
                        print("controlmessage received")
                        # TODO: z.B. bei NACK Fehlermeldung auswerten und Nachricht evtl wiederholen?!
                            
                    else:
                        raise ValueError("unknown message")
                            
                    print("----------------------")
                        
                except ValueError as e:
                    print("ValueError:" + e.args[0])
                    #self.transport.write("err({})\n".format(e.args[0]).encode())
                    self.SendNACK(e.args[0])
                except KeyError as e:
                    print("KeyError:" + e.args[0])
                    #self.transport.write("err({})\n".format(e.args[0]).encode())
                    self.SendNACK(e.args[0])
                else:
                    self.SendACK(root.tag)
            else:
                #print('unknown protocol!\n') # kann sehr Ressourcen-fressend werden, falls viele unbekannte Daten empfangen werden!
                readPos += 1

    def SendMsg(self, Sensor, Message, Unit):
        if DEBUG: print( "Sending Message of Sensor {} to Host {}: {}".format(Sensor, self.peername, Message))
        #self.transport.write((str(Type) + "(" + str(Message) + " " + str(Unit) +")\n").encode())
        root = ET.Element('msg')
        name = ET.SubElement(root, 'name')
        name.text = "sensordata"
        sensor = ET.SubElement(root, 'sensor')
        sensor.text = Sensor
        data = ET.SubElement(root, 'data')
        data.text = Message
        unit = ET.SubElement(root, 'unit')
        unit.text = Unit
        xml = ET.tostring(root)
        if DEBUG:
            print("sending xml:\n", xml)
        self.SendSRCCPPacket(xml)
        
        

    def SendAlert(self, Sensor, Message):
        #TODO:
        if DEBUG: print( "Sending Alert of Sensor {} to Host {}: {}".format(Sensor, self.peername, Message))
        print("Not implemented yet!")
        #self.transport.write(("ALERT:" + str(Sensor) + "(" + str(Message) + ")\n").encode())
        
    def SendACK(self, command):
        root = ET.Element('ctlmsg')
        name = ET.SubElement(root, 'name')
        name.text = "ack"
        type = ET.SubElement(root, 'type')
        type.text = command
        xml = ET.tostring(root)
        if DEBUG:
            print("sending xml:\n", xml)
        self.SendSRCCPPacket(xml)

    
    def SendNACK(self, command, errormsg = None):
        root = ET.Element('ctlmsg')
        name = ET.SubElement(root, 'name')
        name.text = "nack"
        type = ET.SubElement(root, 'type')
        type.text = command
        if errormsg:
            errormsg = ET.SubElement(root, 'message')
            errormsg.text = errormsg
        xml = ET.tostring(root)
        if DEBUG:
            print("sending xml:\n", xml)
        self.SendSRCCPPacket(xml)
        
    
    def SendSRCCPPacket(self, XML):
        frame = b'/SRCCP/v0.1/#' + XML + b'#/'
        length = len(frame).to_bytes(2, "big")
        Packet = length + frame
        if DEBUG: print("Sending SRCCP-Packet:", Packet)
        self.transport.write(Packet)
        
        
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
        
        # TODO:
        except KeyError:
            print("ERROR: Unknown sensor '{}'".format(sensor))
            self.SendNACK("subscribe", "unknown sensor ".format(sensor))
        except ValueError as e:
            print("ValueError:" + e.args[0])
            self.SendNACK("subscribe", e.args[0])
            #self.transport.write("err(sub {}: {})\n".format(sensor, e.args[0]).encode())
        #else:
            #self.transport.write("ack(sub '{}')\n".format(sensor).encode())


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
    loop.create_task(printCurrentTasks(10))
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
