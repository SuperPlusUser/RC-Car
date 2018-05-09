#!/usr/bin/env python3

## Version 0.5.1

## Changelog:
#
# --- 0.5.1 ---
# - unnoetige Programmteile entfernt
# - Problem im Sensorik-Modul behoben, das teilweise dazu fuehrte, dass keine Sensorwerte verschickt wurden.
#
# --- 0.5 ---
# - erste Tests durchgefuehrt
# - Signal-Handler fuer SIGTERM eingebaut --> Programm kann mit "pkill -f Socket.py" sauber beendet werden
# - Option "-a" fuer Autostart eingebaut, bei der 10 Sek. gewartet wird, bevor der Server gestartet wird

# --- 0.4.1 ---
# - Restliche Befehle implementiert
# - weitere Kommentare eingefuegt

# --- 0.4 ---
# - Umstellung auf neue Protokoll-Definition (neuer Header etc.)
# - Senden von Nachrichten im XML-Format eingebaut
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
# - Error-Messages (NACK) spezifiezeieren uns festlegen, was bei einem NACK unternommen wird
# - Alert-Severity einbauen!
# - Ueberlegen, was passieren soll, falls ein Paket aufgeteilt wird?!


import asyncio
import sys
import xml.etree.ElementTree as ET
import signal

import Steuerung_fake as Steuerung
import Sensorik_fake as Sensorik

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

class SRCCP(asyncio.Protocol):
    """
    Implementierung des eigenen Netzwerkprotokolls "Smart RC Car Protocol", in dem die Methoden der Basisklasse
    "asyncio.Protocol" ueberschrieben und erweitert werden.
    weitere Infos: https://docs.python.org/3/library/asyncio-protocol.html?highlight=protocol#protocols
    """
    
    def __init__(self):
        """Konstruktor"""
        self.subscribedSensors = {}

    def connection_made(self, transport):
        """wird bei jedem neuen Verbindungsaufbau aufgerufen."""
        self.peername = transport.get_extra_info('peername')
        print("Connection from {}".format(self.peername))
        self.transport = transport
        self.SendMsg("system", WELCOME_MSG)
        #TODO: Standardmaessig alle Alerts subscriben?!
        # Subscribe Alerts from all Sensors:
        for Sen in Sensorik.Sensoren:
            Sensorik.Sensoren[Sen].SubscribeAlerts(self.SendAlert)

    def connection_lost(self, exc):
        """Wird beim (erwarteten oder unerwarteten) Verbindungsabbruch ausgefuehrt."""
        print("Client {} closed the connection".format(self.peername))
        for sensor in list(self.subscribedSensors):
            print("cancel publishing value of sensor {} to {}".format(sensor,self.peername))
            self.subscribedSensors[sensor].desubscribe()
            del self.subscribedSensors[sensor]
        print("desubscribing Alerts from all Sensors...")
        for Sen in Sensorik.Sensoren:
            Sensorik.Sensoren[Sen].DesubscribeAlerts(self.SendAlert)
        print("Stopping Vehicle...")
        Steuerung.brake()
        Steuerung.disable_steering()

    def data_received(self, receivedData):
        """
        Wird immer aufgerufen, wenn Daten ("receiveData") von einem verbundenen Client empfangen wird.
        Die empfangenen Daten werden dann ausgewährtet und auf bekannte Muster geprueft.
        Bei korrekt empfangenen und bekannten Nachrichten wird die gewuenschte Aktion ausgeloest.
        """
        print("Data received from Host {}: {!r}".format(self.peername, receivedData))

        readPos = 0
        while readPos < len(receivedData):
            
            #gehe die empfangenen bytes solange durch bis "/SRCCP/" gefunden wird
            if receivedData[readPos+2 : readPos+9] == b'/SRCCP/':
                
                try:
                    length = int.from_bytes(receivedData[readPos : readPos+2], "big")
        
                    frame = receivedData[readPos+2 : readPos+length+2]
                    
                    if DEBUG: 
                        print("Received SRCCP-Packet:")
                        print("parsed length: ", length)   
                        print("parsed frame: ", frame)
                    
                    if not frame.endswith(b'#/'):
                        print("ERROR: Wrong length or incomplete data received!")
                        self.SendNACK("TransmissionError", "Incomplete or malformed packet received")
                        # suche weiter nach einem Paket...
                        readPos += 1
                        continue
                    
                    
                    readPos += (length + 2) 
                    
                    headerEnd = frame.find(b'/#', 7)
                    header = frame[ : headerEnd]       
                    
                    message = frame[headerEnd+2 : -2].decode()
                    
                    ack = 0
                    
                    if DEBUG:    
                        print("header =\n", header)
                        print("---")
                        print("parsed length = ", length)
                        print("---")
                        print("message =\n", message)
                        print("---")
                        print("parsing XML...")
                       
                    root = ET.fromstring(message)
                        
                    if root.tag == "cmd":
                        command = root.find("name").text
                        print("command received: ", command)
                            
                        if command == "drive":
                            speed = root.find("speed").text
                            ack += Steuerung.drive(int(speed))
                            
                        elif command == "brake":
                            ack += Steuerung.brake()
                            
                        elif command == "steer":
                            angle = root.find("angle").text
                            if DEBUG:
                                print("Steering to ", angle)
                            ack += Steuerung.steer(int(angle))
                                
                        elif command == "subscribe":
                            if root.find("type").text == "data":
                                for Sen in root.findall("sensor"):
                                    ack += self.subscribeSensor(Sen.text, Sen.get("interval"))
                                    
                            elif root.find("type").text == "alert":
                                for Sen in root.findall("sensor"):
                                    ack += self.subscribeAlert(Sen.text)
                                          
                        elif command == "desubscribe":
                            if root.find("type").text == "data":
                                for sensor in root.findall("sensor"):
                                    ack += self.desubscribeSensor(sensor)
                                        
                            elif root.find("type").text == "alert":
                                for sensor in root.findall("sensor"):
                                    ack += self.desubscribeAlerts(sensor)
                        
                        elif command == "close":
                            print("Client '{}' closed the connection".format(self.peername))
                            self.transport.close()

                                
                    elif root.tag == "msg":
                        print("message received, nothing to do here...")
                            
                    elif root.tag == "ctlmsg":
                        print("controlmessage received. ERROR: Not implemented yet!")
                        # TODO: z.B. bei NACK Fehlermeldung auswerten und Nachricht evtl wiederholen?!
                            
                    else:
                        raise ValueError("unknown message")
                
                        
                except ValueError as e:
                    print("ValueError:" + e.args[0])
                    #self.transport.write("err({})\n".format(e.args[0]).encode())
                    self.SendNACK(command, e.args[0])
                except KeyError as e:
                    print("KeyError:" + e.args[0])
                    #self.transport.write("err({})\n".format(e.args[0]).encode())
                    self.SendNACK(command, e.args[0])
                else:
                    if ack == 0:
                        self.SendACK(command)
                    else:
                        self.SendNACK(command)
            else:
                #print('unknown protocol!\n') # kann sehr Ressourcen-fressend werden, falls viele unbekannte Daten empfangen werden!
                readPos += 1 #gehe einfach zum naechsten Zeichen und suche weiter nach bekannten Mustern...

    def SendMsg(self, Sensor, Message, Unit=None):
        """
        Diese Funktion packt die Sensordaten eines Sensors und optional die zugehoerige Einheit in eine XML
        und sendet diese XML als SRCCP-Paket an den Client, der den Sensor subscribed hat.
        """
        
        if DEBUG: print( "Sending Message of Sensor '{}' to Host '{}': '{}'".format(Sensor, self.peername, Message))
        root = ET.Element('msg')
        name = ET.SubElement(root, 'name')
        name.text = "sensordata"
        sensor = ET.SubElement(root, 'sensor')
        sensor.text = Sensor
        data = ET.SubElement(root, 'data')
        data.text = Message
        if Unit:
            unit = ET.SubElement(root, 'unit')
            unit.text = Unit
        xml = ET.tostring(root)
        if DEBUG:
            print("sending xml:\n", xml)
        self.SendSRCCPPacket(xml)
        

    def SendAlert(self, Sensor, Message):
        """
        Diese Funktion sendet eine Alert-Message eines Sensors an die Subscriber,
        indem sie eine XML erstellt und diese als SRCCP-Paket verschickt.
        """
        if DEBUG: print( "Sending Alert of Sensor '{}' to Host '{}': '{}'".format(Sensor, self.peername, Message))
        root = ET.Element('msg')
        name = ET.SubElement(root, 'name')
        name.text = "alert"
        sensor = ET.SubElement(root, 'sensor')
        sensor.text = Sensor
        #TODO: Severity einbauen!
        severity = ET.SubElement(root, 'severity')
        severity.text = "1"
        message = ET.SubElement(root, 'message')
        message.text = Message
        xml = ET.tostring(root)
        if DEBUG:
            print("sending xml:\n", xml)
        self.SendSRCCPPacket(xml)
        
        
    def SendACK(self, command):
        """
        Sendet ein acknowledgement
        """
        root = ET.Element('ctlmsg')
        name = ET.SubElement(root, 'name')
        name.text = "ack"
        type = ET.SubElement(root, 'type')
        type.text = command
        xml = ET.tostring(root)
        if DEBUG:
            print("sending ACK to Host '{}':\n {}".format(self.peername, xml))
        self.SendSRCCPPacket(xml)

    
    def SendNACK(self, Type, Errormsg = None):
        """
        Sendet ein NOTAcknowledgement
        """
        root = ET.Element('ctlmsg')
        name = ET.SubElement(root, 'name')
        name.text = "nack"
        type = ET.SubElement(root, 'type')
        type.text = Type
        if Errormsg:
            errormsg = ET.SubElement(root, 'message')
            errormsg.text = Errormsg
        xml = ET.tostring(root)
        if DEBUG:
            print("sending NACK to Host '{}':\n {}".format(self.peername, xml))
        self.SendSRCCPPacket(xml)
        
    
    def SendSRCCPPacket(self, XML):
        """
        Packt ein uebergebenes XML (oder eine andere Nachricht) in ein SRCCP-Paket,
        indem es den notwendigen Rahmen inklusive Paketgroesse hinzufuegt.
        """
        frame = b'/SRCCP/v0.1/#' + XML + b'#/'
        length = len(frame).to_bytes(2, "big")
        Packet = length + frame
        if DEBUG: print("Sending SRCCP-Packet to Host '{}':\n {}".format(self.peername, Packet))
        self.transport.write(Packet)
        
        
    def subscribeSensor(self, sensor, refreshtime = None):
        try:
            # if already subscribed desubscribe first:
            if sensor in self.subscribedSensors:
                self.subscribedSensors[sensor].desubscribe()
            else:
                self.subscribedSensors[sensor] = Sensorik.Sensoren[sensor]()

            # Subscribe:
            if refreshtime:
                if DEBUG: print("Host {} subscribes Sensor '{}' with refresh time {}\n".format(self.peername, sensor, refreshtime))
                self.subscribedSensors[sensor].subscribe(self.SendMsg, True, refreshtime)
            else:
                if DEBUG: print("Host {} subscribes Sensor '{}' with default refresh time\n".format(self.peername, sensor))
                self.subscribedSensors[sensor].subscribe(self.SendMsg)
        
        except KeyError:
            print("ERROR: Unknown sensor '{}'".format(sensor))
            self.SendNACK("subscribe", "unknown sensor {}".format(sensor))
            return 1
        except ValueError as e:
            print("ValueError:" + e.args[0])
            self.SendNACK("subscribe", e.args[0])
            return 1
        except:
            print("OtherError:" + e.args[0])
            self.SendNACK("subscribe", e.args[0])
            return 1
        else:
            return 0
        
    def subscribeAlert(self, sensor):
        if DEBUG: print("Host {} subscribes Alerts from Sensor {}\n".format(self.peername, Sen))
        
        try:
            Sensorik.Sensoren[sensor].SubscribeAlerts(self.SendAlert)
        
        except KeyError:
            print("KeyError: Unknown sensor '{}'".format(sensor))
            self.SendNACK("subscribe", "unknown sensor {}".format(sensor))
            return 1
        except ValueError as e:
            print("ValueError:" + e.args[0])
            self.SendNACK("subscribe", e.args[0])
            return 1
        except:
            print("OtherError:" + e.args[0])
            self.SendNACK("subscribe", e.args[0])
            return 1
        else:
            return 0
        
        
    def desubscribeSensor(self, sensor):
        try:
            if DEBUG: print("Host {} desubscribes Sensor {}\n".format(self.peername, sensor))
            self.subscribedSensors[sensor].desubscribe()
            del self.subscribedSensors[sensor]
        except KeyError:
            print("KeyError: Sensor not subscribed or unknown sensor '{}'".format(sensor))
            self.SendNACK("desubscribe", "Sensor not subscribed or unknown sensor '{}'".format(sensor))
            return 1
        else:
            return 0
        
    def desubscribeAlerts(self, sensor):
        try:
            if DEBUG: print("Host {} desubscribes Alerts from Sensor {}\n".format(self.peername, sensor))
            Sensorik.Sensoren[sensor].DesubscribeAlerts(self.SendAlert)
            del self.subscribedSensors[sensor]
        except KeyError:
            print("KeyError: Sensor not subscribed or unknown sensor '{}'".format(sensor))
            self.SendNACK("desubscribe", "Sensor not subscribed or unknown sensor '{}'".format(sensor))
            return 1
        except:
            print("OtherError while desubscribing alerts from sensor '{}'".format(sensor))
            self.SendNACK("desubscribe", e.args[0])
            return 1
        else:
            return 0


loop = asyncio.get_event_loop()

# Im Autostart mus etwas gewartet werden, bis das Netzwerk initialisiert ist und der Serielle Port verfuegbar ist:
if "-a" in sys.argv:
    import lcd
    import time
    loop.run_until_complete(lcd.init())
    loop.run_until_complete(lcd.printString("Starting Socket-", lcd.line1))
    loop.run_until_complete(lcd.printString("Server ...", lcd.line2))
    time.sleep(10)


# Each client connection will create a new protocol instance
coro = loop.create_server(SRCCP, IP, PORT)
server = loop.run_until_complete(coro)

Sensorik.init(loop)
              
if DEBUG:
    # Enable Debugging mode of asyncio:
    loop.set_debug(True)
    import logging
    logging.basicConfig(level=logging.DEBUG)

# Serve requests until Ctrl+C is pressed
print('Serving on {}'.format(server.sockets[0].getsockname()))

def sigterm_handler(_signo, _stack_frame):
    print("Script terminated.")
    sys.exit(0)

#register sigterm_handler:
signal.signal(signal.SIGTERM, sigterm_handler)

try:
    loop.run_forever()
except KeyboardInterrupt:
    print("Interrupted by user.")
finally:
    print("Cleaning up...")
    # Close the server:
    server.close()
    loop.run_until_complete(server.wait_closed())
    # Stop autorefreshing the sensors:
    Sensorik.close()
    Steuerung.close()
    loop.run_until_complete(loop.shutdown_asyncgens())
    loop.close()
