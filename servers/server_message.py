from enum import Enum
from typing import Optional


class MessageType(Enum):
    REGISTER = 1,
    REQUEST = 2,
    TIMER = 3,
    RESPONSE = 4,
    FINISH = 5,


class ServerMessage:
    def __init__(self, em_id, mssg_type, *args):
        self.em_id: str = em_id
        self.mssg_type: MessageType = mssg_type
        self.request: Optional[str] = args if args else None

    @staticmethod
    def gen_mssg(emulator_id: str, mssg_type: MessageType, *args) -> bytes:
        mssg = emulator_id + '\t' + mssg_type.name + '\t' + '\t'.join([str(x) for x in args])
        return mssg.encode(encoding='utf-8')

    @staticmethod
    def from_bytes(raw_mssg: bytes):
        em_id, mssg_type, *request = raw_mssg.decode().split('\t')
        mssg_type = MessageType[mssg_type]
        return ServerMessage(em_id, mssg_type, request)


if __name__ == "__main__":
    mssg = ServerMessage.gen_mssg('ISDISD', MessageType.REGISTER)
    print(mssg)
