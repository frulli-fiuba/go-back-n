from socket import socket, AF_INET, SOCK_DGRAM
from utils import Packet, Window, Timer, Sequence
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


class SocketGoBackN:
    PACKET_SIZE = 1024
    
    def __init__(self):
        self.host = None
        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.connection_queue = None
        self.dest_addr = None
        self.listen_thread = None
        self.end_connection = False
        self.window = Window(5 * self.PACKET_SIZE)
        self.timer = Timer()
        self.sequence = Sequence()
        self.packet_queue = queue.Queue()
        self.process_incoming_thread = Thread(target=self._process_incoming)

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

    def _process_ack(self, packet: Packet):
        logger.debug(f'{packet} - RECEIVED')
        if packet.seq > self.sequence.ack:
            self.window.increase(packet.seq - self.sequence.ack)
            self.sequence.ack = packet.seq
    
    def _process_timeout(self):
        logger.debug('Timeout')
        self.sequence.reset()
        self.window.reset()
        self.timer.stop()
    
    def _process_incoming(self):
        self.socket.settimeout(2)
        while not self.end_connection:
            try:
                if self.timer.is_expired():
                    self._process_timeout()
                
                data, addr = self.socket.recvfrom(1500)
                packet = Packet.from_bytes(data)
                
                if packet.ack:
                    self._process_ack(packet)
                else:
                    packet = Packet.from_bytes(data)
                    if packet.seq == self.sequence.ack:
                        logger.debug(f'{addr} - {Packet.from_bytes(data)} - ACCEPTED')
                        self.sequence.ack = self.sequence.ack + len(packet.data)
                        self.packet_queue.put(packet)
                    else:
                        logger.debug(f'{addr} - {Packet.from_bytes(data)} - IGNORED expected: {self.sequence.ack}')
                   
                    self.socket.sendto(Packet(ack=True, seq=self.sequence.ack).to_bytes(), addr)
            except Exception:
                pass

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
        new_socket.process_incoming_thread.start()
        return new_socket
    
    def connect(self, host: str, port: int):
        self.socket.sendto(Packet(syn=True).to_bytes(), (host, port))
        data, addr = self.socket.recvfrom(self.PACKET_SIZE)
        logger.debug(f'{addr} - {Packet.from_bytes(data)}')
        self.socket.sendto(Packet(ack=True).to_bytes(), addr)
        self.dest_addr = addr
        self.process_incoming_thread.start()
    
    def sendall(self, data: bytes):
        fin = False
        self.sequence.send = 0
        self.window.reset()
        while not fin:
            fin = len(data[self.sequence.send:]) < self.PACKET_SIZE
            start = self.sequence.send
            end = start + min(self.PACKET_SIZE, self.window.size, len(data[start:]))
            if data[start: end]:
                packet = Packet(data=data[start: end], seq=start, fin=fin)
                self.socket.sendto(packet.to_bytes(), self.dest_addr)
                logger.debug(f'{self.dest_addr} - {packet} - SENT')
                
                if self.sequence.are_equal():
                    self.timer.set()
                
                self.window.decrease(len(data[start: end]))
            else:
                if not self.timer.is_set():
                    self.timer.set()
            
            self.sequence.send = end
            
    
    def recv(self, size: int = 1024) -> bytes:
        buffer = b''
        while True:
            packet = self.packet_queue.get()
            buffer += packet.data
            if packet.fin:
                return buffer

    def close(self):
        self.end_connection = True
        self.socket.close()
        if self.listen_thread:
            self.listen_thread.join()
        if self.process_incoming_thread:
            self.process_incoming_thread.join()
