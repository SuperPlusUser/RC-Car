#!/usr/bin/env python3

## Version 0.7
#
## Changelog:
#
# --- 0.7 ---
# - Bremsassistent testweise eingebaut (Voraussetzung: Steuerung.py Version 0.3)
#
# --- 0.6.1 ---
# - Bug behoben, der dafuer sorgte, dass 0 (=False) nicht als Sensor-Messwert ausgegeben wurde.
#
# --- 0.6 ---
# - zweiten Entfernungs-Sensor eingebaut
# - Buzzer eingebaut
# - weitere kleiene Optimierungen und Fehlerkorrekturen
#
# --- 0.5.3 ---
# - Ein paar Dinge vereinfacht.
# - Beim Subscriben werden nun alle Sensorwerte als String an die Output-Funktion weitergegeben.
#
# --- 0.5.2 ---
# - Bug behoben, der dafuer sorgt, dass beim wegklicken eines Alerts, sinnlose Zeichen im Display erscheinen.
# - Beim Wegklicken eines Alerts wird danach der zuvor ausgewaehlte Sensor weiter angezeigt.
#
# --- 0.5.1 ---
# - Bugfix bei den Alerts: gleiche Alerts des selben Sensors werden nun erneut ausgegeben, fals der Alert erneut auftritt.
# - Sensoren DHT22 und BMP180 hinzugefuegt
# - Sonar Sensor Front aktiviert
#
# --- 0.5 ---
# - Verbindung zum BattMon verbessert
# --> Verbindung wird nach abbruch automatisch neu aufgebaut
# --> weniger Wartezeit am Anfang
# --> Verbindungsabbruch wird erkannt und eine Alert-Meldung wird generiert
# - Sensoren "Motor-Speed" und "Lenk-Position" hinzugefuegt
# - Sensor "Motor-Temp." hinzugefuegt.
# - Beim Beenden des Skripts wird besser aufgeraeumt und es treten keine weiteren Exceptions mehr auf.
#
# --- 0.4.3 ---
# - Kommentierung verbessert
# - INA219 entfernt (Ersetzt durch Battery Monitor)
# - Alerts hinzugefuegt
#
# --- 0.4.2 ---
# - Batt_Mon eingefuegt (alpha)
# - Standardwerte fuer Sensordaten und Alerts in "None" statt "False" geaendert
#
# --- 0.4.1 ---
# - Sensoren werden in eigenen Threads aktualisiert --> loop wird nicht blokiert
# - Ultraschall-Sensor mit eingebaut
#
# --- 0.4 ---
# - kopiert von Sensorik
# - Alles auf Asyncio loop umgestellt
# - Display eingabaut, welches bei Tastendruck die naechsten Sensordaten anzeigt
#

## TODO:
# - Severity bei Alerts einbauen!


import time
import sys
from concurrent.futures import ThreadPoolExecutor
executor = ThreadPoolExecutor(max_workers = 5) # max_workers erhoehen bei Problemen?
import pigpio
import subprocess
import asyncio
import serial
import sonar
import lcd
import Adafruit_DHT
import Adafruit_BMP.BMP085

import Steuerung

DEBUG = True if "-d" in sys.argv else False

EN_BRAKE_ASSIST = True    # Bremsassistent aktivieren (=True) / deaktivieren (=False)
DISP_BUTTON = 20
BUZZER_PIN = 25
BUZZER_FREQ = 800
pi = pigpio.pi()          # pigpiod muss im Hintergrund laufen!


# ---------------------------
## --- globale Funktionen ---
# ---------------------------

def init(_loop):
    global loop, Sensoren, SensorenList, pi, cb1, shutdown, DispAlert
    shutdown = False
    loop = _loop
    # Solange das Display nicht initialisiert ist, keine Alerts darstellen:
    DispAlert = True
    # Ein Dictionary, das den Namen aller Subklassen von "Sensor" als Key enthaelt und die jeweilige Klasse als Wert:
    Sensoren = {}
    # Alle Subklassen und das jeweils zugehoerige Klassenatrribut "NAME" werden automatisch in das obige Dictionary eingetragen:
    for subcl in Sensor.__subclasses__():
        Sensoren[subcl.NAME] = subcl
    # Zusaetzlich eine SensorListe erstellen, ueber die iteriert werden kann:
    SensorenList = list(Sensoren.values())   
    
    for Sen in Sensoren:
        # Start Refresh-Tasks:
        Sensoren[Sen]._AutoRefresh()
        # Print all Alerts to StdOut:
        Sensoren[Sen].SubscribeAlerts(PrintAlerts)
        # Display all Alerts at Display:
        Sensoren[Sen].SubscribeAlerts(DisplayAlert)
        
    # kurz warten, bis die IP-Adresse ausgelesen ist:
    time.sleep(1)
    # Display initialisieren:
    init_disp(loop)
    # Callback registrieren, um bei Knopfdruck den naechsten Sensor auf dem Display anzuzeigen:
    pi.set_mode(DISP_BUTTON, pigpio.INPUT)
    pi.set_pull_up_down(DISP_BUTTON, pigpio.PUD_UP)
    cb1 = pi.callback(DISP_BUTTON, pigpio.FALLING_EDGE, DisplayNextSensorData)
    # GPIO des Buzzers konfigurieren:
    pi.set_mode(BUZZER_PIN, pigpio.OUTPUT)
    pi.set_PWM_frequency(BUZZER_PIN, BUZZER_FREQ)
    pi.set_PWM_range(BUZZER_PIN, 100)
    pi.set_PWM_dutycycle(BUZZER_PIN, 0)
    
    #Starte LED-Beleuchtung in Mode 0:
    Steuerung.light.change_mode(mode = 0)

def init_disp(loop):
    global DispSenNr, DispSen, lastTick, DispAlert
    loop.run_until_complete(lcd.init())
    DispSenNr = 0
    lastTick = 0
    DispAlert = False
    #Anfangs IP-Addr anzeigen:
    DispSen = IP_Addr()
    DispSen.subscribe(DisplaySensorData)
    
def close():
    global shutdown
    shutdown = True
    for Sen in Sensoren:
        # Desubscribe Alerts to StdOut:
        Sensoren[Sen].DesubscribeAlerts(PrintAlerts)
        # Desubscribe Alerts at Display:
        Sensoren[Sen].DesubscribeAlerts(DisplayAlert)
    executor.shutdown(wait=True)
    cb1.cancel()
    loop.run_until_complete(lcd.init())
    loop.run_until_complete(lcd.clear())
    loop.run_until_complete(lcd.setBacklightOff())
    Sonar_Sensor_Front.son.cancel()
    Sonar_Sensor_Rear.son.cancel()
    pi.set_PWM_dutycycle(BUZZER_PIN, 0)
    pi.stop()

def PrintSensorData(Sensor, Data, Unit):
    print(str(Sensor), ":", str(Data) + " " + str(Unit))

def PrintAlerts(Type, Msg):
    print("! Alert from Sensor {} received: {} !".format(Type, Msg))

def DisplaySensorData(Sensor, Data, Unit):
    if not DispAlert: #Alerets haben Vorrang
        asyncio.run_coroutine_threadsafe(lcd.printString(str(Sensor) + ":", lcd.line1), loop)
        asyncio.run_coroutine_threadsafe(lcd.printString(str(Data) + " " + str(Unit), lcd.line2), loop)

def DisplayAlert(Type, Msg):   
    global DispAlert
    if not DispAlert: #Alerts nur einmal anzeigen --> verhindert ein "ueberfordern" des Displays
        asyncio.run_coroutine_threadsafe(lcd.printScrollingString("!ALERT!" + ":" + str(Type), str(Msg)), loop)
        # light-mode auf -1 (Alert) stellen:
        Steuerung.light.change_mode(mode = -1)
        DispAlert = True

#Callback function fuer Button:
def DisplayNextSensorData(gpio, level, tick): 
    global DispSen, DispSenNr, lastTick, DispAlert
    # entprellen:
    if DEBUG: print(pigpio.tickDiff(lastTick, tick))
    if (pigpio.tickDiff(lastTick, tick) > 500000):
        lcd.stop_scrolling = True # Falls im Display gerade ein langer Text durchscrollt, dies unterbrechen.
        if DispAlert:
            DispAlert = False # Bei Tastendruck verschwinden Alerts solange, bis ein neuer Alert angezeigt wird
            DisplaySensorData(DispSen.NAME, DispSen.SensorData, DispSen.UNIT)
            Steuerung.light.change_mode(mode = 0)
        else:
            DispSen.desubscribe()
            DispSenNr = (DispSenNr + 1) % len(SensorenList)
            DispSen = SensorenList[DispSenNr]()
            DispSen.subscribe(DisplaySensorData, True, 0.5)
        lastTick = tick

# --------------------------
## --- Sensor-Metaklasse ---
# --------------------------

# Quelle: https://stackoverflow.com/questions/46237639/inheritance-of-class-variables-in-python
class SensorMeta(type):
    def __new__(cls, name, bases, attrs):
        if DEBUG: print("creating Class {}".format(name))
        
        new_class = super(SensorMeta, cls).__new__(cls, name, bases, attrs)

        # Initialisierungen (sollten nicht ueberschrieben werden):
        # In dieser Static Variable werden die zuletzt ausgelesenen Sensor-Daten gespeichert. Solange keine ausgelesen wurden: None
        new_class.SensorData = None
        # In dieser Static Variable werden Alert-Nachrichten als String gespeichert. Solange kein Alert vorliegt: None
        new_class.AlertMsg = None
        # In dieser Liste werden die Funktionen hinterlegt. die bei einem Alert aufgerufen werden.
        new_class.AlertSubscriber = []
                
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
        return None

    @classmethod
    def CheckAlerts(cls):
        """
        muss in den erbenden Sensor-Klassen implementiert werden.
        Die Funktion wird bei jedem Aktualisieren der Sensordaten aufgerufen.
        Sie muss die Sensordaten aus cls.SensorData auslesen und je nach gegebenen
        Bedingungen eine Alert-Nachricht oder False (kein Alert) zurueckliefern.
        """
        return False


    @classmethod
    def Refresh(cls):
        if DEBUG: print("Reading Data from Sensor {}".format(cls.NAME))
        try:
            cls.SensorData = cls.ReadSensorData()
        except Exception as e: #TODO: Exception-Handling verbessern
            print("ERROR while reading Data from Sensor {}: {}!".format(cls.NAME, e))
            cls.NewAlertMsg = "Error while reading Data from Sensor {}: {}!".format(cls.NAME, e)
        else:
            cls.NewAlertMsg = cls.CheckAlerts()
        if cls.NewAlertMsg != cls.AlertMsg: # nur neue Alerts
            # Bei jedem Refresh werden, falls vorhanden, neue Alert-Nachrichten verschickt
            cls.AlertMsg = cls.NewAlertMsg
            if cls.AlertMsg: cls.Alert()

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
        if not shutdown:
            cls.RefreshTask = loop.run_in_executor(executor, cls.Refresh)
            if cls.REFRESH_TIME:
                # schedule next Refresh if REFRESH_TIME is not False:
                cls.NextRefresh = loop.call_later(cls.REFRESH_TIME, cls._AutoRefresh)

    # ---------------------
    ## -- Objektmethoden --
    # ---------------------

    def __init__(self):
        self._sub = False
        self.lastPubValue = None

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
        self._sub = True
        self._SendSensorData(Output, OnlyNew, t)

    def desubscribe(self):
        self._sub = False

    def getSensorData(self, OnlyNew = False, Refresh = False):
        """
        Liefert den zuletzt ausgelesenen Wert des Sensors zurueck.
        Parameter: (OnlyNew = False, Refresh = False)
                    |                 |
                    |                 -> Wenn True: Die Sensordaten werden zuvor neu vom Sensor aktualisiert
                    |                    Standard False: Die als Klassenattribut seit dem letzten Aufruf der Klassenfunktion
                    |                    "Refresh()" zwischengespeicherten Sensordaten werden ausgegeben
                    |
                    -> Wenn True: Es wird nur ein Rueckgabewert gegeben, falls die Sensordaten sich seit dem letzten Aufruf
                       der Methode veraendert haben, andernfalls: None.
        """
        if Refresh: type(self).Refresh()    # Falls Refresh == True: Sensordaten vor der Rueckgabe aktualisieren
        Value = type(self).SensorData        # Das Klassen-Attribut "SensorData" in die lokale Variable "value" zwischenspeichern
        if (Value == self.lastPubValue and OnlyNew == True):
            return None
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
        Data = self.getSensorData(OnlyNew)
        if self._sub and not shutdown:
            if not Data == None:
                if DEBUG: print("Sending Sensor Data: {}".format(Data))
                Output(str(type(self).NAME), str(Data), str(type(self).UNIT))
            self.NextSendTask = loop.call_later(t, self._SendSensorData, Output, OnlyNew, t)


# --------------------------------
## --- konkrete Sensor-Klassen ---
# --------------------------------

# -- Battery Monitor --
class Batt_Mon:
    REFRESH_TIME = 1 # wird eigentlich durch Batt_Mon (Arduino) vorgegeben, muss hier nur als default subscribe-Zeit angegeben werden!
    RefreshTask = None

    @classmethod
    def ConnectToBattMon(cls):
        i = 0
        while i <= 5:
            try:
                print("trying to connect to /dev/ttyUSB{}".format(i))
                cls.ser = serial.Serial('/dev/ttyUSB{}'.format(i), 9600, timeout=2)
                i = 10 # Damit die Schleife verlassen wird, falls keine Exception auftritt.
            except serial.serialutil.SerialException:
                i += 1

        if i == 6:
            print("ERROR: Could not connect to BattMon")
            for subcls in cls.__subclasses__():
                subcls.NewAlertMsg = "Could not connect to BattMon"
                if subcls.AlertMsg != subcls.NewAlertMsg:
                    subcls.AlertMsg = subcls.NewAlertMsg
                    subcls.Alert()
                
            # try again to connect to BattMon after 5 sec:
            if not shutdown:
                Batt_Mon.ConnectTask = loop.call_later(5, Batt_Mon.ConnectToBattMon)
        elif i == 10:
            print("Successfully connected to BattMon")
            Batt_Mon.RefreshTask = loop.run_in_executor(executor, Batt_Mon.ReadSerial)


    @classmethod
    def ReadSerial(cls):
        time.sleep(5) # Wait until Arduino rebooted
        cls.ser.write(b'start')
        while cls.ser.is_open and not shutdown:
            try:
                cls.SensorData = cls.ser.readline() # blokiert solange bis eine neue Zeile empfangen wurde
                cls.ser.reset_input_buffer()        # Sichergehen, dass nur neue Werte gelesen werden
                for subcls in cls.__subclasses__():
                    subcls.Refresh()
            except serial.serialutil.SerialException as e:
                print(e)
                break
        cls.ser.close()
        if not shutdown:
            for subcls in cls.__subclasses__():
                subcls.NewAlertMsg = "Connection to BattMon lost"
                if subcls.AlertMsg != subcls.NewAlertMsg:
                    subcls.AlertMsg = subcls.NewAlertMsg
                    subcls.Alert()
            # try again to connect to BattMon after 5 sec:
            Batt_Mon.ConnectTask = loop.call_later(5, Batt_Mon.ConnectToBattMon)

    @classmethod
    def _AutoRefresh(cls):
        if not Batt_Mon.RefreshTask and not shutdown:
            Batt_Mon.RefreshTask = True
            Batt_Mon.ConnectTask = loop.call_later(5, Batt_Mon.ConnectToBattMon)


class Batt_Mon_Voltage(Batt_Mon, Sensor):
    NAME = "Batt.-Voltage"
    UNIT = "V"
    #REFRESH_TIME wird durch Batt_Mon vorgegeben!

    @classmethod
    def ReadSensorData(cls):
        Start = Batt_Mon.SensorData.find(b'V: ') + 3
        End = Batt_Mon.SensorData.find(b',', Start)
        return float(Batt_Mon.SensorData[Start : End].decode())
            
    @classmethod
    def CheckAlerts(cls):
        if cls.SensorData < 9.5:
            return "Low Voltage"
        else:
            return False
    
class Batt_Mon_Current(Batt_Mon, Sensor):
    NAME = "Batt.-Current"
    UNIT = "A"
    #REFRESH_TIME wird durch Batt_Mon vorgegeben!

    @classmethod
    def ReadSensorData(cls):
        Start = Batt_Mon.SensorData.find(b'A: ') + 3
        End = Batt_Mon.SensorData.find(b',', Start)
        return float(Batt_Mon.SensorData[Start : End].decode())

    @classmethod
    def CheckAlerts(cls):
        if abs(cls.SensorData) > 5:
            return "High Current"
        else:
            return False
    
class Batt_Mon_Charge(Batt_Mon, Sensor):
    NAME = "Batt.-Charge"
    UNIT = "mAh"
    #REFRESH_TIME wird durch Batt_Mon vorgegeben!

    @classmethod
    def ReadSensorData(cls):
        Start = Batt_Mon.SensorData.find(b'C: ') + 3
        End = Batt_Mon.SensorData.find(b',', Start)
        return float(Batt_Mon.SensorData[Start : End].decode())

    @classmethod
    def CheckAlerts(cls):
        if cls.SensorData < 500:
            return "Low Charge"
        else:
            return False

class Batt_Mon_Temp(Batt_Mon, Sensor):
    NAME = "Batt.-Temp"
    UNIT = "°C"
    #REFRESH_TIME wird durch Batt_Mon vorgegeben!

    @classmethod
    def ReadSensorData(cls):
        Start = Batt_Mon.SensorData.find(b'T: ') + 3
        End = Batt_Mon.SensorData.find(b'\r', Start)
        return float(Batt_Mon.SensorData[Start : End].decode())
            
    #@classmethod
    #def CheckAlerts(cls):
    
    
class IP_Addr(Sensor):
    """virtueller Sensor, der die IP-Adresse der WLAN-Schnittstelle zurueckgiebt."""
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


class Sonar_Sensor_Front(Sensor):
    NAME = "Distance Front"
    REFRESH_TIME = 0.4
    UNIT = "cm"

    SONAR_TRIGGER = 19
    SONAR_ECHO = 13
    son = sonar.ranger(pi, SONAR_TRIGGER, SONAR_ECHO)
    i = 0
    EN_BUZZER = True

    beep = False
    brake = False

    @classmethod
    def ReadSensorData(cls):
        data = float("{0:0.1f}".format(cls.son.read()))
        if data > 0: return data
        else: return cls.SensorData

    @classmethod
    def CheckAlerts(cls):
        global RearBeep
        
        if cls.SensorData < 10:
            msg = "Crash!"
            if cls.EN_BUZZER: cls.i = 3
            if EN_BRAKE_ASSIST:
                # weiteres Vorwaertsfahren unterbinden
                Steuerung.set_speed_limit(0, "forward")
                if not cls.brake:
                    # nur einmal bremsen, ansonsten kommt man nicht mehr vom Fleck
                    Steuerung.brake()
                    cls.brake = True
                
            
        elif cls.SensorData < 25:
            msg = "close Obstacle!"
            if cls.EN_BUZZER: cls.i += 2
            if EN_BRAKE_ASSIST:
                # Geschwindigkeit auf 20% limitieren
                Steuerung.set_speed_limit(20, "forward")
                if not cls.brake:
                    # nur einmal bremsen, ansonsten kommt man nicht mehr vom Fleck
                    Steuerung.brake()
                    cls.brake = True
            
        elif cls.SensorData < 50:
            msg = "distant Obstacle"
            if cls.EN_BUZZER: cls.i += 1
            if EN_BRAKE_ASSIST:
                # Geschwindigkeit auf 50% limitieren
                Steuerung.set_speed_limit(50, "forward")
                if not cls.brake:
                    # nur einmal bremsen, ansonsten kommt man nicht mehr vom Fleck
                    Steuerung.brake()
                    cls.brake = True
            
        else:
            msg = False
            cls.i = 0
            if EN_BRAKE_ASSIST:
                # Bremsen wieder erlauben und Speedlimt zuruecksetzen
                cls.brake = False
                Steuerung.set_speed_limit(100, "forward")

        if cls.EN_BUZZER:
            if cls.i >= 3:
                pi.set_PWM_dutycycle(BUZZER_PIN, 50) #Beep
                cls.i = 0
                cls.beep = True
            elif cls.beep:
                pi.set_PWM_dutycycle(BUZZER_PIN, 0) #Buzzer aus
                cls.beep = False

        return msg


class Sonar_Sensor_Rear(Sensor):
    NAME = "Distance Rear"
    REFRESH_TIME = 0.4
    UNIT = "cm"

    SONAR_TRIGGER = 23
    SONAR_ECHO = 24
    son = sonar.ranger(pi, SONAR_TRIGGER, SONAR_ECHO)
    i = 0
    EN_BUZZER = True

    beep = False

    @classmethod
    def ReadSensorData(cls):
        data = float("{0:0.1f}".format(cls.son.read()))
        if data > 0: return data
        else: return cls.SensorData

    @classmethod
    def CheckAlerts(cls):
        global RearBeep
        if cls.SensorData < 10:
            msg = "Crash!"
            if cls.EN_BUZZER: cls.i = 3
        elif cls.SensorData < 25:
            msg = "close Obstacle!"
            if cls.EN_BUZZER: cls.i += 2
        elif cls.SensorData < 50:
            msg = "distant Obstacle"
            if cls.EN_BUZZER: cls.i += 1
        else:
            msg = False
            if cls.EN_BUZZER: cls.i = 0

        if cls.EN_BUZZER:
            if cls.i >= 3:
                pi.set_PWM_dutycycle(BUZZER_PIN, 50) #Beep
                cls.i = 0
                cls.beep = True
            elif cls.beep:
                pi.set_PWM_dutycycle(BUZZER_PIN, 0) #Buzzer aus
                cls.beep = False

        return msg


class DS18B20_1(Sensor):
    NAME = "Motor-Temp."
    UNIT = "°C"
    REFRESH_TIME = 3

    SLAVE_NAME = "10-000802015d01"

    @classmethod
    def ReadSensorData(cls):
        file = open('/sys/bus/w1/devices/' + cls.SLAVE_NAME + '/w1_slave')
        filecontent = file.read()
        file.close()
        stringvalue = filecontent.split("\n")[1].split(" ")[9]
        crcvalue = filecontent.split("\n")[0].split(" ")[11]
        if crcvalue == "YES" and stringvalue != "t=85000": # 85°C wird oft bei Lesefehlern ausgegeben
            temperature = float("{0:0.1f}".format(float(stringvalue[2:]) / 1000))
            return temperature
        else:
            return cls.SensorData # alten Sensorwert zurueckgeben, falls ein Auslesefehler aufgetreten ist
        
    @classmethod
    def CheckAlerts(cls):
        if cls.SensorData > 60:
            return "High Motor Temp."
        else:
            return False

class DHT22_Temp(Sensor):
    NAME = "Aussen-Temp"
    UNIT = "°C"
    REFRESH_TIME = 10
    
    sensor = Adafruit_DHT.DHT22
    gpio = 6
    
    @classmethod
    def ReadSensorData(cls):
        humidity, temperature = Adafruit_DHT.read_retry(cls.sensor, cls.gpio)
        # DHT22_Hum wird hier gleich mit aktualisiert
        DHT22_Hum.SensorData = float("{0:0.1f}".format(humidity))
        return float("{0:0.1f}".format(temperature))
    
class DHT22_Hum(Sensor):
    NAME = "Luftfeuchtigkeit"
    UNIT = "%"
    REFRESH_TIME = 10 # Der Sensor wird eigentlich durch die Klasse DHT22_Temp mit aktualisiert,
    # die Refresh-Time muss hier nur als Default-Subscribe-Zeit angegeben werden.
    
    @classmethod
    def ReadSensorData(cls):
        return cls.SensorData # wird durch DHT22_Temp festgelegt

# --- BMP058 ---
bmp = Adafruit_BMP.BMP085.BMP085()

class BMP085_Pressure(Sensor):
    NAME = "Luftdruck"
    UNIT = "hPa"
    REFRESH_TIME = 10
    
    @classmethod
    def ReadSensorData(cls):
        pressure = bmp.read_pressure()
        return float("{0:0.1f}".format(pressure)) / 100
        
    
class BMP_Altitude(Sensor):
    NAME = "Hoehe"
    UNIT = "m"
    REFRESH_TIME = 10
    
    @classmethod
    def ReadSensorData(cls):
        altitude = bmp.read_altitude()
        return float("{0:0.1f}".format(altitude))

class Mtr_Speed(Sensor):
    NAME = "Motor-Speed"
    UNIT = "%"
    REFRESH_TIME = 0.5

    @classmethod
    def ReadSensorData(cls):
        return Steuerung.get_speed()
    
class Lnk_Pos(Sensor):
    NAME = "Lenk-Position"
    UNIT = ""
    REFRESH_TIME = 0.5

    @classmethod
    def ReadSensorData(cls):
        return Steuerung.get_pos()


# ... Hier weitere konkrete Sensoren nach obigen Beispielen einfuegen ...




# -------------
## --- Main ---
# -------------

if __name__ == "__main__":
    # Hier ergaenzen, was das Modul machen soll, wenn es direkt als Skript gestartet wird
    loop = asyncio.get_event_loop()
    init(loop)
    if DEBUG:
        # Enable Debugging mode of asyncio:
        loop.set_debug(True)
        import logging
        logging.basicConfig(level=logging.DEBUG)
    for Sen in Sensoren:
        S = Sensoren[Sen]()
        S.subscribe(PrintSensorData, False) # subscribe all Sensors with default refresh time
    try:
        loop.run_forever()
    finally:
        print("Cleaning up...")
        close()
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
