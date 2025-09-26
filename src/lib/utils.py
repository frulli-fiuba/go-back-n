from typing import Any, Tuple
from threading import Lock, Condition
from datetime import datetime, timedelta
from .constants import ErrorRecoveryMode, ClientMode
import logging

logger = logging.getLogger("socket")


def validate_type(name: str, value: Any, type_to_validate: type):
    if not isinstance(value,type_to_validate):
        raise ValueError(f"{name} should be of type {type_to_validate}")


def build_syn_payload(mode: ErrorRecoveryMode) -> bytes:
    """
    Formato:
      - 4 bytes: mode (big-endian uint32)
    """
    return mode.value.to_bytes(4, "big")


def parse_syn_payload(data: bytes) -> Tuple[ErrorRecoveryMode]:
    """
    Parsea el payload del SYN.
    Formato:
      - 4 bytes: mode (big-endian uint32)
    """
    if len(data) < 4:
        raise ValueError("syn payload too short")
    
    mode_val = int.from_bytes(data[:4], "big")
    return ErrorRecoveryMode(mode_val)


class Packet:
    def __init__(self, data: bytes = b'', seq_number: int = 0, ack: bool = False, syn: bool = False, fin: bool = False):
        self.data = data
        self.seq_number = seq_number
        self.ack = ack
        self.syn = syn
        self.fin = fin
    #TODO se podrian comprimir los flags en 1 byte para achicar el header
    def to_bytes(self) -> bytes:
        return self.seq_number.to_bytes(4, "big") + self.ack.to_bytes(1, "big") + self.syn.to_bytes(1, "big") + self.fin.to_bytes(1, "big") + self.data
    
    @staticmethod
    def from_bytes(data: bytes) -> 'Packet':
        seq_number = int.from_bytes(data[:4], "big")
        ack = bool(data[4])
        syn = bool(data[5])
        fin = bool(data[6])
        data = data[7:]
        return Packet(data=data, seq_number=seq_number, ack=ack, syn=syn, fin=fin)
    
    def __str__(self) -> str:
        return f"Packet(seq_number={self.seq_number}, ack={self.ack}, syn={self.syn}, fin={self.fin}, datasize={len(self.data)})"


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
        self.empty_window = Condition()

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
        with self.empty_window:
            self.empty_window.notify()      
    
    @property
    def size(self)->int:
        with self.lock:
            return self._actual_size
    
    def reset(self, window_size: int = None):
        with self.lock:
            if window_size:
                self._size = window_size
            old_size = self._actual_size
            self._actual_size = self._size
            logger.debug(f'Window size, from {old_size} to {self._actual_size} - RESET')  
            with self.empty_window:
                self.empty_window.notify()


class Timer:
    def __init__(self):
        self.start_time = None
        self.limit_time = None
        self.estimated_round_trip_time = 1
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
            now = datetime.now()
            if self.start_time:
                self.estimated_round_trip_time = (1 - 0.125) * self.estimated_round_trip_time + 0.125 * (now - self.start_time).seconds
            
            self.start_time = now
            self.limit_time = self.start_time + timedelta(seconds=self.estimated_round_trip_time)
