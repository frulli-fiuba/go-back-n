import sys
import tty
import termios
import os
import argparse
import logging
import logging.config
from threading import Thread
from lib.constants import DEFAULT_HOST, DEFAULT_PORT, ClientMode, FILE_NOT_FOUND_ERROR_CODE
from lib.validations import server_validations
from lib.socket_tp import SocketTP
from lib.file_transfer import send_file, recv_file

logging.config.fileConfig("./lib/logging.conf")

logger = logging.getLogger(__name__)


def get_key():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    try:
        tty.setraw(fd)
        key = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    return key


def wait_for_close(socket: SocketTP):
    key_pressed = None
    while key_pressed != 'q':
        logger.info("Persionar `q` para cerrar")
        key_pressed = get_key()
    socket.close()

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
            socket.sendall((FILE_NOT_FOUND_ERROR_CODE).to_bytes(4, "big", signed=True))
            logger.error(f"Archivo {filepath} no existe, no se puede enviar.")
            socket.close()
            return
        try:
            send_file(socket, filepath)
        finally:
            logger.info("Fin de la descarga, cerrando socket.")
            socket.close()
    elif client_mode == ClientMode.UPLOAD:
        try:
            recv_file(socket, storage_dir, filename)
        finally:
            logger.info("Fin de la subida, cerrando socket.")
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

    if args.verbose:
        logging.getLogger("socket").setLevel(logging.DEBUG)
    if args.quiet:
        logging.getLogger("socket").setLevel(logging.ERROR)
        logger.setLevel(logging.ERROR)
    
    logger.info(f"Iniciando el servidor en {args.host}:{args.port} con el directorio de almacenamiento en '{args.storage}'")
    
    s = SocketTP()
    s.bind(args.host, args.port)
    s.listen()
    threads = []
    close_thread = Thread(target=wait_for_close, args=(s,))
    close_thread.start()
    try:
        while new_socket := s.accept():
            thread = Thread(target=handle_client, args=(new_socket, args.storage))
            thread.start()
            threads.append(thread)
    except Exception:
        logger.info("Cerrando servidor")

    close_thread.join()
    for thread in threads:
        thread.join()
    
if __name__ == '__main__':
    main()
