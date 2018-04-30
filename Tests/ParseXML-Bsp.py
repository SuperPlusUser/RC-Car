# extrahiee Zahl in Form eines Strings zwischen length: und \n

# TODO:
# - Noch den Fall berücksichtigen, dass eine Nachricht nicht vollständig empfangen wird / aufgeteilt wird
# - Exception-Handling...
import xml.etree.ElementTree as ET


receivedData = b'''
\x00\x9d/SRCCP/v0.1/#<command>
    <name>subscribe</name>
    <type>data</type>
    <sensor interval="10">Sensor1</sensor>
    <sensor>Sensor2</sensor>
</command>
#/

\x00\x4e/SRCCP/#
<command>
    <name>drive</name>
    <speed>100</speed>
</command>
#/
'''


readPos = 0
while readPos < len(receivedData):
    
    if receivedData[readPos+2 : readPos+9] == b'/SRCCP/':
        
        length = int.from_bytes(receivedData[readPos : readPos+2], "big")
        
        frame = receivedData[readPos : readPos+length+2]
        
        if not frame.endswith(b'#/'):
            print("ERROR: Wrong length or incomplete data received!")
            #send nack
            # suche weiter nach einem Paket...
            readPos += 1
            continue
        
        
        readPos += (length + 2) 
        
        
        headerEnd = frame.find(b'/#', 7)

        header = frame[ : headerEnd]       
        
        message = frame[headerEnd+2 : -2].decode()
        
            
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
            print("message received/nnothing to do here...")
                
        elif root.tag == "ctlmsg":
            print("controlmessage received")
            #TODO: bei NACK Fehlermeldung auswerten und Nachricht evtl wiederholen?!
                
        else:
            print("ERROR: unknown message")
        print("----------------------")

    else:
        #print('unknown protocol!\n') # wird performance-hungrig bei vielen falschen Bytes!!!
        readPos += 1
        