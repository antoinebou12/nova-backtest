import socket


HEADER = 64
PORT = 5080
SERVER = socket.gethostbyname(socket.gethostname())
ADDR = (SERVER, PORT)
FORMAT = 'utf-8'
DISCONNECT_MESSAGE = '!DISCONNECT'

logger_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
logger_client.connect(ADDR)


while True:
    # receive data from the server and decoding to get the string.
    print(logger_client.recv(1024).decode())



