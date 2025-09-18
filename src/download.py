import argparse
from lib.socket_tp import SocketTP
from time import sleep

HOST = "127.0.0.1"
PORT = 6000

def main():
    parser = argparse.ArgumentParser(description='Downloads a file from the server to the client.')
    parser.add_argument('-v', '--verbose', action='store_true', help='increase output verbosity')
    parser.add_argument('-q', '--quiet', action='store_true', help='decrease output verbosity')
    parser.add_argument('-H', '--host', type=str, default=HOST, help='server IP address')
    parser.add_argument('-p', '--port', type=int, default=PORT, help='server port')
    parser.add_argument('-d', '--dst', type=str, required=True, help='destination file path')
    parser.add_argument('-n', '--name', type=str, required=True, help='file name')
    parser.add_argument('-r', '--protocol', type=str, help='error recovery protocol')
    
    args = parser.parse_args()

    print(f"Descargando el archivo '{args.name}' de {args.host}:{args.port} a '{args.dst}'")

    # TODO: Implementar la lógica de descarga de archivo
    # s = SocketTP()
    # s.connect(args.host, args.port)
    # ...

if __name__ == '__main__':
    main()
