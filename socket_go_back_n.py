from socket import socket, AF_INET, SOCK_DGRAM
from utils import Packet
import queue
import logging
from typing import Tuple
from threading import Thread


logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)


HOST = "127.0.0.1"
PORT = 6000


class SocketGoBackN:
    PACKET_SIZE = 1024
    
    def __init__(self):
        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.connection_queue = None
        self.dest_addr = None
        self.listen_thread = None
        self.ack_thread = None
        self.end_connection = False
        self.window_size = 1024
        self.seq = 0
        self.seq_ack = 0
        self.window = 5

    def _listen(self):
        self.socket.settimeout(2)
        while not self.end_connection:
            try:
                data, addr = self.socket.recvfrom(1024)
                logger.debug(f'{addr} - {Packet.from_bytes(data)}')
                self.connection_queue.put(addr)
            except:
                continue
    
    def listen(self, maxsize: int = 0):
        self.connection_queue = queue.Queue(maxsize=maxsize)
        self.listen_thread = Thread(target=self._listen)
        self.listen_thread.start()

    def _listen_ack(self):
        self.socket.settimeout(2)
        while not self.end_connection:
            try:
                data, addr = self.socket.recvfrom(1024)
                packet = Packet.from_bytes(data)
                logger.debug(f'{addr} - {packet}')
                self.seq_ack = Packet.from_bytes(data).seq
            except:
                continue

    def bind(self, host: str, port: int):
        self.socket.bind((host, port))

    def accept(self) -> 'SocketGoBackN':
        addr = self.connection_queue.get()
        
        socket_connection = socket(AF_INET, SOCK_DGRAM)
        socket_connection.bind((HOST, 0))
        socket_connection.sendto(Packet(syn=True, ack=True).to_bytes(), addr)
        
        data, addr = socket_connection.recvfrom(1024)
        logger.debug(f'{addr} - {Packet.from_bytes(data)}')
        
        new_socket = SocketGoBackN()
        new_socket.socket = socket_connection
        new_socket.dest_addr = addr
        
        return new_socket
    
    def connect(self, host: str, port: int):
        self.socket.sendto(Packet(syn=True).to_bytes(), (host, port))
        data, addr = self.socket.recvfrom(1024)
        logger.debug(f'{addr} - {Packet.from_bytes(data)}')
        self.socket.sendto(Packet(ack=True).to_bytes(), addr)
        self.dest_addr = addr
    
    def sendall(self, data: bytes):
        self.ack_thread = Thread(target=self._listen_ack)
        end = self.PACKET_SIZE if len(data) > self.PACKET_SIZE else len(data)
        fin = False
        start = 0
        while not fin:
            fin = len(data[start:]) < self.PACKET_SIZE
            self.socket.sendto(Packet(data=data[start: end], seq=start, fin=fin).to_bytes(), self.dest_addr)
            start = end
            if len(data[start:]) < self.PACKET_SIZE:
                end = start + len(data[start:])
            else:
                end = start + self.PACKET_SIZE

    
    def recv(self, size: int = 1024) -> Tuple[bytes, str]:
        buffer = b''
        fin = False
        while not fin:
            data, addr = self.socket.recvfrom(size)
            packet = Packet.from_bytes(data)
            logger.debug(f'{addr} - {Packet.from_bytes(data)}')
            if packet.seq == self.seq_ack:
                buffer += packet.data
                self.seq_ack += len(packet.data)
                fin = packet.fin
            self.socket.sendto(Packet(ack=True, seq=self.seq_ack).to_bytes(), addr)
        return buffer, self.dest_addr

    def close(self):
        self.end_connection = True
        self.socket.close()
        if self.listen_thread:
            self.listen_thread.join()
