import os
import argparse
import logging
import logging.config
from threading import Thread
from lib.constants import DEFAULT_HOST, DEFAULT_PORT, ClientMode
from lib.validations import server_validations
from lib.socket_tp import SocketTP
from lib.file_transfer import send_file, recv_file

logging.config.fileConfig("./lib/logging.conf")

logger = logging.getLogger(__name__)


def handle_client(socket: SocketTP, storage_dir: str):
    try:
        client_mode_b = socket.recv(4)
        client_mode = ClientMode(int.from_bytes(client_mode_b, "big"))

        name_len_b = socket.recv(4)
        name_len = int.from_bytes(name_len_b, "big")
        name_b = socket.recv(name_len)
        filename = name_b.decode("utf-8")


    except Exception as e:
        logger.error(f"Error leyendo metadata inicial del cliente: {e}")
        socket.close()
        return

    if client_mode == ClientMode.DOWNLOAD:
        filepath = os.path.join(storage_dir, filename)
        if not os.path.exists(filepath):
            socket.sendall((-1).to_bytes(4, "big", signed=True))
            logger.error(f"Archivo {filepath} no existe, no se puede enviar.")
            socket.close()
            return
        try:
            send_file(socket, filepath)
        finally:
            socket.close()
    elif client_mode == ClientMode.UPLOAD:
        try:
            recv_file(socket, storage_dir, filename)
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

    logger.info(f"Iniciando el servidor en {args.host}:{args.port} con el directorio de almacenamiento en '{args.storage}'")

    if args.verbose:
        logging.getLogger("socket").setLevel(logging.DEBUG)

    s = SocketTP()
    s.bind(args.host, args.port)
    s.listen()
    threads = []
    while True:
        new_socket = s.accept()
        thread = Thread(target=handle_client, args=(new_socket, args.storage))
        thread.start()
        threads.append(thread)
    
    s.close()

if __name__ == '__main__':
    main()
