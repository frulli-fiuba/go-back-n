


class Packet:
    def __init__(self, data: bytes = b'', seq: int = 0, ack: bool = False, syn: bool = False, fin: bool = False):
        self.data = data
        self.seq = seq
        self.ack = ack
        self.syn = syn
        self.fin = fin
    
    def to_bytes(self) -> bytes:
        return self.seq.to_bytes(4, "big") + self.ack.to_bytes(1, "big") + self.syn.to_bytes(1, "big") + self.fin.to_bytes(1, "big") + self.data
    
    @staticmethod
    def from_bytes(data: bytes) -> 'Packet':
        seq = int.from_bytes(data[:4], "big")
        ack = bool(data[4])
        syn = bool(data[5])
        fin = bool(data[6])
        data = data[7:]
        return Packet(data, seq, ack, syn, fin)
    
    def __str__(self) -> str:
        return f"Packet(seq={self.seq}, ack={self.ack}, syn={self.syn}, fin={self.fin}, datasize={len(self.data)})"