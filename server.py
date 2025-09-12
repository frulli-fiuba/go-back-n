from socket_go_back_n import SocketGoBackN


HOST = "127.0.0.1"
PORT = 6000

s = SocketGoBackN()
s.bind(HOST, PORT)
s.listen()

while True:
    new_socket = s.accept()
    with open("/home/federico-rulli/Pictures/Screenshots/Screenshot from 2025-09-12 18-27-48.png", "rb") as f:
        data = f.read()
        new_socket.sendall(data)

s.close()

