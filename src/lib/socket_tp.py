from socket import socket, AF_INET, SOCK_DGRAM
from .utils import Packet, Window, Timer, Sequence
import queue
import logging
from threading import Thread
from time import sleep
from collections import defaultdict


logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)


class SocketTP:
    PACKET_SIZE = 1024
    TIMEOUT = 2
    
    def __init__(self, window_size=5):
        self.host = None
        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.connection_queue = None
        self.dest_addr = None
        self.listen_thread = None
        self.end_connection = False
        self.window_size = window_size
        self.window = Window(window_size * self.PACKET_SIZE)
        self.timer = Timer()
        self.sequence = Sequence()
        self.packet_queue = queue.Queue()
        self.process_incoming_thread = Thread(target=self._process_incoming)
        self.received_ack = 0
        self.connection_being_accepted = None
        self.connection_accepted = False

    def _process_syn(self, addr: str, packet: Packet):     
        logger.debug(f'{addr} - {packet} - SYN RECEIVED')   
        if not packet.ack and addr != self.connection_being_accepted and self.connection_queue:
            logger.debug(f"Added {addr} to the connection queue")
            self.connection_queue.put(addr)
        elif packet.syn and packet.ack:
            self.socket.sendto(Packet(ack=True).to_bytes(), addr)
            self.dest_addr = addr          
    
    def listen(self, maxsize: int = 0):
        self.connection_queue = queue.Queue(maxsize=maxsize)
        self.process_incoming_thread.start()

    def _process_ack(self, packet: Packet, repeated_ack: dict):
        logger.debug(f'{packet} - RECEIVED')
        
        if packet.seq_number > self.sequence.ack:
            self.window.increase(packet.seq_number - self.sequence.ack)
            self.sequence.ack = packet.seq_number
        else:
            repeated_ack[packet.seq_number] += 1
            if repeated_ack[packet.seq_number] > 3:
                logger.debug(f"REPEATED ACK {packet.seq_number}: {repeated_ack[packet.seq_number]} RESENDING")
                self._reset()
    
    def _reset(self):
        self.sequence.reset()
        self.window.reset()
        self.timer.stop()
    
    def _process_incoming(self):
        self.socket.settimeout(self.TIMEOUT)
        repeated_ack = defaultdict(int)
        while not self.end_connection:
            try:
                if self.timer.is_expired():
                    logger.debug('Timeout')
                    self._reset()
                
                data, addr = self.socket.recvfrom(1500)
                packet = Packet.from_bytes(data)
                if packet.syn:
                    self._process_syn(addr, packet)
                elif packet.ack:
                    self._process_ack(packet, repeated_ack)
                else:
                    if packet.seq_number == self.received_ack:
                        logger.debug(f'{addr} - {packet} - ACCEPTED')
                        self.received_ack = self.received_ack + len(packet.data)
                        self.packet_queue.put(packet)
                    else:
                        logger.debug(f'{addr} - {packet} - IGNORED expected: {self.received_ack}')

                    self.socket.sendto(Packet(ack=True, seq_number=self.received_ack).to_bytes(), addr)
            except Exception:
                pass

    def bind(self, host: str, port: int):
        self.host = host
        self.socket.bind((host, port))
 
    def accept(self) -> 'SocketTP':
        addr = self.connection_queue.get()
        self.connection_being_accepted = addr
        
        socket_connection = socket(AF_INET, SOCK_DGRAM)
        socket_connection.bind((self.host, 0))
        socket_connection.settimeout(self.TIMEOUT)

        while self.connection_being_accepted:
            try:
                socket_connection.sendto(Packet(syn=True, ack=True).to_bytes(), addr)
                data, recv_addr = socket_connection.recvfrom(self.PACKET_SIZE)
                packet = Packet.from_bytes(data)
                logger.debug(f'{addr} - {packet}')
                if recv_addr == addr and packet.ack:
                    self.connection_being_accepted = None
            except:
                pass
            
        new_socket = SocketTP(self.window_size)
        new_socket.socket = socket_connection
        new_socket.dest_addr = addr
        new_socket.process_incoming_thread.start()
        return new_socket
    
    #TODO add paramater to use stop & wait or gbn
    def connect(self, host: str, port: int):
        self.process_incoming_thread.start()
        while not self.dest_addr:
            self.socket.sendto(Packet(syn=True).to_bytes(), (host, port))
            sleep(self.TIMEOUT)       

    def sendall(self, data: bytes):
        offset = self.sequence.send
        sequence = self.sequence.send
        fin = False
        while not fin:
            start = sequence - offset
            end = start + min(self.PACKET_SIZE, self.window.size, len(data[start:]))
            if data[start: end]:
                packet = Packet(data=data[start: end], seq_number=sequence)
                self.socket.sendto(packet.to_bytes(), self.dest_addr)
                
                logger.debug(f'{self.dest_addr} - {packet} - SENT')
                
                if self.sequence.are_equal():
                    self.timer.set()
                
                self.window.decrease(len(data[start: end]))
            else:
                if not self.timer.is_set():
                    self.timer.set()
            
            with self.sequence.lock:
                if sequence > self.sequence._send:
                    sequence = self.sequence._send
                else:
                    self.sequence._send = offset + end 
                    sequence = offset + end
                
                fin = len(data) == self.sequence._ack - offset
    
    def recv(self, size: int) -> bytes:
        buffer = b''
        while True:
            packet = self.packet_queue.get()
            buffer += packet.data
            if len(buffer) == size:
                return buffer

    #TODO add close flux
    def close(self):
        self.end_connection = True
        self.socket.close()
        if self.listen_thread:
            self.listen_thread.join()
        if self.process_incoming_thread:
            self.process_incoming_thread.join()
