import os
import logging
from lib.socket_tp import SocketTP
from lib.constants import FILE_NOT_FOUND_ERROR_CODE

logger = logging.getLogger("root")


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
        logger.debug("Envío finalizado.")


def recv_file(socket, dst: str, name: str):
    try: 
        size_bytes = socket.recv(4)
        int_size = int.from_bytes(size_bytes, "big", signed=True)

        if int_size == FILE_NOT_FOUND_ERROR_CODE:
            logger.error("El servidor indicó que el archivo no existe.")
            return

        data = socket.recv(int_size)
    except Exception as e:
        logger.error(f"Error recibiendo archivo: {e}")
        return
    
    file_path = os.path.join(dst, name) if os.path.isdir(dst) else dst
    with open(file_path, "wb") as f:
        f.write(data)
    logger.debug(f"Archivo recibido y guardado en {file_path}")
