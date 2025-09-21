from enum import Enum

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 6000

class ErrorRecoveryMode(Enum):
    GO_BACK_N = 1
    STOP_AND_WAIT = 2


ERROR_RECOVERY_PROTOCOL_MAPPING = {
    "GO_BACK_N": ErrorRecoveryMode.GO_BACK_N,
    "STOP_AND_WAIT": ErrorRecoveryMode.STOP_AND_WAIT
}


class ClientMode(Enum):
    UPLOAD = 1
    DOWNLOAD = 2
