import socket
import os


class UDPServer:
    def __init__(self, port):
        try:
            self.port = int(port)
            self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            # Assign IP address and port number to socket
            self.serverSocket.bind(('127.0.0.1', self.port))
            self.serverSocket.setblocking(0)
            self.filename = None
            self.sender = None
            self.buffer = []
            self.n = 0
            self.is_exit = False
        except OSError:
            if self.serverSocket:
                self.serverSocket.close()

    def listen(self):
        try:
            self.serverSocket.settimeout(5.0)
        except:
            pass

        while True:
            try:
                message, _address = self.serverSocket.recvfrom(1024)

                # Append all the messages into buffer list
                self.buffer.append(message)

                if message.decode('utf-8').startswith('SENDER'):
                    self.buffer.remove(message)
                    self.sender = message.decode('utf-8').split(';')[1]
                if message.decode('utf-8').startswith('FILENAME'):
                    self.buffer.remove(message)
                    self.filename = message.decode('utf-8').split(';')[1]

                # write to file
                with open(f'{self.sender}_{self.filename}', 'wb') as video:
                    for i in self.buffer:
                        video.write(i)

                if self.sender is not None and self.filename is not None:
                    print(f'Received {self.filename} from {self.sender}')

                if os.path.exists(f'{self.sender}_None'):
                    os.remove(f'{self.sender}_None')

                self.serverSocket.close()
            except:
                '''no data yet...'''


class UDPClient:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = int(port)

        # Create a UDP socket
        self.clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Set a timeout value of 1 second
        self.clientSocket.settimeout(1)

    def send(self, msg):
        addr = (self.ip, self.port)

        filename, sender = msg.split(';')

        sender_message = f'SENDER;{sender}'
        filename_message = f'FILENAME;{filename}'

        with open(filename, 'rb') as video:

            while True:
                buffer = video.read(5000)

                self.clientSocket.sendto(buffer, addr)

                if len(buffer) < 5000:
                    # reaches the last set of data
                    break

        self.clientSocket.sendto(sender_message.encode(), addr)
        self.clientSocket.sendto(filename_message.encode(), addr)
