#!/usr/bin/env python3

## Version 0.3
#
## Changelog:
#
# --- 0.3 ---
# - Sensoren werden nun in eigenen Threads aktualisiert --> Main-Thread wird waehrend dem Aktualisieren nicht blockiert
#
# --- 0.2.5 ---
# - asyncio.ensure_future statt loop.create_task
# - SensorMeta hinzugefuegt --> Problem mit Vererbung von Klassen-Variablen geloest
#

## TODO:
# - Exceptions etc. in den Tasks werden nicht weitergegeben?!
# - Kommentierung und Exception-Handling verbessern
# - Uebersichtlichkeit verbessern
# - Werte die 0 sind werden nicht ausgegeben (siehe unten...)


import time
import sys
from concurrent.futures import ThreadPoolExecutor
executor = ThreadPoolExecutor(max_workers=100) # max_workers muss bei mehr Sensoren erhoeht werden
import subprocess
import asyncio

import ina219
# Quelle: https://github.com/chrisb2/pi_ina219

import lcd_pigpio as lcd

import pigpio

DEBUG = True if "-d" in sys.argv else False
Running = True


# ---------------------------
## --- globale Funktionen ---
# ---------------------------

def close():
    global Running
    Running = False
    cb1.cancel()
    lcd.init()
    lcd.clear()
    lcd.setBacklightOff()
    print("Stopping auto-refresh threads for all sensors...")
    executor.shutdown() # TODO: Hier muss man im schlimmsten Fall so lange warten, bis die laengste REFRESH_TIME abgelaufen ist

def PrintSensorData(Sensor, Data, Unit):
    print(str(Sensor), ":", str(Data) + " " + str(Unit))

def PrintAlerts(Type, Msg):
    print("! Alert from Sensor {} received: {} !".format(Type, Msg))
    
def DisplaySensorData(Sensor, Data, Unit):
    if not DispAlert: #Alerets haben Vorrang
        lcd.printString(str(Sensor) + ":", lcd.line1)
        lcd.printString(str(Data) + " " + str(Unit), lcd.line2)
    
def DisplayAlert(Type, Msg):
    global DispAlert
    DispAlert = True
    lcd.printString("!ALERT!" + ":" + str(Type), lcd.line1)
    lcd.printString(str(Msg), lcd.line2)
    
def DisplayNextSensorData(gpio, level, tick): 
    global DispSen, DispSenNr, lastTick, DispAlert
    # entprellen:
    if DEBUG: print(pigpio.tickDiff(lastTick, tick))
    if (pigpio.tickDiff(lastTick, tick) > 500000):
        DispAlert = False # Bei Tastendruck verschwinden Alerts solange, bis ein neuer Alert angezeigt wird
        lcd.init() # Display neu initialisieren --> Anzeigefehler beheben
        DispSen.desubscribe()
        DispSenNr = (DispSenNr + 1) % len(SensorenList)
        DispSen = SensorenList[DispSenNr]()
        DispSen.subscribe(DisplaySensorData)
        lastTick = tick

# --------------------------
## --- Sensor-Metaklasse ---
# --------------------------

# Quelle: https://stackoverflow.com/questions/46237639/inheritance-of-class-variables-in-python
class SensorMeta(type):
    def __new__(cls, name, bases, attrs):
        
        new_class = super(SensorMeta, cls).__new__(cls, name, bases, attrs)

        # Initialisierungen (sollten nicht ueberschrieben werden):
        
        # In dieser Static Variable werden die zuletzt ausgelesenen Sensor-Daten gespeichert. Solange keine ausgelesen wurden: False
        new_class.SensorData = False
        
        # In dieser Static Variable werden Allert-Nachrichten als String gespeichert. Solange kein Alert vorliegt: False
        new_class.AlertMsg = False
        
        # In dieser Liste werden die Funktionen hinterlegt. die bei einem Alert aufgerufen werden.
        new_class.AlertSubscriber = []
        
        if new_class.REFRESH_TIME:
            new_class.RefreshTask = executor.submit(new_class._AutoRefresh)
        else:
            #refresh Sensor Data once at start
            new_class.Refresh()
                
        return new_class


# -------------------------------------
## --- abstrakte Sensor-Basisklasse ---
# -------------------------------------

class Sensor(metaclass=SensorMeta):
    """
    Abstrakte Basisklasse, die alle Methoden in Bezug zu den Sensoren implementiert. Fuer jeden Sensor sollte eine Klasse
    von dieser Klasse geerbt werden, die zumindest festlegt, welche Funktion zum Auslesen der Sensordaten aufgerufen werden muss.
    Bei jeder konkreter Sensorklasse muss der Name als Klassenattribut angegeben werden, unter welchem der Sensor angesprochen werden soll!
    """

    # ----------------------
    ## --Klassenattribute --
    # ----------------------

    # Diese Klassenatribute muessen auf konkreter Ebene ueberschrieben werden:
    NAME = "AbstrakteSensorklasse" # Gibt den Namen des Sensors an. Dieser wird als Key im Dict 'Sensoren' abgelegt
    REFRESH_TIME = False           # Nach dieser Zeit in Sekunden weden die Sensordaten erneut vom Sensor aktualisiert, wenn False nur einmal beim Start
    UNIT = "Einheit"               # Einheit der Sensordaten


    # ----------------------
    ## -- Klassenmethoden --
    # ----------------------

    @classmethod
    def ReadSensorData(cls):
        """
        muss in den erbenden Sensor-Klassen implementiert werden.
        Die Funktion muss die Sensordaten vom Sensor einlesen und als Reuckgabewert liefern
        """
        return False

    @classmethod
    def CheckAlerts(cls):
        """
        muss in den erbenden Sensor-Klassen implementiert werden.
        Die Funktion wird bei jedem Aktualisieren der Sensordaten aufgerufen.
        Sie muss die Sensordaten aus cls.SensorData auslesen und je nach gegebenen
        Bedingungen eine Alert-Nachricht oder False (kein Alert) zurückliefern.
        """
        return False


    @classmethod
    def Refresh(cls):
        if DEBUG: print("Reading Data from Sensor {}".format(cls.NAME))
        try:
            cls.SensorData = cls.ReadSensorData()
            cls.AlertMsg = cls.CheckAlerts()
        except Exception as e: #TODO: Exception-Handling verbessern
            print("ERROR while reading Data from Sensor {}: {}!".format(cls.NAME, e))
            cls.AlertMsg = "Error while reading Data from Sensor {}: {}!".format(cls.NAME, e)
        if cls.AlertMsg:                # Bei jedem Refresh werden, falls vorhanden, Alert-Nachrichten verschickt
            cls.Alert()

    @classmethod
    def SubscribeAlerts(cls, AlertOutput):
        cls.AlertSubscriber.append(AlertOutput)

    @classmethod
    def DesubscribeAlerts(cls, AlertOutput):
        cls.AlertSubscriber.remove(AlertOutput)

    @classmethod
    def Alert(cls):
        for Output in cls.AlertSubscriber:
            if DEBUG: print("Sending Alert {} to {}".format(cls.AlertMsg, Output))
            Output(cls.NAME, cls.GetAlert())

    @classmethod
    def GetAlert(cls):
            return cls.AlertMsg

    @classmethod
    def _AutoRefresh(cls):
        while Running:
            if DEBUG: print("Refreshing Sensor {} ...".format(cls.NAME))
            cls.Refresh()
            time.sleep(cls.REFRESH_TIME)

    # ---------------------
    ## -- Objektmethoden --
    # ---------------------

    def __init__(self):
        self.sub = False
        self.lastPubValue = None

    def __del__(self):
        if self.sub:
            self.sub = False

    def subscribe(self, Output, OnlyNew = True, time = False):
        """
        Die uebergebene Funktion "Output" muss drei Parameter annehmen: Type, Message, und Unit
        Es macht keinen Sinn, das Intervall "time" der Veroeffentlichungen kleiner zu waehlen
        als das Intervall, in dem die jeweiligen Sensordaten aktualisiert werden.
        Wenn OnlyNew True ist (Standard) werden nur neue Werte veroeffentlicht.
        """
        if not time:
            if type(self).REFRESH_TIME:
                # Wenn keine Zeit angegeben ist standardmaesig REFRESH-TIME als Intervall nehmen
                time = type(self).REFRESH_TIME
            else:
                # Wenn AutoRefresh deaktiviert ist (REFRESH-TIME = False)
                # und keine Zeit angegeben ist, Sensordaten nur einmal veroeffentlichen:
                Output(str(type(self).NAME), self.getSensorData(), str(type(self).UNIT))
                return
        
        t = float(time)
        if t < type(self).REFRESH_TIME or t > 3600:
            raise ValueError("Time out of Range ({} , 3600)".format(type(self).REFRESH_TIME))
        if self.sub == False:
            self.sub = True
            executor.submit(self._SendSensorData, Output, OnlyNew, t)
        else:
            raise ValueError("ERROR: Sensor already subscribed. One object of a sensor cannot be subscribed twice. Call 'desubscribe' first!")

    def desubscribe(self):
        self.sub = False

    def getSensorData(self, OnlyNew = False, Refresh = False):
        """
        Liefert den zuletzt ausgelesenen Wert des Sensors zurück.
        Parameter: (OnlyNew = False, Refresh = False)
                    |                 |
                    |                 -> Wenn True: Die Sensordaten werden zuvor neu vom Sensor aktualisiert
                    |                    Standard False: Die als Klassenattribut seit dem letzten Aufruf der Klassenfunktion
                    |                    "Refresh()" zwischengespeicherten Sensordaten werden ausgegeben
                    |
                    -> Wenn True: Es wird nur ein Rueckgabewert gegeben, falls die Sensordaten sich seit dem letzten Aufruf
                       der Methode verändert haben, andernfalls: False.
        """
        if Refresh: type(self).Refresh()    # Falls Refresh == True: Sensordaten vor der Rueckgabe aktualisieren
        Value = type(self).SensorData        # Das Klassen-Attribut "SensorData" in die lokale Variable "value" zwischenspeichern
        if (Value == self.lastPubValue and OnlyNew == True):
            return False
        else:
            self.lastPubValue = Value
            return Value

    def _SendSensorData(self, Output, OnlyNew, t):
        """
        Veroeffentlicht die Sensordaten wiederholt an die uebergebene 'Output(Name, SensorDaten, Einheit)'- Fkt
        time gibt die Zeit in Sekunden zwischend den Veroeffentlichungen an
        BEACHTEN: Es macht keinen Sinn, das Intervall der Veroeffentlichungen kleiner zu waehlen
                  als das Intervall, in dem die jeweiligen Sensordaten aktualisiert werden (REFRESH_TIME)!
        """
        while self.sub and Running:
            Data = self.getSensorData(OnlyNew)
            if Data: #TODO: Hier werden auch alle Werte abgefangen, die 0 sind!
                if DEBUG: print("Sending Sensor Data: {}".format(Data))
                Output(str(type(self).NAME),Data, str(type(self).UNIT))
            time.sleep(t)


# --------------------------------
## --- konkrete Sensor-Klassen ---
# --------------------------------

SHUNT_OHMS = 0.1
ina = ina219.INA219(SHUNT_OHMS)
ina.configure()

class INA219_Current(Sensor):
    NAME = "Current"
    REFRESH_TIME = 1
    UNIT = "A"
    e = False

    @classmethod
    def ReadSensorData(cls):
        try:
            return "{0:0.3f}".format(ina.current()/1000)
        except ina219.DeviceRangeError as e:
            cls.e = e
            print(e)
            
    @classmethod
    def CheckAlerts(cls):
        return cls.e
    
class INA219_Voltage(Sensor):
    NAME = "Voltage"
    REFRESH_TIME = 1
    UNIT = "V"
    e = False

    @classmethod
    def ReadSensorData(cls):
        try:
            return "{0:0.3f}".format(ina.voltage())
        except ina219.DeviceRangeError as e:
            cls.e = e
            print(e)
            
    @classmethod
    def CheckAlerts(cls):
        if cls.e:
            return cls.e
        if float(cls.SensorData) < 10:
            return "Low Volt. {} {}".format(cls.SensorData[0:4], cls.UNIT)
    
class INA219_Power(Sensor):
    NAME = "Power"
    REFRESH_TIME = 1
    UNIT = "W"
    e = False

    @classmethod
    def ReadSensorData(cls):
        try:
            return "{0:0.3f}".format(ina.power()/1000)
        except ina219.DeviceRangeError as e:
            cls.e = e
            print(e)
            
    @classmethod
    def CheckAlerts(cls):
        return cls.e

class IP_Addr(Sensor):
    NAME = "IP-Address"
    REFRESH_TIME = False
    UNIT = ""

    @classmethod
    def ReadSensorData(cls):
        cmdIP = "ip addr show wlan0 | grep inet | awk '{print $2}' | cut -d/ -f1"
        com = subprocess.Popen(cmdIP, shell=True, stdout=subprocess.PIPE)
        shellOutput = com.communicate()
        strIP = shellOutput[0].decode()
        IP = strIP.split('\n')[0]
        return IP
        


# Hier weitere konkrete Sensoren nach obigen Beispielen einfuegen...

# ---------------------------
## --- Initialisierungen ---
# ---------------------------

# Ein Dictionary, das den Namen aller Subklassen von "Sensor" als Key enthaelt und die jeweilige Klasse als Wert:
Sensoren = {}
# Alle Subklassen und das jeweils zugehoerige Klassenatrribut "NAME" werden automatisch in das obige Dictionary eingetragen:
for subcl in Sensor.__subclasses__():
    Sensoren[subcl.NAME] = subcl
# Zusätzlich eine SensorListe erstellen:
SensorenList = list(Sensoren.values())
# Display initialisieren:
lcd.init()
DispSenNr = 0
lastTick = 0
DispAlert = False
# Anfangs IP-Addr. anzeigen
DispSen = IP_Addr()
DispSen.subscribe(DisplaySensorData)
# Callback registrieren, um bei Knopfdruck den naechsten Sensor auf dem Display anzuzeigen:
b = pigpio.pi()          # pigpiod muss im Hintergrund laufen!
b.set_mode(20, pigpio.INPUT)
b.set_pull_up_down(20, pigpio.PUD_UP)
cb1 = b.callback(20, pigpio.RISING_EDGE, DisplayNextSensorData)
# Print all Allerts to StdOut:
for Sen in Sensoren:
    Sensoren[Sen].SubscribeAlerts(PrintAlerts)
    # Display all Alerts at Display:
    Sensoren[Sen].SubscribeAlerts(DisplayAlert)

# -------------
## --- Main ---
# -------------

if __name__ == "__main__":
    # Hier ergaenzen, was das Modul machen soll, wenn es direkt als Skript gestartet wird
    #for Sen in Sensoren:
    #    S = Sensoren[Sen]()
    #    S.subscribe(PrintSensorData, False) # subscribe all Sensors with default refresh time
    try:
        time.sleep(3600)
    finally:
       print("Cleaning up...")
       close()