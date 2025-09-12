from socket import socket, AF_INET, SOCK_DGRAM
from utils import Packet
import queue
import logging
from typing import Tuple
from threading import Thread, Lock
from datetime import datetime, timedelta


logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)


class Timer:
    def __init__(self):
        self.limit_time = None

    def stop(self):
        self.limit_time = None

    def is_expired(self) -> bool:
        return self.limit_time and datetime.now() > self.limit_time

    def set(self):
        self.limit_time = datetime.now() + timedelta(seconds=2)


class SocketGoBackN:
    PACKET_SIZE = 1024
    
    def __init__(self):
        self.host = None
        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.connection_queue = None
        self.dest_addr = None
        self.listen_thread = None
        self.ack_thread = None
        self.end_connection = False
        self.seq = 0
        self.seq_ack = 0
        self.limit_time = None
        self.window_size = 5 * self.PACKET_SIZE
        self.window_lock = Lock()
        self.timer = Timer()

    def _listen(self):
        self.socket.settimeout(2)
        while not self.end_connection:
            try:
                data, addr = self.socket.recvfrom(self.PACKET_SIZE)
                logger.debug(f'{addr} - {Packet.from_bytes(data)}')
                self.connection_queue.put(addr)
            except:
                continue
    
    def listen(self, maxsize: int = 0):
        self.connection_queue = queue.Queue(maxsize=maxsize)
        self.listen_thread = Thread(target=self._listen)
        self.listen_thread.start()

    def _process_ack(self, last_ack: int):
        self.socket.settimeout(2)
        completed = False
        while not self.end_connection and not completed:
            try: 
                if self.timer.is_expired():
                    logger.debug(f'{addr} - Timeout')
                    self.seq = self.seq_ack
                    self.window_size = 5 * self.PACKET_SIZE
                    self.timer.stop()
                
                data, addr = self.socket.recvfrom(self.PACKET_SIZE)
                packet = Packet.from_bytes(data)
                logger.debug(f'{addr} - {Packet.from_bytes(data)} - RECEIVED')
                if packet.ack:
                    if packet.seq > self.seq_ack:
                        with self.window_lock:
                            new_window_size = self.window_size + packet.seq - self.seq_ack
                            logger.debug(f'{addr} - window size, from {self.window_size} to {new_window_size} FROM ACK')
                            self.window_size = new_window_size
                        self.seq_ack = packet.seq
                    if packet.seq == last_ack:
                        logger.debug(f'{addr} - Transmision completed')
                        completed = True
            except Exception:
                logger.debug(f"{self.dest_addr} - No new ACKS")

    def bind(self, host: str, port: int):
        self.host = host
        self.socket.bind((host, port))

    def accept(self) -> 'SocketGoBackN':
        addr = self.connection_queue.get()
        
        socket_connection = socket(AF_INET, SOCK_DGRAM)
        socket_connection.bind((self.host, 0))
        socket_connection.sendto(Packet(syn=True, ack=True).to_bytes(), addr)
        
        data, addr = socket_connection.recvfrom(self.PACKET_SIZE)
        logger.debug(f'{addr} - {Packet.from_bytes(data)}')
        
        new_socket = SocketGoBackN()
        new_socket.socket = socket_connection
        new_socket.dest_addr = addr
        
        return new_socket
    
    def connect(self, host: str, port: int):
        self.socket.sendto(Packet(syn=True).to_bytes(), (host, port))
        data, addr = self.socket.recvfrom(self.PACKET_SIZE)
        logger.debug(f'{addr} - {Packet.from_bytes(data)}')
        self.socket.sendto(Packet(ack=True).to_bytes(), addr)
        self.dest_addr = addr
    
    def sendall(self, data: bytes):
        self.ack_thread = Thread(target=self._process_ack, args=(len(data),))
        self.ack_thread.start()
        fin = False
        self.seq = 0
        self.window_size = 5 * self.PACKET_SIZE
        while not fin:
            fin = len(data[self.seq:]) < self.PACKET_SIZE
            end = self.seq + min(self.PACKET_SIZE, self.window_size, len(data[self.seq:]))
            if data[self.seq: end]:
                packet = Packet(data=data[self.seq: end], seq=self.seq, fin=fin)
                self.socket.sendto(packet.to_bytes(), self.dest_addr)
                logger.debug(f'{self.dest_addr} - {packet} - SENT')
                if self.seq == self.seq_ack:
                    self.timer.set()
                
                with self.window_lock:
                    new_window_size = self.window_size - len(data[self.seq: end])
                    logger.debug(f'{self.dest_addr} - window size, from {self.window_size} to {new_window_size } FROM SEND') 
                    self.window_size = new_window_size 
            
            self.seq = end
            
    
    def recv(self, size: int = 1024) -> Tuple[bytes, str]:
        buffer = b''
        fin = False
        while not fin:
            data, addr = self.socket.recvfrom(size)
            packet = Packet.from_bytes(data)
            if packet.seq == self.seq_ack:
                logger.debug(f'{addr} - {Packet.from_bytes(data)} - ACCEPTED')
                buffer += packet.data
                self.seq_ack += len(packet.data)
                fin = packet.fin
            else:
                logger.debug(f'{addr} - {Packet.from_bytes(data)} - IGNORED')

            self.socket.sendto(Packet(ack=True, seq=self.seq_ack).to_bytes(), addr)
        return buffer, self.dest_addr

    def close(self):
        self.end_connection = True
        self.socket.close()
        if self.listen_thread:
            self.listen_thread.join()
