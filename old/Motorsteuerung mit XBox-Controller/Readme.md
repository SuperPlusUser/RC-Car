Skript zur grundlegenden Steuerung des Autos mit dem XBox 360 Wireless Controller.

-------- INSTALLATION ------------------------------------

"xboxdrv" installieren:
	sudo apt-get install xboxdrv

Testen ob Treiber korrekt installiert ist:
	sudo xboxdrv --detach-kernel-driver

	... Mehr siehe https://github.com/FRC4564/Xbox ...

Falls notwendig: "python3-rpi.gpio"-Paket installieren (ist standardm��ig nur f�r Python2 installiert?):
	sudo apt install python3-rpi.gpio
	

-------- START -------------------------------------------

Skript.py auf dem Raspberry Pi mit root-Rechten starten:
	sudo python3 Skript.py

------- STEUERUNG ----------------------------------------

Beschleunigung:				rechter Trigger
R�ckw�rts:				linker Trigger
Lenkung:				linker Analogstick
Bremsen (Motor "kurzschlie�en"): 	B
Skript Beenden:				"Strg" + C oder "Start" und "Back"



-------- BEIM BEARBEITEN BEACHTEN! -----------------------

Bei Python m�ssen die Einr�ckungen einheitlich vorgenommen werden, entweder mit Leerzeichen oder mit Tabs! Ansonsten kommt bei der Ausf�hrung eine Fehlermeldung.

Im Skript.py sind die Einr�ckungen mit Tabs realisiert.

Um zu �berpr�fen ob die Einr�ckungen einheitlich sind, k�nnen bei Notepad++ unter "Ansicht", "Nicht druckbare Zeichen" Leerzeichen und Tabulatoren angezeigt werden.

------- QUELLEN ------------------------------------------

https://sourceforge.net/p/raspberry-gpio-python/wiki/PWM/
https://github.com/FRC4564/Xbox


