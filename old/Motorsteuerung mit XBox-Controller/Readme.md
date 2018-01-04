Skript zur grundlegenden Steuerung des Autos mit dem XBox 360 Wireless Controller.

-------- INSTALLATION ------------------------------------

"xboxdrv" installieren:
	sudo apt-get install xboxdrv

Testen ob Treiber korrekt installiert ist:
	sudo xboxdrv --detach-kernel-driver

	... Mehr siehe https://github.com/FRC4564/Xbox ...

Falls notwendig: "python3-rpi.gpio"-Paket installieren (ist standardmäßig nur für Python2 installiert?):
	sudo apt install python3-rpi.gpio
	

-------- START -------------------------------------------

Skript.py auf dem Raspberry Pi mit root-Rechten starten:
	sudo python3 Skript.py

------- STEUERUNG ----------------------------------------

Beschleunigung:				rechter Trigger
Rückwärts:				linker Trigger
Lenkung:				linker Analogstick
Bremsen (Motor "kurzschließen"): 	B
Skript Beenden:				"Strg" + C oder "Start" und "Back"



-------- BEIM BEARBEITEN BEACHTEN! -----------------------

Bei Python müssen die Einrückungen einheitlich vorgenommen werden, entweder mit Leerzeichen oder mit Tabs! Ansonsten kommt bei der Ausführung eine Fehlermeldung.

Im Skript.py sind die Einrückungen mit Tabs realisiert.

Um zu überprüfen ob die Einrückungen einheitlich sind, können bei Notepad++ unter "Ansicht", "Nicht druckbare Zeichen" Leerzeichen und Tabulatoren angezeigt werden.

------- QUELLEN ------------------------------------------

https://sourceforge.net/p/raspberry-gpio-python/wiki/PWM/
https://github.com/FRC4564/Xbox


