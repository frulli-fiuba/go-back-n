import argparse
import logging
import logging.config
from threading import Thread
from lib.constants import DEFAULT_HOST, DEFAULT_PORT
from lib.validations import server_validations

logging.config.fileConfig("./lib/logging.conf")

from lib.socket_tp import SocketTP

logger = logging.getLogger(__name__)

def send_file(socket: SocketTP):
    with open("./test.png", "rb") as f:
        data = f.read()
        size = len(data)
        try:
            socket.sendall(size.to_bytes(4, "big"))
            socket.sendall(data)
        finally:
            socket.close()


def main():
    parser = argparse.ArgumentParser(description='Starts the server for file transfers.')
    parser.add_argument('-v', '--verbose', action='store_true', help='increase output verbosity')
    parser.add_argument('-q', '--quiet', action='store_true', help='decrease output verbosity')
    parser.add_argument('-H', '--host', type=str, default=DEFAULT_HOST, help='service IP address')
    parser.add_argument('-p', '--port', type=int, default=DEFAULT_PORT, help='service port')
    parser.add_argument('-s', '--storage', type=str, required=True, help='storage directory path')

    args = parser.parse_args()
    server_validations(args)

    print(f"Iniciando el servidor en {args.host}:{args.port} con el directorio de almacenamiento en '{args.storage}'")
    if args.verbose:
        logging.getLogger("socket").setLevel(logging.DEBUG)
    # TODO: Implementar la lógica del servidor, idealmente en una función aparte y con los parámetros correspondientes.
    s = SocketTP()
    s.bind(args.host, args.port)
    s.listen()
    threads = []
    while True:
        new_socket = s.accept()
        #TODO add parameter
        thread = Thread(target=send_file, args=(new_socket,))
        thread.start()
        threads.append(thread)
    
    s.close()

if __name__ == '__main__':
    main()
