import json
import fcntl
import socket
from pathlib import Path

class QEMU:

	client = None
	socket = None


	def __init__(self, unixSocket):
		self.socket = unixSocket


	def __enter__(self):
		self.client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
		self.client.settimeout(1)
		self.client.setblocking(1)
		self.client.connect(self.socket)
		self.read(self.client)
		self.qmp({ "execute": "qmp_capabilities" })
		return self


	def __exit__(self, _type, value, tb):
		self.client.close()


	# TODO: Do not return unless f is not empty
	def read(self, socket):
		f = ''
		while True:
			try:
				obj = json.loads(f.strip())
				print('RECV <-', obj)
				return obj
			except:
				f += self.client.recv(1).decode()


	def qmp(self, command):
		message = f"{json.dumps(command)}\n"
		print(f"SEND -> {message.strip()}")
		self.client.send(str.encode(message))
		return self.read(self.client)


	def hmp(self, command):
		result = self.qmp({ "execute": "human-monitor-command", "arguments": { "command-line": f"{command}" } })
		return result['return'] if 'return' in result else result

