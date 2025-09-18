from lib.socket import SocketTP

HOST = "127.0.0.1"
PORT = 6000

s = SocketTP(5)
s.bind(HOST, PORT)
s.listen()

while True:
    new_socket = s.accept()
    #TODO add parameter
    with open("/home/federico-rulli/Pictures/Screenshots/Screenshot from 2025-09-12 18-27-48.png", "rb") as f:
        data = f.read()
        size = len(data)
        new_socket.sendall(size.to_bytes(4))
        new_socket.sendall(data)

s.close()

