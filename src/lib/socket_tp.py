from socket import socket, AF_INET, SOCK_DGRAM
from .utils import Packet, Window, Timer, Sequence, ErrorRecoveryMode, validate_type
import queue
import logging
from threading import Thread
from time import sleep
from collections import defaultdict
from datetime import datetime, timedelta


logger = logging.getLogger("socket")


class SocketTP:
    PACKET_SIZE = 1024
    CONNECTION_TIMEOUT = 30
    SOCKET_TIMEOUT = 1
    GO_BACK_N_WINDOW = 100 * PACKET_SIZE
    STOP_AND_WAIT_WINDOW = PACKET_SIZE

    def __init__(self):
        self.host = None
        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.connection_queue = None
        self.dest_addr = None
        self.end_connection = False
        self.window = Window(self.PACKET_SIZE)
        self.timer = Timer()
        self.sequence = Sequence()
        self.packet_queue = queue.Queue()
        self.timer_thread = Thread(target=self._process_timer)
        self.process_incoming_thread = Thread(target=self._process_incoming)
        self.received_ack = 0
        self.connection_being_accepted = None
        self.connection_accepted = False
        self.repeat_threshold = 0

    def _process_syn(self, addr: str, packet: Packet):     
        logger.debug(f'{addr} - {packet} - SYN RECEIVED')   
        if not packet.ack and addr != self.connection_being_accepted and self.connection_queue:
            try:
                data = int.from_bytes(packet.data)
                mode = ErrorRecoveryMode(data)
            except ValueError:
                logger.error(f"{addr} invalid mode: {data} IGNORED")
            
            logger.debug(f"Added {addr} mode: {mode.name} to the connection queue")
            
            self.connection_queue.put((addr, mode))
        
        elif packet.syn and packet.ack:
            self.socket.sendto(Packet(ack=True).to_bytes(), addr)
            self.dest_addr = addr          
    
    def listen(self, maxsize: int = 0):
        validate_type("maxsize", maxsize, int)
        self.connection_queue = queue.Queue(maxsize=maxsize)
        self.process_incoming_thread.start()
        self.timer_thread.start()

    def _process_ack(self, packet: Packet, repeated_ack: dict):
        logger.debug(f'{packet} - RECEIVED')
        if packet.seq_number > self.sequence.ack:
            self.window.increase(packet.seq_number - self.sequence.ack)
            self.sequence.ack = packet.seq_number
        else:
            repeated_ack[packet.seq_number] += 1
            if repeated_ack[packet.seq_number] > self.repeat_threshold:
                logger.debug(f"REPEATED ACK {packet.seq_number}: {repeated_ack[packet.seq_number]} RESENDING")
                self._reset()
                repeated_ack[packet.seq_number] = 0 
    
    def _reset(self):
        self.sequence.reset()
        self.window.reset()
        self.timer.stop()
    
    def _process_timer(self):
        while not self.end_connection:
            if self.timer.is_expired():
                logger.debug('Time out: Packet Lost')
                self._reset()
            sleep(0.01)

    def _process_incoming(self):
        self.socket.settimeout(self.SOCKET_TIMEOUT)
        repeated_ack = defaultdict(int)
        while not self.end_connection:
            try:
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
        validate_type("host", host, str)
        validate_type("port", port, int)
        self.host = host
        self.socket.bind((host, port))
 
    def accept(self) -> 'SocketTP':
        addr, mode = self.connection_queue.get()
        self.connection_being_accepted = addr
        
        socket_connection = socket(AF_INET, SOCK_DGRAM)
        socket_connection.bind((self.host, 0))
        socket_connection.settimeout(self.SOCKET_TIMEOUT)

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
            
        new_socket = SocketTP()
        new_socket.socket = socket_connection
        new_socket.dest_addr = addr
        new_socket._set_error_recovery_mode(mode)
        new_socket.process_incoming_thread.start()
        new_socket.timer_thread.start()
        return new_socket
    
    def connect(self, host: str, port: int, mode: ErrorRecoveryMode = ErrorRecoveryMode.GO_BACK_N):
        validate_type("host", host, str)
        validate_type("port", port, int)
        validate_type("mode", mode, ErrorRecoveryMode)
    
        logger.debug(f"Attempting to establish a connection with {host}:{port}")
        
        self.process_incoming_thread.start()
        self.timer_thread.start()
        
        time_limit = datetime.now() + timedelta(seconds=self.CONNECTION_TIMEOUT)
        while not self.dest_addr:
            if datetime.now() > time_limit:
                raise Exception("TIME OUT")
            self.socket.sendto(Packet(syn=True, data=mode.value.to_bytes()).to_bytes(), (host, port))
            sleep(self.SOCKET_TIMEOUT)
        
        self._set_error_recovery_mode(mode)
        
        logger.debug(f"Connection established successflully with {host}:{port}")       

    def sendall(self, data: bytes):
        validate_type("data", data, bytes)
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
        validate_type("size", size, int)
        buffer = b''
        while True:
            try:
                packet = self.packet_queue.get(timeout=self.CONNECTION_TIMEOUT)
            except queue.Empty:
                raise Exception("Time Out")
            
            buffer += packet.data
            if len(buffer) == size:
                return buffer

    def _set_error_recovery_mode(self, mode: ErrorRecoveryMode):
        new_window_size = self.GO_BACK_N_WINDOW
        repeat_threashold = 2
        if mode == ErrorRecoveryMode.STOP_AND_WAIT:
            new_window_size = self.STOP_AND_WAIT_WINDOW
            repeat_threashold = 0
        
        self.window.reset(new_window_size)
        self.repeat_threshold = repeat_threashold

    #TODO add close flux
    def close(self):
        sleep(1)
        self.end_connection = True
        self.socket.close()
        self.process_incoming_thread.join()
        self.timer_thread.join()
