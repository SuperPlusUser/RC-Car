#!/usr/bin/env python3

# Fake Modul, das auch auf anderen Geraeten ausser dem Raspberry Pi lauffaehig ist.
# Statt echter Sensordaten gibt es irgendwelche Phantasiewerte zurueck, die nur zu Testzwecken geeignet sind.


import time
import sys
import subprocess
import asyncio

DEBUG = True if "-d" in sys.argv else False

# ---------------------------
## --- globale Funktionen ---
# ---------------------------

def init(_loop):
    global loop, Sensoren, SensorenList, b, cb1
    loop = _loop
    # Ein Dictionary, das den Namen aller Subklassen von "Sensor" als Key enthaelt und die jeweilige Klasse als Wert:
    Sensoren = {}
    # Alle Subklassen und das jeweils zugehoerige Klassenatrribut "NAME" werden automatisch in das obige Dictionary eingetragen:
    for subcl in Sensor.__subclasses__():
        Sensoren[subcl.NAME] = subcl
    # Zusaetzlich eine SensorListe erstellen, ueber die iteriert werden kann:
    SensorenList = list(Sensoren.values())
    # Print all Allerts to StdOut:
    for Sen in Sensoren:
        Sensoren[Sen].SubscribeAlerts(PrintAlerts)
 
def close():
    print("Closing sensor module")

def PrintSensorData(Sensor, Data, Unit):
    print(str(Sensor), ":", str(Data) + " " + str(Unit))

def PrintAlerts(Type, Msg):
    print("! Alert from Sensor {} received: {} !".format(Type, Msg))

# --------------------------
## --- Sensor-Metaklasse ---
# --------------------------

# Quelle: https://stackoverflow.com/questions/46237639/inheritance-of-class-variables-in-python
class SensorMeta(type):
    def __new__(cls, name, bases, attrs):
        if DEBUG: print("creating Class {}".format(name))
        
        new_class = super(SensorMeta, cls).__new__(cls, name, bases, attrs)

        # Initialisierungen (sollten nicht ueberschrieben werden):
        # In dieser Static Variable werden die zuletzt ausgelesenen Sensor-Daten gespeichert. Solange keine ausgelesen wurden: False
        new_class.SensorData = False
        # In dieser Static Variable werden Allert-Nachrichten als String gespeichert. Solange kein Alert vorliegt: False
        new_class.AlertMsg = False
        # In dieser Liste werden die Funktionen hinterlegt. die bei einem Alert aufgerufen werden.
        new_class.AlertSubscriber = []

        if new_class.REFRESH_TIME:
            new_class.RefreshTask = asyncio.ensure_future(new_class._AutoRefresh())
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
        except Exception as e: #TODO: Exception-Handling verbessern
            print("ERROR while reading Data from Sensor {}: {}!".format(cls.NAME, e))
            cls.AlertMsg = "Error while reading Data from Sensor {}: {}!".format(cls.NAME, e)
        else:
            cls.AlertMsg = cls.CheckAlerts()
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
    async def _AutoRefresh(cls):
        while True:
            if DEBUG: print("Refreshing Sensor {} ...".format(cls.NAME))
            cls.Refresh()
            await asyncio.sleep(cls.REFRESH_TIME)

    # ---------------------
    ## -- Objektmethoden --
    # ---------------------

    def __init__(self):
        self.sub = False
        self.lastPubValue = None

    def __del__(self):
        if self.sub:
            self.sub.cancel()

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
        if t < type(self).REFRESH_TIME:
            if DEBUG: print("Time lower than refresh rate! Taking refresh rate instead.")
            t = type(self).REFRESH_TIME
        if self.sub == False:
            self.sub = asyncio.run_coroutine_threadsafe(self._SendSensorData(Output, OnlyNew, t), loop)
        else:
            raise ValueError("ERROR: Sensor already subscribed. One object of a sensor cannot be subscribed twice. Call 'desubscribe' first!")

    def desubscribe(self):
        if self.sub:
            self.sub.cancel()
            if DEBUG: print("Subscription cancelled")
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
            return None
        else:
            self.lastPubValue = Value
            return Value

    async def _SendSensorData(self, Output, OnlyNew, t):
        """
        Veroeffentlicht die Sensordaten wiederholt an die uebergebene 'Output(Name, SensorDaten, Einheit)'- Fkt
        time gibt die Zeit in Sekunden zwischend den Veroeffentlichungen an
        BEACHTEN: Es macht keinen Sinn, das Intervall der Veroeffentlichungen kleiner zu waehlen
                  als das Intervall, in dem die jeweiligen Sensordaten aktualisiert werden (REFRESH_TIME)!
        """
        while True:
            Data = self.getSensorData(OnlyNew)
            if Data is not None:
                if DEBUG: print("Sending Sensor Data: {}".format(Data))
                Output(str(type(self).NAME),Data, str(type(self).UNIT))
            await asyncio.sleep(t)


# --------------------------------
## --- konkrete Sensor-Klassen ---
# --------------------------------

class Sensor1(Sensor):
    NAME = "1"
    REFRESH_TIME = 10
    UNIT = "?"

    @classmethod
    def ReadSensorData(cls):
        return "xyz"

x = 0 # Initialisierung der Test-Variable fuer Sensor 2
class Sensor2(Sensor):
    NAME = "2"
    REFRESH_TIME = 10
    UNIT = "°C"

    @classmethod
    def ReadSensorData(cls):
        global x
        x+=1
        return x

    @classmethod
    def CheckAlerts(cls):
        #if int(cls.SensorData) > 10:
        #    return "Value of Sensor2 over 10: {}".format(cls.SensorData)
        #else:
        return False

class Sensor3(Sensor):
    NAME = "3"
    REFRESH_TIME = 10
    UNIT = "blub"

    @classmethod
    def ReadSensorData(cls):
        return "abc"

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

# -------------
## --- Main ---
# -------------

if __name__ == "__main__":
    # Hier ergaenzen, was das Modul machen soll, wenn es direkt als Skript gestartet wird
    loop = asyncio.get_event_loop()
    init(loop)
    for Sen in Sensoren:
        S = Sensoren[Sen]()
        S.subscribe(PrintSensorData, False) # subscribe all Sensors with default refresh time
    try:
        loop.run_forever()
    finally:
        print("Cleaning up...")
        close()
