#!/usr/bin/env python3

## Version 0.1

## TODO:
# - bei jedem sub eine individuelle Aktualisierungszeit
# - Warum funktionieren manchmal keine KeyboardInterrupts?

import asyncio

IP = "192.168.177.54"
PORT = 8888

SensorDat1 = "xyz"
SensorDat2 = 0

DefPubDelay = 5 # Zeit in Sekunden zwischen Updates der Sensordaten

WelcomeMsg = """
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

def SensorFkt1():
    return SensorDat1

def SensorFkt2():
    global SensorDat2
    SensorDat2 += 1
    return SensorDat2

#Hier koennen die Funktionen definiert werden, die den jeweiligen Sensorwert zurueckliefern (z.B. "Temp" : Sensors.getTemp):
SensorDict = {"Sensor1" : SensorFkt1, "Sensor2" : SensorFkt2}



class ServerProtocol(asyncio.Protocol):
    """
    Implementierung eines eigenen Netzwerkprotokol, indem die Methoden der Basisklasse
    "asyncio.Protocol" ueberschrieben werden.
    weitere Infos: https://docs.python.org/3/library/asyncio-protocol.html?highlight=protocol#protocols
    """
    def __init__(self):
        self.runningSensorTasks = {} # leeres Dictionary, in dem die Tasks eingetragen werden, welche die Sensordaten senden.
        
    def connection_made(self, transport):
        self.peername = transport.get_extra_info('peername')
        print("Connection from {}".format(self.peername))
        self.transport = transport
        self.transport.write(WelcomeMsg.encode())

    def connection_lost(self, exc):
        print("Client {} closed the connection".format(self.peername))
        for sensor in  self.runningSensorTasks:
            print("cancel publishing value of sensor {}".format(sensor)) 
            self.runningSensorTasks[sensor].cancel()

    def data_received(self, data):
        err = False             # um "sonstige" Fehler zu speichern (TODO: evtl andere Loesung suchen!)
        message = data.decode()
        print("Data received: {!r}".format(message))

        try:
            try:
                command = message[:message.index("(")]
                operand = message[message.index("(")+1 : message.index(")")]
            except ValueError:
                raise ValueError("wrong format. try 'command(operand)'")


            # bekannte Befehle abfangen:
            if command == "close":
                print("closing connection...")
                self.transport.close()


            elif command == "sub":
                sensors = operand.split(",")
                print("subscribing Sensor(s) {}\n".format(sensors))
                
                for sen in sensors:
                    
                    try:
                        sensor,t = sen.split(":")
                        time = float(t)
                        if time < 0.1 or time > 3600:
                            print("Time out of range. Taking default time {}s".format(DefPubDelay))
                            self.transport.write("err(Time out of range. Taking default time {}s)\n".format(DefPubDelay).encode())
                            time = DefPubDelay
                    except ValueError as e:
                        print("ValueError:" + e.args[0])
                        # self.transport.write("err({})\n".format(e.args[0]).encode())
                        sensor = sen
                        time = DefPubDelay
                        pass
                        
                    if sensor in self.runningSensorTasks:
                        print("ERROR: Sensor '{}' already subscribed".format(sensor))
                        self.transport.write("err(already subscribed {})\n".format(sensor).encode())
                        err = True
                    else:
                        try:
                            self.runningSensorTasks[sensor] = loop.create_task(self.Send_Sensor_Dat(sensor, SensorDict[sensor], time))
                        except KeyError:
                            print("ERROR: unknown sensor '{}'".format(sensor))
                            self.transport.write("err(unknown sensor '{}')\n".format(sensor).encode())
                            err = True
                            pass # Falls ein Sensor nicht existiert, sollen die folgenden trotzdem noch abonniert werden
                        else:
                            self.transport.write("ack(sub '{}')\n".format(sensor).encode())

            # Hier weitere Befehle mit elif ... einfuegen!

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


    async def Send_Sensor_Dat(self, sensor, sensorFkt, time):
        while True:
            print("Reading Data from Sensor {}".format(sensor))
            sensorDat = (sensor + "(" + str(sensorFkt()) + ")\n").encode()
            print("Sending Sensor Data: {}".format(sensorDat))
            self.transport.write(sensorDat)
            await asyncio.sleep(time)


loop = asyncio.get_event_loop()
# Each client connection will create a new protocol instance
coro = loop.create_server(ServerProtocol, IP, PORT)
server = loop.run_until_complete(coro)


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
    loop.close()
