# extrahiee Zahl in Form eines Strings zwischen length: und \n

# TODO:
# - Falls length zu lang angegeben ist, wird die nachfolgende Nachricht nicht ausgewertet...
# --> length muss genau stimmen, ansonsten kommt alles durcheinander!
# - Noch den Fall berücksichtigen, dass eine Nachricht nicht vollständig empfangen wird / aufgeteilt wird
# - Exception-Handling...
import xml.etree.ElementTree as ET


receivedData = b'''
//SRCCP//v0.1
length:141

---START---
<command>
    <name>subscribe</name>
    <type>data</type>
    <sensor interval="10">Sensor1</sensor>
    <sensor>Sensor2</sensor>
</command>
---END---

//SRCCP//v0.1
length:66

---START---
<command>
    <name>drive</name>
    <speed>100</speed>
</command>
---END---
'''


readPos = 0
while readPos < len(receivedData):
    
    received = receivedData[readPos : ]
    
    if received.startswith(b'//SRCCP//'):
    
        headerEnd = received.find(b'\n---START---\n')
        messageBegin = headerEnd + 13

        header = received[0 : headerEnd].decode()
                    
        lengthPos = header.find('length:')
        length = int(header[lengthPos + len('length:') : header.find('\n', lengthPos)])
        
        messageEnd = messageBegin + length
        
        if received[messageEnd : messageEnd + 11] == b'\n---END---\n':
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
                    print("Set speed to ", speed)
                    
                if command == "subscribe":
                    if root.find("type").text == "data":
                        for Sen in root.findall("sensor"):
                            Sensor = Sen.text
                            refreshtime = Sen.get("interval")
                            if refreshtime:
                                print("Subscribing Data from Sensor '{}' with refreshtime {}".format(Sensor, refreshtime))
                            else:
                                print("Subscribing Data from Sensor '{}' with default refreshtime".format(Sensor))
                    
            elif root.tag == "message":
                print("message received")
                
            elif root.tag == "ctlmsg":
                print("controlmessage received")
                
            else:
                print("ERROR: unknown message")
            print("----------------------")
            
            
        else:
            print("ERROR: invalid length or incomplete data received")
            readPos += 1

    else:
        #print('unknown protocol!\n')
        readPos += 1