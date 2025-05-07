import socket
import struct
import logging
import zlib
import threading
from enum import Enum
from typing import Callable
import json
import time

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

    ROSSTAT = 0xfd

    REQUEST_AUTH = 0xfe
    SEND_AUTH = 0xff

class Errortypes(Enum):
    NODE_EXISTS = 0x00
    METHOD_NOT_FOUND = 0x01
    INVALID_CREDENTIALS = 0x02
    INVALID_SUBSCRIBE = 0x03
    INVALID_ANON_CREDENTIALS = 0x04

class Status(Enum):
    OK = 0x00
    ERROR = 0x01

def new_sock(use_udp: bool = False) -> socket.socket:
    """
    Initializes new fast socket
    :param 
    """
    
    sock = None
    if "AF_UNIX" in socket.__dict__:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM if use_udp else socket.SOCK_STREAM)

    else:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM if use_udp else socket.SOCK_STREAM)

    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1) if not use_udp else ...
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024 * 1024 * 32)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024 * 1024 * 32)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # sock.setblocking(False)

    return sock

class SockServer:
    """
    Socket server base class
    Implements basic methods for interacting with clients
    """

    def __init__(self, ip: str, port: int):
        self.ip = ip
        self.port = port
        self.servers: dict[str, dict] = {}

        self.sending = False # fix for byte-mismatch

    def send(self, sock: socket.socket, data: bytearray, addr: None | AddrLike) -> None:
        data = zlib.compress(data)
        length = len(data)
        length = struct.pack(">I", length)

        while self.sending:
            time.sleep(0.01)
        
        self.sending = True

        self._send(sock, length, addr)
        self._send(sock, data, addr)
        
        self.sending = False

    def recv(self, sock: socket.socket, addr: None | AddrLike) -> bytearray:
        try:
            length = self._recv(sock, 4, addr)
            length = struct.unpack(">I", length)[0]
            logging.info(f"WAITING FOR {length}")
            return zlib.decompress(self._recv(sock, length, addr))        
        except:
            return bytearray([])
            
    def _recv(self, sock, length, addr):
        ...

    def _send(self, sock, data, addr):
        ...

    def handler(self, conn: socket.socket, addr: None | AddrLike) -> None:
        CREDENTIALS = None

        self.send(conn, bytearray([Datatypes.REQUEST_AUTH.value]), addr)
        
        try:
            while True:
                data = self.recv(conn, addr)
                data, datatype = data[1:], data[0]

                match datatype:
                    case Datatypes.SEND_AUTH.value:
                        logging.debug("GOT SEND_AUTH")

                        CREDENTIALS = data.decode()

                        if len(CREDENTIALS) != 3:
                            self.send(conn, bytearray([Datatypes.ERROR.value, Errortypes.INVALID_CREDENTIALS.value]), addr)
                            
                        if CREDENTIALS in self.servers:
                            self.send(conn, bytearray([Datatypes.ERROR.value, Errortypes.INVALID_CREDENTIALS.value]), addr)
                            continue

                        self.servers[CREDENTIALS] = {
                            "name": CREDENTIALS,
                            "fields": {},
                            "socket": conn,
                        }

                    case Datatypes.GET.value:
                        logging.debug("GOT GET")

                        raw_node_name = data[0:3]
                        raw_field_name = data[3:6]
                        node_name = raw_node_name.decode()
                        field_name = raw_field_name.decode()

                        if node_name not in self.servers or field_name not in self.servers[field_name]:
                            self.send(conn, bytearray([
                                Datatypes.ERROR.value,
                                Errortypes.INVALID_CREDENTIALS.value
                            ]), addr)
                            continue

                        send = self.servers[node_name]["fields"][field_name]["data"]
                        send = send if send else bytearray([])
                        self.send(conn, bytearray([
                            Datatypes.SEND_GET.value,
                            *raw_node_name,
                            *raw_field_name,
                            *send,
                        ]), addr)

                    case Datatypes.POST.value:
                        logging.debug("GOT POST")

                        raw_field_name = data[0:3]
                        field_name = raw_field_name.decode()
                        if field_name not in self.servers[CREDENTIALS]["fields"]:
                            self.servers[CREDENTIALS]["fields"][field_name] = {
                                "data": data[3:],
                                "subscribers": [], 
                            }
                        else:
                            self.servers[CREDENTIALS]["fields"][field_name]["data"] = data[3:]

                        
                        for subscriber in self.servers[CREDENTIALS]["fields"][field_name]["subscribers"]:
                            self.send(self.servers[subscriber]["socket"], bytearray([
                                Datatypes.SEND_GET.value,
                                *CREDENTIALS.encode(),
                                *raw_field_name,
                                *self.servers[CREDENTIALS]["fields"][field_name]["data"],
                            ]), addr)
                        

                        self.send(conn, bytearray([
                            Datatypes.SEND_POST.value,
                            Status.OK.value
                        ]), addr)

                    case Datatypes.SUBSCRIBE.value:
                        logging.debug("GOT SUBSCRIBE")

                        node_name = data[0:3].decode()
                        field_name = data[3:6].decode()

                        if node_name not in self.servers:
                            self.send(conn, bytearray([
                                Datatypes.ERROR.value,
                                Errortypes.INVALID_SUBSCRIBE.value
                            ]), addr)
                            continue

                        if field_name not in self.servers[node_name]["fields"]:
                            self.servers[node_name]["fields"][field_name] = {
                                "data": None,
                                "subscribers": [
                                    CREDENTIALS,
                                ]
                            }
                        else:
                            self.servers[node_name]["fields"][field_name]["subscribers"].append(CREDENTIALS)

                    case Datatypes.ANON.value:
                        logging.debug("GOT ANON")

                        raw_node_name = data[0:3]
                        raw_field_name = data[3:6]

                        node_name = raw_node_name.decode()
                        field_name = raw_field_name.decode()

                        if node_name not in self.servers:
                            self.send(conn, bytearray([
                                Datatypes.ERROR.value,
                                Errortypes.INVALID_ANON_CREDENTIALS.value
                            ]), addr)
                            continue

                        self.send(self.servers[node_name]["socket"], bytearray([
                            Datatypes.SEND_ANON.value,
                            *CREDENTIALS.encode(),
                            *raw_field_name,
                            *data[6:], # additional info
                        ]), addr)

                    case Datatypes.ROSSTAT.value:
                        logging.debug("GOT ROSSTAT")

                        tosend = {}
                        for x in self.servers.keys():
                            v = self.servers[x].copy()

                            for fld in v["fields"].keys():
                                del v["fields"][fld]["data"]

                            del v["socket"]
                            tosend[x] = v

                        self.send(conn, bytearray([
                            Datatypes.ROSSTAT.value,
                            *json.dumps(tosend).encode()
                        ]), addr)

                    case _:
                        self.send(conn, bytearray([Datatypes.ERROR.value, Errortypes.METHOD_NOT_FOUND.value]), addr)

        except Exception as e:
            print(e)
        
        finally:
            if CREDENTIALS in self.servers:
                del self.servers[CREDENTIALS]


class SockClient:
    def __init__(self, ip: str, port: int, name: str):
        self.ip = ip
        self.port = port
        self.name = name

        self.received = {}
        self.handlers = {}
        self.anon_handlers = {}

        self.sending = False # fix for byte-mismatch

        self.on_rosstat = lambda *val: ...

    def send(self, data: bytearray) -> None:
        data = zlib.compress(data)
        length = len(data)
        length = struct.pack(">I", length)

        while self.sending:
            time.sleep(0.01)

        self.sending = True

        self._send(length)
        self._send(data)
        
        self.sending = False

    def recv(self) -> bytearray:
        try:
            length = self._recv(4)
            length = struct.unpack(">I", length)[0]
            return zlib.decompress(self._recv(length))
        except:
            return bytearray([])

    def _recv(self, length) -> bytearray:
        ...

    def _send(self, data) -> bytearray:
        ...
    
    def subscribe(self, node: str, field: str, handler: Callable | None) -> None:
        self.send(bytearray([
            Datatypes.SUBSCRIBE.value,
            *node.encode(),
            *field.encode(),
        ]))

        if handler is not None:
            if node not in self.handlers:
                self.handlers[node] = {}

            self.handlers[node][field] = handler

            logging.debug(f"ADDED HANDLER {node}:{field}")

    def unsubscribe(self, node: str, field: str) -> None:
        self.send(bytearray([
            Datatypes.UNSUBSCRIBE.value,
            *node.encode(),
            *field.encode(),
        ]))

    def post(self, field: str, data: bytearray) -> None:
        self.send(bytearray([
            Datatypes.POST.value,
            *field.encode(),
            *data,
        ]))

    def anon(self, node: str, field: str, data: bytearray) -> None:
        self.send(bytearray([
            Datatypes.ANON.value,
            *node.encode(),
            *field.encode(),
            *data
        ]))

    def rosstat(self) -> None:
        self.send(bytearray([
            Datatypes.ROSSTAT.value,
        ]))

    def mainloop(self):
        while True:
            data = self.recv()
            data, datatype = data[1:], data[0]

            match datatype:
                case Datatypes.REQUEST_AUTH.value:
                    logging.debug("GOT REQUEST_AUTH")

                    CREDENTIALS = self.name.encode()

                    self.send(bytearray([
                        Datatypes.SEND_AUTH.value,
                        *CREDENTIALS
                    ]))

                case Datatypes.SEND_GET.value:
                    logging.debug("GOT SEND_GET")
                    
                    node_name = data[0:3].decode()
                    field_name = data[3:6].decode()
                    
                    if node_name not in self.received:
                        self.received[node_name] = {}

                    self.received[node_name][field_name] = data[6:]
                    if node_name in self.handlers and field_name in self.handlers[node_name]:
                        self.handlers[node_name][field_name](data[6:])

                case Datatypes.SEND_POST.value:
                    logging.debug("GOT SEND_POST")

                case Datatypes.ERROR.value:
                    logging.debug("GOT ERROR")
                    logging.debug(data)

                    match data[0]:
                        case Errortypes.NODE_EXISTS.value:
                            logging.error("Node name already exists")
                            break

                        case Errortypes.INVALID_CREDENTIALS.value:
                            logging.error("Sended invalid credentials")
                            break

                        case Errortypes.METHOD_NOT_FOUND.value:
                            logging.error("Requested method not found")

                        case Errortypes.INVALID_SUBSCRIBE.value:
                            logging.error("Sended invalid subscribe credentials")

                case Datatypes.SEND_ANON.value:
                    logging.debug("GOT SEND_ANON")

                    raw_node_name = data[0:3]
                    raw_field_name = data[3:6]

                    node_name = raw_node_name.decode()
                    field_name = raw_field_name.decode()

                    self.anon_handlers[field_name](data[6:], node_name)

                case Datatypes.ROSSTAT.value:
                    self.on_rosstat(json.loads(data.decode()))

                case _:
                    self.send(bytearray([Datatypes.ERROR.value, Errortypes.METHOD_NOT_FOUND.value]))        

class TCPSockServer(SockServer):
    def __init__(self, ip: str, port: int):
        self.sock = new_sock(False)
        self.sock.bind((ip, port))
        super().__init__(ip, port)

    def run(self) -> None:
        self.sock.listen()
        while True:
            conn, addr = self.sock.accept()
            threading.Thread(target=self.handler, args=(conn, addr)).start()

    def _recv(self, sock: socket.socket, length, addr):
        return sock.recv(length)
    
    def _send(self, sock: socket.socket, data, addr):
        return sock.send(data)
    
class TCPSockClient(SockClient):
    def __init__(self, ip: str, port: int, name: str):
        self.sock = new_sock(False)
        self.sock.connect((ip, port))
        super().__init__(ip, port, name)

    def _recv(self, length):
        return self.sock.recv(length)
    
    def _send(self, data):
        return self.sock.send(data)


class UDPSockServer(SockServer):
    def __init__(self, ip: str, port: int):
        self.n = 1

        self.sock = new_sock(True)
        self.sock.bind((ip, port))
        super().__init__(ip, port)

    def run(self) -> None:
        while True:
            _, addr = self.sock.recvfrom(1)

            handler_sock = new_sock(True)
            handler_sock.bind((self.ip, self.port + self.n))
            
            self.n += 1
            threading.Thread(target=self.handler, args=(handler_sock, addr)).start()

    def _recv(self, sock: socket.socket, length, addr: AddrLike):
        data, _addr = sock.recvfrom(length)
        return data
    
    def _send(self, sock: socket.socket, data, addr: AddrLike):
        return sock.sendto(data, addr)

class UDPSockClient(SockClient):
    def __init__(self, ip: str, port: int, name: str):
        self.sock = new_sock(True)
        self.sock.sendto(b"0", (ip, port))

        super().__init__(ip, port, name)

    def _recv(self, length):
        data, _addr = self.sock.recvfrom(length)
        ip, port = _addr

        self.ip = ip
        self.port = port

        return data
    
    def _send(self, data):
        return self.sock.sendto(data, (self.ip, self.port))