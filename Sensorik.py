#!/usr/bin/env python3

## Version 0.2.5
#
## Changelog:
#
# --- 0.2.5 ---
# - asyncio.ensure_future statt loop.create_task
# - SensorMeta hinzugefuegt --> Problem mit Vererbung von Klassen-Variablen geloest
# 

## TODO:
# - Eventuell Beobachter-Entwurfsmuster implementieren
# - Kommentierung und Exception-Handling verbessern


import asyncio
import sys

DEBUG =True if "-d" in sys.argv else False

# Quelle: https://stackoverflow.com/questions/46237639/inheritance-of-class-variables-in-python
class SensorMeta(type):
    def __new__(cls, name, bases, attrs):
        new_class = super(SensorMeta, cls).__new__(cls, name, bases, attrs)
        
        # Initialisierungen (sollten nicht ueberschrieben werden):
        new_class.SensorDat = False   # In dieser Static Variable werden die zuletzt ausgelesenen Sensor-Daten gespeichert. Solange keine ausgelesen wurden: False
        new_class.AlertMsg = False    # In dieser Static Variable werden Allert-Nachrichten als String gespeichert. Solange kein Alert vorliegt: False
        new_class.AlertSubscriber = []# In dieser Liste werden die Funktionen hinterlegt. die bei einem Alert aufgerufen werden.
        if new_class.REFRESH_TIME:
            new_class.RefreshTask = asyncio.ensure_future(new_class._AutoRefresh())

        return new_class


class Sensor(metaclass=SensorMeta):
    """
    Abstrakte Basisklasse, die alle Methoden in Bezug zu den Sensoren implementiert. Für jeden Sensor sollte eine Klasse
    von dieser Klasse geerbt werden, die zumindest festlegt, welche Funktion zum Auslesen der Sensordaten aufgerufen werden muss.
    Bei jeder konkreter Sensorklasse muss der Name als Klassenattribut angegeben werden, unter welchem der Sensor angesprochen werden soll!
    """

    # Diese Klassenatribute muessen auf konkreter Ebene ueberschrieben werden:
    NAME = "AbstrakteSensorklasse" # Gibt den Namen des Sensors an. Dieser wird als Key im Dict 'Sensoren' abgelegt
    REFRESH_TIME = False    # Nach dieser Zeit in Sekunden weden die Sensordaten erneut vom Sensor aktualisiert
    
    @classmethod
    def ReadSensorDat(cls):
        """
        muss in den erbenden Sensor-Klassen implementiert werden.
        Die Funktion muss die Sensordaten vom Sensor einlesen und als Reuckgabewert liefern
        """
        return 0

    @classmethod
    def CheckAlerts(cls):
        """
        muss in den erbenden Sensor-Klassen implementiert werden.
        Die Funktion wird bei jedem Aktualisieren der Sensordaten aufgerufen.
        Sie muss die Sensordaten aus cls.SensorDat auslesen und je nach gegebenen
        Bedingungen eine Alert-Nachricht oder False (kein Alert) zurückliefern.
        """
        return False

    @classmethod
    def Refresh(cls):
        if DEBUG: print("Reading Data from Sensor {}".format(cls.NAME))
        cls.SensorDat = cls.ReadSensorDat()
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
            cls.Refresh()
            await asyncio.sleep(cls.REFRESH_TIME)


    def __init__(self):
        self.sub = False
        self.lastPubValue = None

    def __del__(self):
        if self.sub:
            self.sub.cancel()

    def subscribe(self, Output, time = False):
        """
        Die uebergebene Funktion "Output" muss zwei Parameter annehmen: Type und Message
        Es macht keinen Sinn, das Intervall "time" der Veroeffentlichungen kleiner zu waehlen
        als das Intervall, in dem die jeweiligen Sensordaten aktualisiert werden
        """
        if not time:
            time = type(self).REFRESH_TIME
        t = float(time)
        if t < type(self).REFRESH_TIME or t > 3600: 
            raise ValueError("Time out of Range ({} , 3600)".format(type(self).REFRESH_TIME))
        if self.sub == False:
            self.sub = asyncio.ensure_future(self._SendSensorDat(Output, t))
        else:
            raise ValueError("ERROR: Sensor already subscribed. One object of a sensor cannot be subscribed twice. Call 'desubscribe' first!")

    def desubscribe(self):
        if self.sub:
            self.sub.cancel()
            self.sub = False

    def getSensorDat(self, OnlyNew = False, Refresh = False):
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
        Value = type(self).SensorDat        # Das Klassen-Attribut "SensorDat" in die lokale Variable "value" zwischenspeichern
        if Value == self.lastPubValue and OnlyNew: return False
        else: 
            self.lastPubValue = Value
            return Value

    async def _SendSensorDat(self, Output, time):
        """
        Veroeffentlicht die Sensordaten wiederholt an die uebergebene 'Output(Name, SensorDaten)'- Fkt
        time gibt die Zeit in Sekunden zwischend den Veroeffentlichungen an
        BEACHTEN: Es macht keinen Sinn, das Intervall der Veroeffentlichungen kleiner zu waehlen
                  als das Intervall, in dem die jeweiligen Sensordaten aktualisiert werden (REFRESH_TIME)!
        """
        while True:
            Dat = self.getSensorDat(True) # Nur neue Werte veroeffentlichen
            if Dat:
                if DEBUG: print("Sending Sensor Data: {}".format(Dat))
                Output(str(type(self).NAME),Dat) 
            await asyncio.sleep(time)


# ------------------------------------------------
#       konkrete Sensor-Klassen:
# ------------------------------------------------

class Sensor1(Sensor):
    NAME = "1"
    REFRESH_TIME = 1
    
    @classmethod
    def ReadSensorDat(cls):
        return "xyz"

x = 0 # Initialisierung der Test-Variable für Sensor 2
class Sensor2(Sensor):
    NAME = "2"
    REFRESH_TIME = 2
    
    @classmethod
    def ReadSensorDat(cls):
        global x
        x+=1
        return x

    @classmethod
    def CheckAlerts(cls):
        if int(cls.SensorDat) > 10:
            return "Value of Sensor2 over 10: {}".format(cls.SensorDat)
        else: return False

class Sensor3(Sensor):
    NAME = "3"
    REFRESH_TIME = 5
    
    @classmethod
    def ReadSensorDat(cls):
        return "abc"
    
    @classmethod
    def CheckAlerts(cls):
        return "TEST Alert"
        
# Hier weitere konkrete Sensoren nach obigen Beispielen einfuegen...




## Initialisierungen:

# Ein Dictionary, das den Namen aller Subklassen von "Sensor" als Key enthält und die jeweilige Klasse als Wert:
Sensoren = {}
# Alle Subklassen und das jeweils zugehörige Klassenatrribut "name" werden automatisch in das obige Dictionary eingetragen:
for subcl in Sensor.__subclasses__():
    Sensoren[subcl.NAME] = subcl
    
# Print all Alerts to StdOut:
def PrintAlerts(Type, Msg):
    print("! Alert from Sensor {} received: {} !".format(Type, Msg))
    
for Sen in Sensoren:
    Sensoren[Sen].SubscribeAlerts(PrintAlerts)


if __name__ == "__main__":
    # Hier ergaenzen, was das Modul machen soll, wenn es direkt als Skript gestartet wird:
    print("This Module is currently not intended to be started as a script! Exiting...")
