import json
import socket

class QEMU:

	client = None

	def __init__(self):
		pass

	def connect(self, unixSocket):
		self.client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
		self.client.settimeout(.2)
		self.client.connect(unixSocket)
		self.read(self.client)
		self.send({ "execute": "qmp_capabilities" })


	def read(self, socket):
		f = ''
		while True:
			try:
				obj = json.loads(f.strip())
				print('RECV <-', obj)
				return obj
			except:
				f += self.client.recv(1).decode()


	def send(self, command):
		message = f"{json.dumps(command)}\n"
		print(f"SEND -> {message.strip()}")
		self.client.send(str.encode(message))
		return self.read(self.client)


	def disconnect(self):
		self.client.close()

