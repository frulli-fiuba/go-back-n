from socket_go_back_n import SocketGoBackN
from time import sleep

HOST = "127.0.0.1"
PORT = 6000


s = SocketGoBackN()
s.connect(HOST, PORT)

data = s.recv(1500)
with open("archivo.png", "wb") as f:
    f.write(data)
s.close()
#sleep(10)