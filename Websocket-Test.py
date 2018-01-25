import socket
import sys

HOST = 'localhost'
PORT = 8000

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
	s.bind((HOST,PORT))
except socket.error as msg:
	print('Port binding Fehlgeschlagen. Error :  ' + str(msg[0]) + ' Message ' + msg[1])
	sys.exit()

print('Socket binding erfolgreich')

# Auf Port hoeren
s.listen(10)
print(' Socket now listening ')
conn, addr = s.accept()
print(' Verbunden mit: ' + addr[0] + '+' + str(addr[1]))

while 1:
		conn.send(bytes('Nachricht' + '\r\n', 'UTF-8'))
		print('Nachricht gesendet')
		data = conn.recv(1024)
		print(data.decode(encoding='UTF-8'))
s.close()
