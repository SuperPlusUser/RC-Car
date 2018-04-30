<<<<<<< HEAD
import Sensorik
import time
import asyncio

loop = asyncio.get_event_loop()
Sensorik.init(loop)

V = Sensorik.Batt_Mon_Voltage()
I = Sensorik.Batt_Mon_Current()
C = Sensorik.Batt_Mon_Charge()

start = time.time()

try:
    v = open('Ladekennlinie_Voltage', 'w')
    v.write("time, voltage[V]\n")
    V.subscribe((lambda n,d,u : v.write(str(time.time() - start) +", " + d + "\n")), False, 10)
    
    i = open('Ladekennlinie_Current', 'w')
    i.write("time, current[A]\n")
    I.subscribe((lambda n,d,u : i.write(str(time.time() - start) +", " + d + "\n")), False, 10)
    
    c = open('Ladekennlinie_Charge', 'w')
    c.write("time, charge[mAh]\n")
    start_charge = float(C.getSensorData())
    C.subscribe((lambda n,d,u : c.write( str(time.time() - start) +", " + str(float(d) - start_charge) + "\n")), False, 10)
    
    loop.run_forever()
    
finally:
    print("Saving Files...")
    v.close()
    i.close()
    c.close()
    Sensorik.close()
=======
import Sensorik_async as Sensorik
import time
import asyncio

start = time.time()
loop = asyncio.get_event_loop()

Sensorik.init(loop)

try:
    V = Sensorik.INA219_Voltage()
    I = Sensorik.INA219_Current()

    v = open('Entladekennlinie_Voltage', 'w')
    v.write("time, voltage[V]\n")
    V.subscribe((lambda n,d,u : v.write(str(time.time() - start) +", " + d + "\n")), False, 10)
    
    i = open('Entladekennlinie_Current', 'w')
    i.write("time, current[A]\n")
    I.subscribe((lambda n,d,u : i.write(str(time.time() - start) +", " + d + "\n")), False, 10)
    
    loop.run_forever()
    
finally:
    print("Saving Files...")
    v.close()
    i.close()
    Sensorik.close()
>>>>>>> 7c7b7429a99c1b0c8e68dfaecdf3e9240966f79f
