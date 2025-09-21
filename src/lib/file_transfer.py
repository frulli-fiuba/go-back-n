import os
import logging
from lib.socket_tp import SocketTP

logger = logging.getLogger(__name__)


def send_file(socket: SocketTP, src: str):
    with open(src, "rb") as f:
        data = f.read()
    size_bytes = len(data).to_bytes(4, "big")
    try:
        logger.debug(f"Enviando {len(data)} bytes...")
        socket.sendall(size_bytes)
        socket.sendall(data)
        logger.debug("Archivo enviado correctamente.")
    finally:
        logger.debug("Conexión cerrada.")
        socket.close()


def recv_file(socket, dst: str, name: str):
    try: 
        size_bytes = socket.recv(4)
        int_size = int.from_bytes(size_bytes, "big")
        data = socket.recv(int_size)
    except Exception as e:
        logger.error(f"Error recibiendo archivo: {e}")
        socket.close()
        return
    
    file_path = os.path.join(dst, name) if os.path.isdir(dst) else dst
    with open(file_path, "wb") as f:
        f.write(data)
    logger.debug(f"Archivo recibido y guardado en {file_path}")
    socket.close()
