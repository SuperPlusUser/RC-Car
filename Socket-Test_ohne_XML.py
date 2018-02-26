#!/usr/bin/env python3

## Version 0.2.7 (ohne XML --> Debugging)

## Befehle:
# - sub(<Sensor>[:<refreshtime>])
# - desub(<Sensor>)
# - drv(<Speed>)
# - close()

## Changelog:
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
# - Nachrichten im XML-Format austauschen?!
# - Warum funktionieren manchmal keine KeyboardInterrupts?
# - Kommentierung und Exception-Handling verbessern


import asyncio
import sys

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

        # Desubscribe Alerts from all Sensors:
        for Sen in Sensorik.Sensoren:
            Sensorik.Sensoren[Sen].DesubscribeAlerts(self.SendAlert)

    def data_received(self, data):
        err = False             # um "sonstige" Fehler zu speichern (TODO: evtl andere Loesung suchen!)
        message = data.decode()
        print("Data received from Host {}: {!r}".format(self.peername, message))

        try:
            try:
                command = message[:message.index("(")]
                operand = message[message.index("(")+1 : message.index(")")]
            except ValueError:
                raise ValueError("wrong format. try 'command(operand)'")


            # bekannte Befehle abfangen:

            if command == "drv":
                Steuerung.drive(int(operand))

            elif command == "sub":
                sensors = operand.split(",")
                print("Host {} subscribes Sensor(s) {}\n".format(self.peername, sensors))
                for sen in sensors:
                    try:
                        if ":" in sen:
                            sensor,t = sen.split(":")
                        else:
                            sensor = sen
                            t = None

                        # if already subscribed desubscribe:
                        if sensor in self.subscribedSensors:
                            self.subscribedSensors[sensor].desubscribe()
                        else:
                            self.subscribedSensors[sensor] = Sensorik.Sensoren[sensor]()

                        # Subscribe (only new values):
                        self.subscribedSensors[sensor].subscribe(self.SendMsg, True, t)

                    except KeyError:
                        print("ERROR: Unknown sensor '{}'".format(sensor))
                        self.transport.write("err(sub '{}', unknown sensor!)\n".format(sensor).encode())
                        err = True
                        pass # Falls ein Sensor nicht existiert, sollen die folgenden trotzdem noch abonniert werden
                    except ValueError as e:
                        print("ValueError:" + e.args[0])
                        self.transport.write("err(sub {}: {})\n".format(sensor, e.args[0]).encode())
                        err = True
                        pass
                    else:
                        self.transport.write("ack(sub '{}')\n".format(sensor).encode())

            elif command == "desub":
                sensors = operand.split(",")
                print("Host {} desubscribes Sensor(s) {}\n".format(self.peername, sensors))
                for sensor in sensors:
                    try:
                        self.subscribedSensors[sensor].desubscribe()
                        del self.subscribedSensors[sensor]
                        self.transport.write("ack(desub '{}')\n".format(sensor).encode())
                    except KeyError:
                        print("ERROR: Sensor not subscribed or unknown sensor '{}'".format(sensor))
                        self.transport.write("err(desub '{}', sensor not subscribed or unknown sensor)\n".format(sensor).encode())
                        err = True
                        pass # Falls ein Sensor nicht existiert, sollen die folgenden trotzdem noch deabonniert werden

            elif command == "close":
                print("Closing connection to client {}".format(self.peername))
                self.transport.close()

            else:
                raise ValueError("unknown command")

        except ValueError as e:
            print("ValueError:" + e.args[0])
            self.transport.write("err({})\n".format(e.args[0]).encode())
        except KeyError as e:
            print("KeyError:" + e.args[0])
            self.transport.write("err({})\n".format(e.args[0]).encode())
        else:
            if err:
                self.transport.write("err({})\n".format(command).encode())
            else:
                self.transport.write("ack({})\n".format(command).encode())
            err = False

    def SendMsg(self, Type, Message, Unit):
        if DEBUG: print( "Sending Message of Type {} to Host {}: {}".format(Type, self.peername, Message))
        self.transport.write((str(Type) + "(" + str(Message) + " " + str(Unit) + ")\n").encode())

    def SendAlert(self, Sensor, Message):
        if DEBUG: print( "Sending Alert of Sensor {} to Host {}: {}".format(Sensor, self.peername, Message))
        self.transport.write(("ALERT:" + str(Sensor) + "(" + str(Message) + ")\n").encode())

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
    # Close the server
    server.close()
    loop.run_until_complete(server.wait_closed())
    for task in asyncio.Task.all_tasks():
        print("cancelling task {}".format(task))
        task.cancel()
    loop.close()
