# Simple demo of of the WS2801/SPI-like addressable RGB LED lights.
import time
import RPi.GPIO as GPIO
 
# Import the WS2801 module.
import Adafruit_WS2801
import Adafruit_GPIO.SPI as SPI

import threading
import pigpio

import Sensorik #_fake as Sensorik
 
 
# Configure the count of pixels:
PIXEL_COUNT = 40
 
# Alternatively specify a hardware SPI connection on /dev/spidev0.0:
SPI_PORT   = 0
SPI_DEVICE = 0
Pixels = Adafruit_WS2801.WS2801Pixels(PIXEL_COUNT, spi=SPI.SpiDev(SPI_PORT, SPI_DEVICE), gpio=GPIO)

BLINK_RIGHT = (3, 4, 5)
BLINK_LEFT = (34, 35, 36)

BRAKE_LIGHT = (17, 18, 21, 22)
FRONT_LIGHT = (0, 1, 2, 37, 38, 39)
BACK_LICHT = (16, 23)
REVERSE_LIGHT = (19, 20)

light_modes = (-1,0,1,10)
light_mode = 0
light_events = {}
for mode in light_modes:
    light_events[mode] = None
    
# --- Initialisiere IR-LED ---
IR = 21
l = pigpio.pi()
l.set_mode(IR, pigpio.OUTPUT)
l.write(IR, 0) # IR-LED standardmaessig aus

 
# --- Effects ---- 
# Define the wheel function to interpolate between different hues.
def wheel(pos):
    if pos < 85:
        return Adafruit_WS2801.RGB_to_color(pos * 3, 255 - pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return Adafruit_WS2801.RGB_to_color(255 - pos * 3, 0, pos * 3)
    else:
        pos -= 170
        return Adafruit_WS2801.RGB_to_color(0, pos * 3, 255 - pos * 3)
 
# Define rainbow cycle function to do a cycle of all hues.
def rainbow_cycle_successive(pixels = Pixels, wait=0.1):
    for i in range(pixels.count()):
        # tricky math! we use each pixel as a fraction of the full 96-color wheel
        # (thats the i / strip.numPixels() part)
        # Then add in j which makes the colors go around per pixel
        # the % 96 is to make the wheel cycle around
        pixels.set_pixel(i, wheel(((i * 256 // pixels.count())) % 256) )
        pixels.show()
        if wait > 0:
            time.sleep(wait)
 
def rainbow_cycle(pixels = Pixels, wait=0.005):
    for j in range(256): # one cycle of all 256 colors in the wheel
        for i in range(pixels.count()):
            pixels.set_pixel(i, wheel(((i * 256 // pixels.count()) + j) % 256) )
        pixels.show()
        if wait > 0:
            time.sleep(wait)
 
def rainbow_colors(pixels = Pixels, wait=0.05):
    for j in range(256): # one cycle of all 256 colors in the wheel
        for i in range(pixels.count()):
            pixels.set_pixel(i, wheel(((256 // pixels.count() + j)) % 256) )
        pixels.show()
        if wait > 0:
            time.sleep(wait)
            
def spin(pixels = Pixels, color="changing", step = 1, wait = 0.02, reverse = False):
    pos = 0
    if color == "changing":
        change = True
    else:
        change = False
        
    if reverse:
        Range = reversed(range(0, pixels.count()- step + 1, step))
    else:
        Range = range(0, pixels.count()- step + 1, step)
        
    for j in Range:
        pixels.clear()
        if change:
            for l in range(j, j+step):
                pixels.set_pixel(l, wheel(((j * 256 // pixels.count())) % 256))
        else:
            for l in range(j, j+step):
                pixels.set_pixel(l, Adafruit_WS2801.RGB_to_color( color[0], color[1], color[2] ))
        pixels.show()
        time.sleep(wait)
 
def appear_from_back_blocking(pixels = Pixels, color="changing", step = 1, wait = 0.02):
    pos = 0
    if color == "changing":
        change = True
    else:
        change = False
    for i in range(0, pixels.count(), step):
        for j in reversed(range(i, pixels.count()- step + 1, step)):
            pixels.clear()
            # first set all pixels at the begin
            for k in range(i):
                if change:
                    pixels.set_pixel(k, wheel(((k * 256 // pixels.count())) % 256))
                else:
                    pixels.set_pixel(k, Adafruit_WS2801.RGB_to_color( color[0], color[1], color[2] ))
            # set then the pixel at position j
            if change:
                for l in range(j, j+step):
                    pixels.set_pixel(l, wheel(((j * 256 // pixels.count())) % 256))
            else:
                for l in range(j, j+step):
                    pixels.set_pixel(l, Adafruit_WS2801.RGB_to_color( color[0], color[1], color[2] ))
            pixels.show()
            time.sleep(wait)
            
def blink(pixels = Pixels, blink_range = range(Pixels.count()), blink_delay = 0.5, color = (255, 50, 0), blink_times = 1):
    blink_counter = 0
    current_light_mode = light_mode
    while blink_counter < blink_times:
        try:
            for i in blink_range:
                pixels.set_pixel_rgb(i, color[0], color[1], color[2])
            pixels.show()
            if light_events[current_light_mode].wait(timeout = blink_delay):
                return
            for i in blink_range:
                pixels.set_pixel_rgb(i, 0, 0, 0)
            pixels.show()
            if light_events[current_light_mode].wait(timeout = blink_delay):
                return
            blink_counter += 1
        finally:
            for i in blink_range:
                pixels.set_pixel_rgb(i, 0, 0, 0)
            pixels.show()         
 
# -------------- 
# --- MODE 0 ---
# --------------
def front_light(on = "toggle", area = FRONT_LIGHT, area_back = BACK_LICHT, pixels = Pixels, color = (255, 120, 100), color_back = (90, 0, 0)):
    if light_mode == 0:
        global front_light_on
        if on == "toggle":
            front_light_on = not front_light_on
        else:
            front_light_on = on
        
        if front_light_on:
            for pixel in area:
                pixels.set_pixel_rgb(pixel, color[0], color[1], color[2])
            for pixel in area_back:
                pixels.set_pixel_rgb(pixel, color_back[0], color_back[1], color_back[2])
        else:
            for pixel in area + area_back:
                pixels.set_pixel_rgb(pixel, 0, 0, 0)
        pixels.show()
            
def brake_light(on = True, area = BRAKE_LIGHT, pixels = Pixels, color = (255, 0, 0)):
    if light_mode == 0:
        if on:
            for pixel in area:
                pixels.set_pixel_rgb(pixel, color[0], color[1], color[2])
        else:
            for pixel in area:
                pixels.set_pixel_rgb(pixel, 0, 0, 0)
        #pixels.show()
            
def reverse_light(on = True, area = REVERSE_LIGHT, pixels = Pixels, color = (255, 120, 100)):
    if light_mode == 0:
        if on:
            for pixel in area:
                pixels.set_pixel_rgb(pixel, color[0], color[1], color[2])
        else:
            for pixel in area:
                pixels.set_pixel_rgb(pixel, 0, 0, 0)
                
# ---------------


class battery():
    
    def __init__(self, pixels = Pixels):
        self.pixels = Pixels
        self.BattSenCurrent = None
        self.BattSenCharge = None
        self.Blink = False
        self.toggle_off = False
        
    def start(self):
        self.light_mode = light_mode
        
        if not self.BattSenCharge:
            self.BattSenCharge = Sensorik.Batt_Mon_Charge()
            self.BattSenCharge.subscribe(self.receive_charge, OnlyNew = False, time = 1)
            
        if not self.BattSenCurrent:
            self.BattSenCurrent = Sensorik.Batt_Mon_Current()
            self.BattSenCurrent.subscribe(self.receive_current, OnlyNew = False, time = 1)
            
    def stop(self):
        if self.BattSenCurrent:
            self.BattSenCurrent.desubscribe()
            self.BattSenCurrent = None
            
        if self.BattSenCharge:
            self.BattSenCharge.desubscribe()
            self.BattSenCharge = None
        
    def receive_charge(self, Sensor, Data, Unit):
        if self.light_mode == light_mode:
            self.pixels.clear()
            if not self.toggle_off:
                percent = int(float(Data) / type(self.BattSenCharge).MAX_CHARGE * 100)
                activatedPixels =  int(percent * self.pixels.count() / 100)
                for pixel in range(activatedPixels):
                    self.pixels.set_pixel_rgb(pixel, 256 - 2 * percent, percent, 0)
                if self.Blink:
                    self.toggle_off = True
            else:
                self.toggle_off = False
            self.pixels.show()
            
    def receive_current(self, Sensor, Data, Unit):
        if float(Data) > 0:
            #Beim Laden Blinken aktivieren:
            self.Blink = True
        else:
            self.Blink = False
        

class blinker():
    
    def __init__(self, pixels = Pixels, color = (255, 50, 0)):
        self.LED_ON = False
        self.color = color
        self.pixels = Pixels
        self.LenkSen = None
        
    def start(self):
        self.light_mode = light_mode
        
        if not self.LenkSen:
            self.LenkSen = Sensorik.Lnk_Pos()
            self.LenkSen.subscribe(self.receive_steer_position, OnlyNew = False, time = 0.5)
            
    def stop(self):
        if self.LenkSen:
            self.LenkSen.desubscribe()
            self.LenkSen = None
        
    def receive_steer_position(self, Sensor, Data, Unit):
        if self.light_mode == light_mode:
            if self.LED_ON:
                self.off()
            elif int(Data) > 75:
                self.on("left")
            elif int(Data) < 25:
                self.on("right")
            else:
                self.off()
        
    def on(self, side = "both"):
        if side == "left":
            blinker = BLINK_LEFT
        elif side == "right":
            blinker = BLINK_RIGHT
        else:
            blinker = BLINK_LEFT + BLINK_RIGHT
            
        for pixel in blinker:
            self.pixels.set_pixel_rgb(pixel, self.color[0], self.color[1], self.color[2])
        self.pixels.show()
        self.LED_ON = True
        
    def off(self):
        blinker = BLINK_LEFT + BLINK_RIGHT    
        for pixel in blinker:
            self.pixels.set_pixel_rgb(pixel, 0, 0, 0)
        self.pixels.show()
        self.LED_ON = False
        
class spinner():
    
    def __init__(self, pixels = Pixels, color = "change"):
        self.LED_ON = False
        self.color = color
        self.pixels = Pixels
        self.SpeedSen = None
        
    def start(self):
        self.light_mode = light_mode
        
        if not self.SpeedSen:
            self.SpeedSen = Sensorik.Mtr_Speed()
            self.SpeedSen.subscribe(self.receive_speed, OnlyNew = False, time = 0.5)
            
    def stop(self):
        if self.SpeedSen:
            self.SpeedSen.desubscribe()
            self.SpeedSen = None
        
    def receive_speed(self, Sensor, Data, Unit):
        if self.light_mode == light_mode:
            pass#TODO
        
        
Battery = battery()
Blinker = blinker()
Spinner = spinner()

def change_mode(mode = "toggle"):
    global light_mode, light_thread, light_events
    #light_mode = 0 # Normal (Bremslicht etc.) = 0, Alert = -1, Farbwechsel etc > 0...
    global Blinker
    
    # Stop light_threads:
    if light_events[light_mode]:
        light_events[light_mode].set()
        
    Pixels.clear()
    Pixels.show()  # Make sure to call show() after changing any pixels!
    
    if mode == "toggle":
        light_mode = light_modes[(light_modes.index(light_mode) + 1) % len(light_modes)]
        while light_mode < 0:
            light_mode = light_modes[(light_modes.index(light_mode) + 1) % len(light_modes)]
    elif mode in light_modes:
        light_mode = mode
    else:
        raise ValueError("invalid light_mode")
    
    print("Light Mode set to", light_mode)
    
    if light_mode == -1:
        light_events[light_mode] = threading.Event()
        thread = threading.Thread(target=blink, kwargs={'blink_times':10, 'color':(100, 0, 0)})
        thread.start()
        
    if light_mode == 0:
        Blinker.start()
        front_light(on = True)
        light_thread = None
        light_events[light_mode] = None
    else:
        Blinker.stop()
 
    if light_mode == 1:
        Battery.start()
        light_thread = None
        light_events[light_mode] = None
    else:
        Battery.stop()     
        
    if light_mode == 10:
        l.write(IR, 1)
    else:
        l.write(IR, 0)



if __name__ == "__main__":
    # Clear all the pixels to turn them off.
    Pixels.clear()
    Pixels.show()  # Make sure to call show() after changing any pixels!
 
    #rainbow_cycle_successive(Pixels, wait=0.1)
    #rainbow_cycle(Pixels, wait=0.01)
    #appear_from_back_blocking(Pixels, step = 2)
    #blink(Pixels, blink_times = 3, color=(255, 0, 0))
    #blink(Pixels, blink_times = 3, color=(0, 255, 0))
    #blink(Pixels, blink_times = 3, color=(0, 0, 255))
    #rainbow_colors(Pixels)
    #brightness_decrease(Pixels)
    for i in range(10):
        spin(step = i+1, wait = 0.05)
