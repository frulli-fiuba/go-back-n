from socket import socket, AF_INET, SOCK_DGRAM
from .constants import ErrorRecoveryMode
from .utils import Packet, Window, Timer, Sequence, validate_type, build_syn_payload, parse_syn_payload
import queue
import logging
from threading import Thread, Condition
from time import sleep
from datetime import datetime, timedelta


logger = logging.getLogger("socket")


class SocketTP:
    PACKET_DATA_SIZE = 1400
    CONNECTION_TIMEOUT = 30
    CLOSING_LOOP_LIMIT = 5
    SOCKET_TIMEOUT = 1
    GO_BACK_N_WINDOW = 5 * PACKET_DATA_SIZE

    def __init__(self):
        self.host = None
        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.connection_queue = None
        self.dest_addr = None
        self.end_connection = False
        self.window = Window(self.PACKET_DATA_SIZE)
        self.timer = Timer()
        self.sequence = Sequence()
        self.packet_queue = queue.Queue()
        self.timer_thread = Thread(target=self._process_timer)
        self.process_incoming_thread = Thread(target=self._process_incoming)
        self.received_ack = 0
        self.connection_being_accepted = None
        self.connection_accepted = False
        self.fin_received = False
        self.closed = False
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def _process_syn(self, addr: str, packet: Packet):     
        logger.debug(f'{addr} - {packet} - SYN RECEIVED')
        
        # SYN inicial sin ACK: cliente solicitando conexión
        if not packet.ack and addr != self.connection_being_accepted and self.connection_queue:
            try:
                mode = parse_syn_payload(packet.data)
            except ValueError as e:
                logger.error(f"{addr} invalid mode: {e} - IGNORED")
                return

            logger.debug(f"Added {addr} mode: {mode.name}, to the connection queue")
            self.connection_queue.put((addr, mode))
        elif packet.syn and packet.ack:
            self.socket.sendto(Packet(ack=True).to_bytes(), addr)
            self.dest_addr = addr          
    
    def listen(self, maxsize: int = 0):
        validate_type("maxsize", maxsize, int)
        self.connection_queue = queue.Queue(maxsize=maxsize)
        self.process_incoming_thread.start()
        self.timer_thread.start()

    def _process_ack(self, addr: str, packet: Packet):
        logger.debug(f'{packet} - RECEIVED from {addr}')
        if packet.seq_number > self.sequence.ack:
            self.window.increase(packet.seq_number - self.sequence.ack)
            self.sequence.ack = packet.seq_number
            self.timer.update_estimated_round_trip_time()
            self.timer.stop()

    def _reset(self):
        self.sequence.reset()
        self.window.reset()
        self.timer.stop()
    
    def _process_timer(self):
        while not self.end_connection:
            if self.timer.is_expired():
                logger.debug('Time out: Packet Lost')
                self._reset()
            sleep(0.001)
        
    def _process_incoming(self):
        self.socket.settimeout(self.SOCKET_TIMEOUT)

        while not self.end_connection:
            try:
                data, addr = self.socket.recvfrom(self.PACKET_DATA_SIZE + 7) # el tamanio maximo de datos mas los flags
                packet = Packet.from_bytes(data)
                if packet.syn:
                    self._process_syn(addr, packet)
                elif packet.fin:
                    self.end_connection = True
                    self.fin_received = True
                elif packet.ack and addr == self.dest_addr:
                    self._process_ack(addr, packet)
                else:
                    if packet.seq_number == self.received_ack and addr == self.dest_addr:
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
    
    def get_incomming_connection(self):
        addr = None
        mode = None
        
        while not self.end_connection and not addr:
            try:
                addr, mode = self.connection_queue.get(timeout=2)
            except:
                # intentamos tomar una conexion entrante,
                # si en 2 segundos no aparecio ninguna chequeamos si se cerro el socket,
                # si no se cerro intentamos 2 segundos mas, asi hasta q aparezca algo
                # o se cierre el socket
                continue
        
        if self.end_connection:
            raise Exception("Socket Closed")
        
        return addr, mode

    def accept(self) -> 'SocketTP':
        addr = None
        mode = None
        
        addr, mode = self.get_incomming_connection()
        
        self.connection_being_accepted = addr
        
        socket_connection = socket(AF_INET, SOCK_DGRAM)
        socket_connection.bind((self.host, 0))
        socket_connection.settimeout(self.SOCKET_TIMEOUT)
        
        time_limit = datetime.now() + timedelta(seconds=self.CONNECTION_TIMEOUT)
        while self.connection_being_accepted:
            if datetime.now() > time_limit:
                # si hay timeout buscamos otra conexion entrante
                addr, mode = self.get_incomming_connection()
                self.connection_being_accepted = addr
                time_limit = datetime.now() + timedelta(seconds=self.CONNECTION_TIMEOUT)
            try:
                socket_connection.sendto(Packet(syn=True, ack=True).to_bytes(), addr)
                data, recv_addr = socket_connection.recvfrom(self.PACKET_DATA_SIZE)
                packet = Packet.from_bytes(data)
                logger.debug(f'{addr} - {packet}')
                if recv_addr == addr and packet.ack:
                    self.connection_being_accepted = None
            except:
                # no recibimos nada del socket abierto, 
                # seguimos esperando hasta el timeout antes de descartarla y buscar otra
                pass
        
        new_socket = SocketTP()

        new_socket.socket = socket_connection
        new_socket.dest_addr = addr
        new_socket._set_error_recovery_mode(mode)
        new_socket.process_incoming_thread.start()
        new_socket.timer_thread.start()

        logger.debug(f"Connection established successfully with {addr} mode: {mode.name}")

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

            self.socket.sendto(
                Packet(syn=True, data=build_syn_payload(mode)).to_bytes(),
                (host, port)
            )
            sleep(self.SOCKET_TIMEOUT)
        
        self._set_error_recovery_mode(mode)

        logger.debug(f"Connection established successfully with {host}:{port}")

    def sendall(self, data: bytes):
        validate_type("data", data, bytes)
        offset = self.sequence.send
        sequence = self.sequence.send
        fin = False
        time_limit = datetime.now() + timedelta(seconds=self.CONNECTION_TIMEOUT)
        last_ack = None
        while not fin and not self.end_connection:
            if datetime.now() > time_limit:
                raise Exception("TIME OUT")
            start = sequence - offset
            end = start + min(self.PACKET_DATA_SIZE, self.window.size, len(data[start:]))
            if data[start: end]:
                if self.sequence.are_equal():
                    self.timer.set()

                packet = Packet(data=data[start: end], seq_number=sequence)
                self.socket.sendto(packet.to_bytes(), self.dest_addr)
                
                logger.debug(f'{self.dest_addr} - {packet} - SENT')
                
                self.window.decrease(len(data[start: end]))
            else:
                if not self.timer.is_set():
                    self.timer.set()
                with self.window.empty_window: # esperamos hasta q tengamos lugar en la ventana
                    self.window.empty_window.wait(timeout=self.timer.estimated_round_trip_time)
            
            with self.sequence.lock:
                if sequence > self.sequence._send:
                    sequence = self.sequence._send
                else:
                    self.sequence._send = offset + end 
                    sequence = offset + end
                if last_ack != self.sequence._ack:
                    # Si no cambio el ack por CONNECTION_TIMEOUT segundos asumimos q murio el receiver
                    time_limit = datetime.now() + timedelta(seconds=self.CONNECTION_TIMEOUT)
                    last_ack = self.sequence._ack
                fin = len(data) == self.sequence._ack - offset
    
    def recv(self, size: int) -> bytes:
        validate_type("size", size, int)
        buffer = b''
        started = datetime.now()
        while not self.end_connection:
            try:
                packet = self.packet_queue.get(timeout=self.CONNECTION_TIMEOUT)
            except queue.Empty:
                raise Exception("TIME OUT")
            
            buffer += packet.data
            if len(buffer) == size:
                logger.debug(f"Downloaded in {(datetime.now() - started).seconds / 60} minutes")
                return buffer
        raise Exception("CONNECTION CLOSED")   

    def _set_error_recovery_mode(self, mode: ErrorRecoveryMode):
        new_window_size = self.GO_BACK_N_WINDOW

        if mode == ErrorRecoveryMode.STOP_AND_WAIT:
            # mandamos un solo paquete y esperamos ack
            new_window_size = self.PACKET_DATA_SIZE 
        
        self.window.reset(new_window_size)


    def close(self):
        if self.closed:
            return    
        self.closed = True
        self.end_connection = True
        self.process_incoming_thread.join()
        self.timer_thread.join()  
        if self.dest_addr:
            #se podrian hacer chequeos de sequence number para emular tcp, aunque no traeria ningun beneficio real a este cierre
            time_wait = timedelta(seconds=self.timer.estimated_round_trip_time * 2) #una especie de timewait
            time_limit = datetime.min
            fin_acked = False
            timeout = True
            for _ in range(self.CLOSING_LOOP_LIMIT):
                if not fin_acked and datetime.now() > time_limit:
                    self.socket.sendto(Packet(fin=True).to_bytes(), self.dest_addr)
                    logger.debug(f"{self.dest_addr} - FIN - SENT")  
                    time_limit = datetime.now() + time_wait 
                try:
                    data, _ = self.socket.recvfrom(self.PACKET_DATA_SIZE)
                    packet = Packet.from_bytes(data)
                    if packet.ack:
                        fin_acked = True
                        logger.debug(f"{self.dest_addr} - ACK - RECEIVED") 
                    if packet.fin:
                        self.fin_received = True
                        logger.debug(f"{self.dest_addr} - FIN - RECEIVED") 
                        self.socket.sendto(Packet(ack=True).to_bytes(), self.dest_addr)
                        logger.debug(f"{self.dest_addr} - ACK - SENT")  
                except TimeoutError:
                    if self.fin_received and fin_acked:
                        break
                    continue      
        self.socket.close()


