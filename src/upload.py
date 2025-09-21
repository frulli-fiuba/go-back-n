import argparse
import logging
import logging.config
from lib.validations import upload_validations
from lib.constants import ERROR_RECOVERY_PROTOCOL_MAPPING, DEFAULT_HOST, DEFAULT_PORT, ClientMode

logging.config.fileConfig("./lib/logging.conf")

from lib.socket_tp import SocketTP

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Transfers a file from the client to the server.')
    parser.add_argument('-v', '--verbose', action='store_true', help='increase output verbosity')
    parser.add_argument('-q', '--quiet', action='store_true', help='decrease output verbosity')
    parser.add_argument('-H', '--host', type=str, default=DEFAULT_HOST, help='server IP address')
    parser.add_argument('-p', '--port', type=int, default=DEFAULT_PORT, help='server port')
    parser.add_argument('-s', '--src', type=str, required=True, help='source file path')
    parser.add_argument('-n', '--name', type=str, required=True, help='file name')
    parser.add_argument('-r', '--protocol', type=str, help='error recovery protocol', choices=ERROR_RECOVERY_PROTOCOL_MAPPING.keys(), default="GO_BACK_N")
    
    args = parser.parse_args()
    upload_validations(args)

    logger.info(f"Subiendo el archivo '{args.name}' desde '{args.src}' a {args.host}:{args.port}")

    if args.verbose:
        logging.getLogger("socket").setLevel(logging.DEBUG)

    s = SocketTP()
    s.connect(
        args.host,
        args.port,
        args.name,
        ERROR_RECOVERY_PROTOCOL_MAPPING[args.protocol],
        ClientMode.UPLOAD
    )

    with open(args.src, "rb") as f:
        data = f.read()
    size_bytes = len(data).to_bytes(4, "big")
    try:
        logger.debug(f"Enviando {len(data)} bytes al servidor...")
        s.sendall(size_bytes)
        s.sendall(data)
        logger.info(f"Archivo '{args.name}' enviado correctamente al servidor.")
    finally:
        logger.debug("Conexión cerrada.")
        s.close()


if __name__ == '__main__':
    main()
