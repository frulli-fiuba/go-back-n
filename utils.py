
from threading import Lock
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class Packet:
    def __init__(self, data: bytes = b'', seq_number: int = 0, ack_number: int = 0, ack: bool = False, syn: bool = False, fin: bool = False):
        self.data = data
        self.seq_number = seq_number
        self.ack_number = ack_number
        self.ack = ack
        self.syn = syn
        self.fin = fin
    
    def to_bytes(self) -> bytes:
        return self.seq_number.to_bytes(4, "big") + self.ack_number.to_bytes(4, "big") + self.ack.to_bytes(1, "big") + self.syn.to_bytes(1, "big") + self.fin.to_bytes(1, "big") + self.data
    
    @staticmethod
    def from_bytes(data: bytes) -> 'Packet':
        seq_number = int.from_bytes(data[:4], "big")
        ack_number = int.from_bytes(data[4:8], "big")
        ack = bool(data[8])
        syn = bool(data[9])
        fin = bool(data[10])
        data = data[11:]
        return Packet(data=data, seq_number=seq_number, ack_number=ack_number, ack=ack, syn=syn, fin=fin)
    
    def __str__(self) -> str:
        return f"Packet(seq_number={self.seq_number}, ack_number={self.ack_number}, ack={self.ack}, syn={self.syn}, fin={self.fin}, datasize={len(self.data)})"


class Sequence:
    def __init__(self, send: int = 0, ack: int = 0):
        self._send = send
        self._ack = ack
        self.lock = Lock()

    @property
    def send(self):
        with self.lock:
            return self._send
    
    @property
    def ack(self):
        with self.lock:
            return self._ack

    @send.setter
    def send(self, send: int):
        with self.lock:
            self._send = send
    
    @ack.setter
    def ack(self, ack: int):
        with self.lock:
            self._ack = ack
    
    def reset(self):
        with self.lock:
            self._send = self._ack
    
    def are_equal(self):
        with self.lock:
            return self._send == self._ack

class Window:
    def __init__(self, size: int):
        self._size = size
        self._actual_size = size
        self.lock = Lock()

    def decrease(self, size: int):
        with self.lock:
            old_size = self._actual_size
            self._actual_size -= size
            logger.debug(f'Window size, from {old_size} to {self._actual_size} - DECREASE')    
    
    def increase(self, size: int):
        with self.lock:
            old_size = self._actual_size
            self._actual_size += size
            logger.debug(f'Window size, from {old_size} to {self._actual_size} - INCREASE')      
    
    @property
    def size(self)->int:
        with self.lock:
            return self._actual_size
    
    def reset(self):
        with self.lock:
            old_size = self._actual_size
            self._actual_size = self._size
            logger.debug(f'Window size, from {old_size} to {self._actual_size} - RESET')  

class Timer:
    def __init__(self):
        self.limit_time = None
        self.lock = Lock()

    def stop(self):
        with self.lock:
            self.limit_time = None

    def is_expired(self) -> bool:
        with self.lock:
            return self.limit_time and datetime.now() > self.limit_time
    
    def is_set(self) -> bool:
        with self.lock:
            return bool(self.limit_time)
    
    def set(self):
        with self.lock:
            self.limit_time = datetime.now() + timedelta(seconds=2)