import argparse
import logging
import logging.config

logging.config.fileConfig("./lib/logging.conf")

from lib.socket_tp import SocketTP
from lib.utils import ErrorRecoveryMode

logger = logging.getLogger(__name__)

HOST = "127.0.0.1"
PORT = 6000

def main():
    parser = argparse.ArgumentParser(description='Transfers a file from the client to the server.')
    parser.add_argument('-v', '--verbose', action='store_true', help='increase output verbosity')
    parser.add_argument('-q', '--quiet', action='store_true', help='decrease output verbosity')
    parser.add_argument('-H', '--host', type=str, default=HOST, help='server IP address')
    parser.add_argument('-p', '--port', type=int, default=PORT, help='server port')
    parser.add_argument('-s', '--src', type=str, required=True, help='source file path')
    parser.add_argument('-n', '--name', type=str, help='file name')
    parser.add_argument('-r', '--protocol', type=str, help='error recovery protocol')
    
    args = parser.parse_args()

    # Si no se especifica un nombre, se usa el del archivo de origen.
    filename = args.name if args.name else args.src.split('/')[-1]

    print(f"Subiendo el archivo '{filename}' desde '{args.src}' a {args.host}:{args.port}")
    if args.verbose:
        logging.getLogger("socket").setLevel(logging.DEBUG)
    # TODO: Implementar la lógica de subida de archivo, idealmente en nueva función y con los parámetros correspondientes.
    s = SocketTP()
    s.connect(args.host, args.port, ErrorRecoveryMode.GO_BACK_N)
    size = s.recv(4)
    int_size = int.from_bytes(size)
    data = s.recv(int_size)
    with open("/home/federico-rulli/Pictures/Screenshots/archivo.png", "wb") as f:
        f.write(data)
    s.close()
if __name__ == '__main__':
    main()
