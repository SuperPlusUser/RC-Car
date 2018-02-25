"""
16x2 I2C Display
Version 1.0.1
DELOARTS Research Inc.
Philip Delorenzo
02.05.2016
"""
# Anmerkung: von smbus auf pigpio umgestellt
# auf asyncio umgestellt

import pigpio
import asyncio

pi = pigpio.pi()

# Basic display data (change them for your display)
deviceAddress  = 0x27   # I2C device address
                        # Use i2cdetect -y 1 to find your lcd
deviceWidth = 16 # Maximum characters per line
# Device constants
CHR = 1 # Mode - Sending data
CMD = 0 # Mode - Sending command
# Device deviceAddressesses (refer to the data sheet)
line1 = 0x80
line2 = 0xC0
line3 = 0x94
line4 = 0xD4
backlightOn = 0x08
backlightOff = 0x00
# Time "delays" for the I2C bus
ePulse = 0.0001
eDelay = 0.0001
# Enable the I2C bus
d = pi.i2c_open(1, deviceAddress)
lock = asyncio.Lock()

async def init():
    await lock.acquire()
    await sendByte(0x33, CMD)
    await sendByte(0x32, CMD)
    await sendByte(0x06, CMD)
    await sendByte(0x0C, CMD)
    await sendByte(0x2B, CMD)
    await asyncio.sleep(eDelay)
    await clear()
    await setBacklightOn()
    lock.release()
    
async def close():
    await clear()
    await setBacklightOff()

async def sendByte(bits, mode):
    
    # bits = data
    # mode = 1 for data
    #        0 for command   
    bitsHigh = mode | (bits & 0xF0) | backlightOn
    bitsLow = mode | ((bits << 4) & 0xF0) | backlightOn
    pi.i2c_write_byte(d, bitsHigh)
    await asyncio.sleep(eDelay)
    pi.i2c_write_byte(d, (bitsHigh | 0b00000100)) # 0b00000100: enable
    await asyncio.sleep(ePulse)
    pi.i2c_write_byte(d, (bitsHigh & ~0b00000100))
    await asyncio.sleep(eDelay)
    pi.i2c_write_byte(d, bitsLow)
    await asyncio.sleep(eDelay)
    pi.i2c_write_byte(d, (bitsLow | 0b00000100))
    await asyncio.sleep(ePulse)
    pi.i2c_write_byte(d, (bitsLow & ~0b00000100))
    await asyncio.sleep(eDelay)
    wait = False

async def setBacklightOn():
    pi.i2c_write_byte(d, backlightOn)
    await asyncio.sleep(eDelay)

async def setBacklightOff():
    pi.i2c_write_byte(d, backlightOff)

async def clear():
    await sendByte(0x01, CMD)

async def printString(message, line):
    await lock.acquire()
    
    message = message.ljust(deviceWidth, " ")
    await sendByte(line, CMD)
    for i in range(deviceWidth):
        await sendByte(ord(message[i]), CHR)
        
    lock.release()
        
async def printScrollingString(messageL1, messageL2, times = 1):    
    l1 = len(messageL1)
    l2 = len(messageL2)
    await printString(messageL1, line1)
    await printString(messageL2, line2)
    if l1 > deviceWidth or l2 > deviceWidth:
        lock.acquire()
        for t in range(times):
            await asyncio.sleep(1)
            for i in range(max(l1,l2) - deviceWidth + 1):
                if i < l1 - deviceWidth + 1:
                    #await printString(messageL1[i : i+deviceWidth], line1)
                    await sendByte(line1, CMD)
                    for j in range(deviceWidth):
                        await sendByte(ord(messageL1[j + i]), CHR)
                if i < l2 - deviceWidth + 1:
                    #await printString(messageL2[i : i+deviceWidth], line2)
                    await sendByte(line2, CMD)
                    for j in range(deviceWidth):
                        await sendByte(ord(messageL2[j + i]), CHR)
                await asyncio.sleep(0.2)
            
        lock.release()
            
if __name__ == "__main__":       
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(init())
        loop.run_until_complete(printScrollingString("Zahlen:", "<1|2|3|4|5|6|7|8|9|10|11|12|13|14|15|16|17|18|19|20>", 10))
        loop.run_forever()
    finally:
        loop.run_until_complete(close())
        loop.close()