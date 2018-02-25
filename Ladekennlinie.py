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