import argparse
import logging
import logging.config

logging.config.fileConfig("./lib/logging.conf")

from lib.socket_tp import SocketTP

logger = logging.getLogger(__name__)

HOST = "127.0.0.1"
PORT = 6000

def main():
    parser = argparse.ArgumentParser(description='Starts the server for file transfers.')
    parser.add_argument('-v', '--verbose', action='store_true', help='increase output verbosity')
    parser.add_argument('-q', '--quiet', action='store_true', help='decrease output verbosity')
    parser.add_argument('-H', '--host', type=str, default=HOST, help='service IP address')
    parser.add_argument('-p', '--port', type=int, default=PORT, help='service port')
    parser.add_argument('-s', '--storage', type=str, required=True, help='storage directory path')

    args = parser.parse_args()

    print(f"Iniciando el servidor en {args.host}:{args.port} con el directorio de almacenamiento en '{args.storage}'")
    if args.verbose:
        logging.getLogger("socket").setLevel(logging.DEBUG)
    # TODO: Implementar la lógica del servidor, idealmente en una función aparte y con los parámetros correspondientes.
    s = SocketTP()
    s.bind(args.host, args.port)
    s.listen()

    while True:
        new_socket = s.accept()
        #TODO add parameter
        with open("/home/federico-rulli/Pictures/Screenshots/Screenshot from 2025-09-08 21-31-19.png", "rb") as f:
            data = f.read()
            size = len(data)
            new_socket.sendall(size.to_bytes(4))
            new_socket.sendall(data)

    s.close()

if __name__ == '__main__':
    main()
