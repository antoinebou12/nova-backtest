import socket
import threading


class ServerLog:

    def __init__(self):

        self.HEADER = 64
        self.PORT = 5080
        self.SERVER = socket.gethostbyname(socket.gethostname())
        self.ADDR = (self.SERVER, self.PORT)
        self.FORMAT = 'utf-8'
        self.DISCONNECT_MESSAGE = '!DISCONNECT'

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(self.ADDR)

    def handle_client(self, conn, addr):
        print(f"new connection -- {addr} connected")
        connected = True

        while connected:
            msg_length = conn.recv(self.HEADER).decode(self.FORMAT)
            if msg_length:
                msg_length = int(msg_length)
                msg = conn.recv(msg_length).decode(self.FORMAT)
                if msg == self.DISCONNECT_MESSAGE:
                    connected = False
                print(f'address -- {addr} -- {msg}')

                # message = msg.encode(self.FORMAT)
                # conn.send(message)

        conn.close()

    def start(self):
        self.server.listen()
        print(f'Sever is listening on {self.SERVER}')
        while True:
            conn, addr = self.server.accept()
            thread = threading.Thread(target=self.handle_client, args=(conn, addr))
            thread.start()
            print(f'Active Connections -- {threading.active_count() - 1}')


log_server = ServerLog()
print('SERVER IS STARTING')
log_server.start()
