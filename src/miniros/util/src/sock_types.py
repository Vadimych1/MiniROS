from enum import Enum
import socket

AddrLike = str | tuple[str, int]


class Datatypes(Enum):
    ERROR = 0x00

    POST = 0x01
    SEND_POST = 0x02

    GET = 0x03
    SEND_GET = 0x04

    SUBSCRIBE = 0x05
    UNSUBSCRIBE = 0x06

    ANON = 0x07
    SEND_ANON = 0x08

    ROSSTAT = 0xFB

    GET_UDP_AUTH = 0xFC
    SEND_UDP_AUTH = 0xFD
    REQUEST_AUTH = 0xFE
    SEND_AUTH = 0xFF


class Errortypes(Enum):
    NODE_EXISTS = 0x00
    METHOD_NOT_FOUND = 0x01
    INVALID_CREDENTIALS = 0x02
    INVALID_SUBSCRIBE = 0x03
    INVALID_ANON_CREDENTIALS = 0x04
    INVALID_GET_UDP_CREDENTIALS = 0x05


class DistributedDatatypes(Enum):
    PING = 0x00
    PONG = 0x01

    ANON = 0x02


class Status(Enum):
    OK = 0x00
    ERROR = 0x01


class Field:
    __slots__ = ("name", "data", "subscribers")

    def __init__(self, name: bytes, data: bytes, subscribers: list[str]):
        self.data = data
        self.subscribers = subscribers
        self.name = name

    def to_json(self):
        return {
            "name": self.name.decode(),
            "subscribers": list(map(bytes.decode, self.subscribers)),
        }


class Connection:
    __slots__ = ("name", "fields", "socket", "udp_addr")

    def __init__(
        self,
        name: bytes,
        fields: dict[str, Field],
        socket: "socket.socket",
        udp_addr: AddrLike,
    ):
        self.name = name
        self.fields = fields
        self.socket = socket
        self.udp_addr = udp_addr

    def to_json(self):
        return {
            "name": self.name.decode(),
            "fields": list(map(Field.to_json, self.fields.values())),
        }
