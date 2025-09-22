import argparse
import logging
import logging.config
from lib.socket_tp import SocketTP
from lib.constants import ERROR_RECOVERY_PROTOCOL_MAPPING, DEFAULT_HOST, DEFAULT_PORT, ClientMode
from lib.validations import download_validations
from lib.file_transfer import recv_file

logging.config.fileConfig("./lib/logging.conf")

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Downloads a file from the server to the client.')
    parser.add_argument('-v', '--verbose', action='store_true', help='increase output verbosity')
    parser.add_argument('-q', '--quiet', action='store_true', help='decrease output verbosity')
    parser.add_argument('-H', '--host', type=str, default=DEFAULT_HOST, help='server IP address')
    parser.add_argument('-p', '--port', type=int, default=DEFAULT_PORT, help='server port')
    parser.add_argument('-d', '--dst', type=str, required=True, help='destination file path')
    parser.add_argument('-n', '--name', type=str, required=True, help='file name')
    parser.add_argument('-r', '--protocol', type=str, help='error recovery protocol', choices=ERROR_RECOVERY_PROTOCOL_MAPPING.keys(), default="GO_BACK_N")
    
    args = parser.parse_args()
    download_validations(args)

    logger.info(f"Descargando el archivo '{args.name}' de {args.host}:{args.port} a '{args.dst}'")
    
    if args.verbose:
        logging.getLogger("socket").setLevel(logging.DEBUG)
    
    s = SocketTP()
    s.connect(
        args.host,
        args.port,
        ERROR_RECOVERY_PROTOCOL_MAPPING[args.protocol],
    )

    s.sendall(ClientMode.DOWNLOAD.value.to_bytes(4, "big"))

    name_b = args.name.encode("utf-8")
    s.sendall(len(name_b).to_bytes(4, "big"))
    s.sendall(name_b)

    recv_file(s, args.dst, args.name)

    s.close()
    logger.info("Fin de la descarga, cerrando socket.")


if __name__ == '__main__':
    main()
