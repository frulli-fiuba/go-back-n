from socket_go_back_n import SocketGoBackN


HOST = "127.0.0.1"
PORT = 6000


s = SocketGoBackN()
s.connect(HOST, PORT)

data, addr = s.recv(1500)
with open("archivo.png", "wb") as f:
    f.write(data)